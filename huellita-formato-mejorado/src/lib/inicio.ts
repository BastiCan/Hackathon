/**
 * Pantalla de inicio: la semana de lunes a viernes con lo que se registró cada
 * día y el próximo registro del IEA. Funciones puras, para probarlas sin
 * montar pantallas.
 */
import type { Evidencia, Sugerencia } from './tipos';

const DIAS_CORTOS = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb'];
const DIAS_LARGOS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];

/** Máximo de puntos por día: más no caben en la casilla. */
const MAX_PUNTOS = 6;

function aFecha(iso: string): Date {
  const [a, m, d] = iso.slice(0, 10).split('-').map(Number);
  return new Date(Date.UTC(a, m - 1, d));
}

function aISO(fecha: Date): string {
  return fecha.toISOString().slice(0, 10);
}

export type EstadoRegistro = 'revisado' | 'pendiente';

export interface DiaSemana {
  fecha: string;
  nombreCorto: string;
  nombreLargo: string;
  numero: number;
  esHoy: boolean;
  /** Día que todavía no llega. */
  esFuturo: boolean;
  /** Registros del día que siguen vigentes (lo descartado entero no cuenta). */
  registros: number;
  /** De esos, los que todavía esperan la revisión de la tía. */
  porRevisar: number;
  /** Un punto por registro (máximo 6), en el orden en que llegaron. */
  puntos: EstadoRegistro[];
}

/**
 * Estado de un registro: pendiente mientras Huellita lo lee, si no se pudo leer
 * o si tiene alguna sugerencia por confirmar; `null` si se descartó entero.
 */
export function estadoRegistro(
  evidencia: Evidencia,
  sugerencias: Sugerencia[],
): EstadoRegistro | null {
  const suyas = sugerencias.filter(
    (s) => s.evidenciaId === evidencia.id && s.estado !== 'descartada',
  );
  if (evidencia.estado === 'lista' && suyas.length === 0) return null;
  if (evidencia.estado !== 'lista' || suyas.some((s) => s.estado === 'pendiente')) {
    return 'pendiente';
  }
  return 'revisado';
}

/** Lunes a viernes de la semana de `hoy` (si `hoy` es fin de semana, la que termina). */
export function semanaDe(
  hoy: string,
  evidencias: Evidencia[],
  sugerencias: Sugerencia[],
): DiaSemana[] {
  const base = aFecha(hoy);
  const dow = base.getUTCDay(); // 0 domingo
  const desdeLunes = dow === 0 ? 6 : dow - 1; // sábado = 5, domingo = 6
  const lunes = new Date(base);
  lunes.setUTCDate(base.getUTCDate() - desdeLunes);
  const diaHoy = hoy.slice(0, 10);

  return [0, 1, 2, 3, 4].map((i) => {
    const d = new Date(lunes);
    d.setUTCDate(lunes.getUTCDate() + i);
    const fecha = aISO(d);
    const estados = evidencias
      .filter((e) => e.creadaEn.slice(0, 10) === fecha)
      .map((e) => estadoRegistro(e, sugerencias))
      .filter((e): e is EstadoRegistro => e !== null);
    return {
      fecha,
      nombreCorto: DIAS_CORTOS[d.getUTCDay()],
      nombreLargo: DIAS_LARGOS[d.getUTCDay()],
      numero: d.getUTCDate(),
      esHoy: fecha === diaHoy,
      esFuturo: fecha > diaHoy,
      registros: estados.length,
      porRevisar: estados.filter((e) => e === 'pendiente').length,
      puntos: estados.slice(0, MAX_PUNTOS),
    };
  });
}

/** Lo que un lector de pantalla dice de un día: "lunes 12: 3 registros, 1 por revisar". */
export function etiquetaDia(d: DiaSemana): string {
  const nombre = `${d.nombreLargo} ${d.numero}${d.esHoy ? ', hoy' : ''}`;
  if (d.esFuturo) return `${nombre}: todavía no llega`;
  if (d.registros === 0) return `${nombre}: sin registros`;
  const registros = `${d.registros} ${d.registros === 1 ? 'registro' : 'registros'}`;
  return d.porRevisar > 0 ? `${nombre}: ${registros}, ${d.porRevisar} por revisar` : `${nombre}: ${registros}`;
}

/** Próximo registro del IEA (abril, agosto y noviembre) desde `hoy`. */
export function proximoIEA(hoy: string): { numero: 1 | 2 | 3; mes: string } {
  const mes = Number(hoy.slice(5, 7));
  if (mes <= 4) return { numero: 1, mes: 'abril' };
  if (mes <= 8) return { numero: 2, mes: 'agosto' };
  if (mes <= 11) return { numero: 3, mes: 'noviembre' };
  return { numero: 1, mes: 'abril' };
}
