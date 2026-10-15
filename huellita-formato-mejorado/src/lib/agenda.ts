/**
 * Agenda de la tía: el día ordenado por los períodos de la jornada (Referente
 * Curricular de Integra, "períodos constantes") y la semana de lunes a viernes.
 * Funciones puras, para probarlas sin montar pantallas.
 */
import type { Evidencia, NucleoId, Sugerencia } from './tipos';

export interface Periodo {
  inicio: string; // "HH:MM"
  nombre: string;
}

/** Jornada típica de un jardín de Integra. Configurable en el futuro por sala. */
export const JORNADA: Periodo[] = [
  { inicio: '08:30', nombre: 'Recepción y saludo' },
  { inicio: '09:00', nombre: 'Desayuno' },
  { inicio: '09:30', nombre: 'Experiencia de aprendizaje' },
  { inicio: '10:30', nombre: 'Patio y juego libre' },
  { inicio: '11:30', nombre: 'Hábitos y almuerzo' },
  { inicio: '12:30', nombre: 'Descanso' },
  { inicio: '14:30', nombre: 'Experiencia de la tarde' },
  { inicio: '16:00', nombre: 'Despedida' },
];

const DIAS_CORTOS = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb'];

function aFecha(iso: string): Date {
  const [a, m, d] = iso.slice(0, 10).split('-').map(Number);
  return new Date(Date.UTC(a, m - 1, d));
}

function aISO(fecha: Date): string {
  return fecha.toISOString().slice(0, 10);
}

/** Período de la jornada al que pertenece una hora; antes de las 8:30, el primero. */
export function periodoDe(horaHHMM: string): Periodo {
  let elegido = JORNADA[0];
  for (const p of JORNADA) {
    if (horaHHMM >= p.inicio) elegido = p;
  }
  return elegido;
}

export interface DiaSemana {
  fecha: string;
  nombreCorto: string;
  numero: number;
  esHoy: boolean;
  /** Un punto por registro del día, con el color de su ámbito (o gris). */
  puntos: ('dps' | 'com' | 'ent' | 'sala')[];
}

const AMBITO: Record<NucleoId, 'dps' | 'com' | 'ent'> = {
  IA: 'dps',
  CC: 'dps',
  CM: 'dps',
  LV: 'com',
  LA: 'com',
  EN: 'ent',
  ES: 'ent',
  PM: 'ent',
};

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

  return [0, 1, 2, 3, 4].map((i) => {
    const d = new Date(lunes);
    d.setUTCDate(lunes.getUTCDate() + i);
    const fecha = aISO(d);
    const delDia = evidencias.filter((e) => e.creadaEn.slice(0, 10) === fecha);
    const puntos = delDia.slice(0, 6).map((e) => {
      const s = sugerencias.find(
        (x) => x.evidenciaId === e.id && x.estado !== 'descartada' && x.nucleo,
      );
      return s?.nucleo ? AMBITO[s.nucleo] : ('sala' as const);
    });
    return {
      fecha,
      nombreCorto: DIAS_CORTOS[d.getUTCDay()],
      numero: d.getUTCDate(),
      esHoy: fecha === hoy.slice(0, 10),
      puntos,
    };
  });
}

export interface EntradaAgenda {
  sugerenciaId: string;
  tipo: Sugerencia['tipo'];
  ninoId?: string;
  nombre: string;
  nucleo?: NucleoId;
  nivel?: Sugerencia['nivel'];
  pendiente: boolean;
}

export interface RegistroAgenda {
  evidenciaId: string;
  hora: string;
  formato: Evidencia['formato'];
  foto?: string;
  texto: string;
  autorId: string;
  estado: Evidencia['estado'];
  entradas: EntradaAgenda[];
}

export interface PeriodoAgenda extends Periodo {
  registros: RegistroAgenda[];
}

/** El día elegido, ordenado por los períodos de la jornada. */
export function agendaDelDia(
  dia: string,
  evidencias: Evidencia[],
  sugerencias: Sugerencia[],
  nombreNino: (id: string | undefined) => string | undefined,
): PeriodoAgenda[] {
  const delDia = evidencias
    .filter((e) => e.creadaEn.slice(0, 10) === dia.slice(0, 10))
    .sort((a, b) => a.creadaEn.localeCompare(b.creadaEn));

  const periodos: PeriodoAgenda[] = JORNADA.map((p) => ({ ...p, registros: [] }));
  for (const e of delDia) {
    const hora = e.creadaEn.slice(11, 16) || '08:30';
    const suyas = sugerencias.filter((s) => s.evidenciaId === e.id && s.estado !== 'descartada');
    if (e.estado === 'lista' && suyas.length === 0) continue; // todo descartado
    const entradas: EntradaAgenda[] = suyas.map((s) => ({
      sugerenciaId: s.id,
      tipo: s.tipo,
      ninoId: s.ninoId,
      nombre:
        s.tipo === 'nota_sala'
          ? 'Toda la sala'
          : nombreNino(s.ninoId) ?? s.nombreDetectado ?? 'Por confirmar',
      nucleo: s.nucleo,
      nivel: s.nivel,
      pendiente: s.estado === 'pendiente',
    }));
    const texto = e.textoExtraido ?? suyas[0]?.cita ?? '';
    const periodo = periodos.find((p) => p.inicio === periodoDe(hora).inicio)!;
    periodo.registros.push({
      evidenciaId: e.id,
      hora,
      formato: e.formato,
      foto: e.foto,
      texto,
      autorId: e.autorId,
      estado: e.estado,
      entradas,
    });
  }
  return periodos;
}

/** Próximo registro del IEA (abril, agosto y noviembre) desde `hoy`. */
export function proximoIEA(hoy: string): { numero: 1 | 2 | 3; mes: string } {
  const mes = Number(hoy.slice(5, 7));
  if (mes <= 4) return { numero: 1, mes: 'abril' };
  if (mes <= 8) return { numero: 2, mes: 'agosto' };
  if (mes <= 11) return { numero: 3, mes: 'noviembre' };
  return { numero: 1, mes: 'abril' };
}
