/**
 * Modelos de vista: funciones puras que convierten los datos del dominio en lo
 * que muestran las pantallas (textos, orden, conteos y colores). Están aquí
 * para poder probarlas sin montar componentes.
 *
 * Los nombres de niveles y núcleos salen siempre de la rúbrica; aquí no se
 * escribe contenido pedagógico a mano (ver `.kiro/steering/rubrica.md`).
 */
import {
  diasDesdeUltimaEvaluacion,
  evaluacionesDe,
  frescura,
  nivelActualPorNucleo,
  nivelGeneral,
  revisarAvance,
} from './evaluacion';
import { codigosNucleos, colorNivel, nombreNivel, nombreNucleo, siglaNucleo } from './rubrica';
import type {
  Certeza,
  ColorFrescura,
  EvaluacionValidada,
  Formato,
  Nino,
  Nivel,
  NucleoId,
  ResumenSala,
  Sugerencia,
  SugerenciaObservacion,
} from './tipos';

const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

const DIAS_SEMANA = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];

const MESES_LARGOS = [
  'enero',
  'febrero',
  'marzo',
  'abril',
  'mayo',
  'junio',
  'julio',
  'agosto',
  'septiembre',
  'octubre',
  'noviembre',
  'diciembre',
];

/** Iniciales del avatar: las dos primeras letras del nombre de pila. */
export function iniciales(nombre: string): string {
  return nombre.trim().slice(0, 2).toLocaleUpperCase('es-CL');
}

/** Iniciales de la usuaria: una letra por palabra ("Tía Ana" → "TA"). */
export function inicialesUsuaria(nombre: string): string {
  return nombre
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p[0]?.toLocaleUpperCase('es-CL') ?? '')
    .join('');
}

/** "2026-10-13" → "13 oct". */
export function fechaCorta(iso: string): string {
  const partes = iso.slice(0, 10).split('-');
  return `${Number(partes[2])} ${MESES[Number(partes[1]) - 1]}`;
}

/** "2026-10-15" → "Jueves 15 de octubre" (encabezado de Mi sala). */
export function fechaLarga(iso: string): string {
  const [anio, mes, dia] = iso.slice(0, 10).split('-').map(Number);
  const nombreDia = DIAS_SEMANA[new Date(Date.UTC(anio, mes - 1, dia)).getUTCDay()];
  return `${nombreDia} ${dia} de ${MESES_LARGOS[mes - 1]}`;
}

/** Hora en formato 24 h, o cadena vacía si la fecha no la trae. */
export function hora(iso: string): string {
  const m = /T(\d{2}):(\d{2})/.exec(iso);
  return m ? `${m[1]}:${m[2]}` : '';
}

/** Origen de una evidencia: "Hoy, 09:12", "Ayer, 15:20" o "13 oct, 11:05". */
export function cuando(iso: string, hoy: string): string {
  const dia = iso.slice(0, 10);
  const hhmm = hora(iso);
  const sufijo = hhmm ? `, ${hhmm}` : '';
  if (dia === hoy.slice(0, 10)) return `Hoy${sufijo}`;
  const [anio, mes, diaHoy] = hoy.slice(0, 10).split('-').map(Number);
  const ayer = new Date(Date.UTC(anio, mes - 1, diaHoy - 1)).toISOString().slice(0, 10);
  if (dia === ayer) return `Ayer${sufijo}`;
  return `${fechaCorta(dia)}${sufijo}`;
}

/** Etiqueta del formato de la evidencia, como en el prototipo. */
export function etiquetaFormato(formato: Formato): string {
  if (formato === 'foto') return 'Foto de post-it';
  if (formato === 'audio') return 'Audio';
  return 'Nota escrita';
}

/** Certeza en palabras de la tía; nunca porcentajes (requisito 3.7). */
export function textoCerteza(certeza: Certeza): string {
  if (certeza === 'alta') return 'Alta';
  if (certeza === 'media') return 'Media';
  return 'Baja';
}

export interface TarjetaNinoVista {
  id: string;
  nombre: string;
  /** "Josefa R." para la planilla. */
  nombreCorto: string;
  iniciales: string;
  /** Nivel actual de cada núcleo (planilla de la sala). */
  niveles: Record<NucleoId, Nivel | null>;
  /** Núcleos en "revisar avance". */
  marcados: NucleoId[];
  frescura: ColorFrescura;
  /** Días desde la última evaluación validada; `null` si no tiene ninguna. */
  dias: number | null;
  nivelGeneral: Nivel | null;
  revisarAvance: boolean;
}

/** Una tarjeta por niño/a activo de la sala, en el orden en que vienen. */
export function tarjetasDeSala(
  ninos: Nino[],
  evaluaciones: EvaluacionValidada[],
  hoy: string,
): TarjetaNinoVista[] {
  return ninos
    .filter((n) => n.activo)
    .map((nino) => {
      const suyas = evaluacionesDe(evaluaciones, nino.id);
      const niveles = nivelActualPorNucleo(suyas);
      const marcados = revisarAvance(suyas, nino.fechaNacimiento);
      return {
        id: nino.id,
        nombre: nino.nombre,
        nombreCorto: nino.apellidoInicial ? `${nino.nombre} ${nino.apellidoInicial}` : nino.nombre,
        iniciales: iniciales(nino.nombre),
        niveles,
        marcados,
        frescura: frescura(suyas, hoy),
        dias: diasDesdeUltimaEvaluacion(suyas, hoy),
        nivelGeneral: nivelGeneral(niveles),
        revisarAvance: marcados.length > 0,
      };
    });
}

export type FiltroSala = 'todos' | 'sin-registro' | 'revisar-avance';

export interface ConteosFiltro {
  todos: number;
  sinRegistro: number;
  revisarAvance: number;
}

export function conteosFiltro(tarjetas: TarjetaNinoVista[]): ConteosFiltro {
  return {
    todos: tarjetas.length,
    sinRegistro: tarjetas.filter((t) => t.frescura === 'rojo').length,
    revisarAvance: tarjetas.filter((t) => t.revisarAvance).length,
  };
}

export function filtrarTarjetas(
  tarjetas: TarjetaNinoVista[],
  filtro: FiltroSala,
): TarjetaNinoVista[] {
  if (filtro === 'sin-registro') return tarjetas.filter((t) => t.frescura === 'rojo');
  if (filtro === 'revisar-avance') return tarjetas.filter((t) => t.revisarAvance);
  return tarjetas;
}

/** Línea de resumen de la sala, con los textos del prototipo. */
export function textoResumenSala(resumen: ResumenSala): string {
  const partes = partesResumenSala(resumen);
  return `Observados en 30 días: ${partes.observados} · Menos registrado: ${partes.menos}`;
}

/**
 * Las dos partes que el prototipo muestra en negrita dentro de la línea de
 * resumen de la sala ("14 de 18" y el núcleo).
 */
export function partesResumenSala(resumen: ResumenSala): { observados: string; menos: string } {
  return {
    observados: `${resumen.observadosMes} de ${resumen.total}`,
    menos: resumen.nucleoMenosCubierto ? nombreNucleo(resumen.nucleoMenosCubierto) : '—',
  };
}

export interface TarjetaSalaVista {
  id: string;
  nombre: string;
  /** Niños/as activos de la sala. */
  total: number;
  /** Con al menos un registro validado en los últimos 30 días. */
  observados30: number;
  /** Porcentaje redondeado de observados en 30 días. */
  porcentaje: number;
  revisarAvance: number;
  nucleoMenosCubierto: NucleoId | null;
  nombreNucleoMenosCubierto: string | null;
}

/**
 * Tarjeta de una sala para la vista directora: cuántos niños/as tiene, cuántos
 * se observaron en los últimos 30 días, cuántos están en "revisar avance" y
 * cuál es el núcleo menos cubierto.
 *
 * El 30 es el mismo corte del semáforo de frescura: "observado" = tiene una
 * evidencia validada de hace 30 días o menos (aro verde o amarillo).
 */
export function tarjetaSala(
  sala: { id: string; nombre: string },
  ninos: Nino[],
  evaluaciones: EvaluacionValidada[],
  hoy: string,
  nucleoMenosCubierto: NucleoId | null,
): TarjetaSalaVista {
  const tarjetas = tarjetasDeSala(ninos, evaluaciones, hoy);
  const total = tarjetas.length;
  const observados30 = tarjetas.filter((t) => t.dias !== null && t.dias <= 30).length;
  return {
    id: sala.id,
    nombre: sala.nombre,
    total,
    observados30,
    porcentaje: total === 0 ? 0 : Math.round((observados30 / total) * 100),
    revisarAvance: tarjetas.filter((t) => t.revisarAvance).length,
    nucleoMenosCubierto,
    nombreNucleoMenosCubierto: nucleoMenosCubierto ? nombreNucleo(nucleoMenosCubierto) : null,
  };
}

/** Descripción accesible de una tarjeta de niño/a (va en `aria-label`). */
export function etiquetaTarjeta(t: TarjetaNinoVista): string {
  const partes = [t.nombre];
  partes.push(t.nivelGeneral ? `nivel ${t.nivelGeneral}` : 'sin nivel todavía');
  partes.push(
    t.dias === null
      ? 'sin registros'
      : t.dias === 0
        ? 'registrado hoy'
        : `${t.dias} ${t.dias === 1 ? 'día' : 'días'} desde el último registro`,
  );
  if (t.revisarAvance) partes.push('revisar avance');
  return partes.join(', ');
}

export interface NucleoVista {
  nucleo: NucleoId;
  nombre: string;
  nivel: Nivel | null;
  nombreNivel: string | null;
  color: string | null;
  revisarAvance: boolean;
}

/** Todos los núcleos con su nivel actual, en el orden de la rúbrica. */
export function nucleosDeFicha(
  evaluaciones: EvaluacionValidada[],
  fechaNacimiento: string,
): NucleoVista[] {
  const niveles = nivelActualPorNucleo(evaluaciones);
  const marcados = new Set(revisarAvance(evaluaciones, fechaNacimiento));
  return codigosNucleos().map((nucleo) => {
    const nivel = niveles[nucleo];
    return {
      nucleo,
      nombre: nombreNucleo(nucleo),
      nivel,
      nombreNivel: nivel ? nombreNivel(nivel) : null,
      color: nivel ? colorNivel(nivel) : null,
      revisarAvance: marcados.has(nucleo),
    };
  });
}

/**
 * Resumen de 2 líneas por plantilla (en la Fase 3 lo escribe la IA): dónde va
 * mejor y qué conviene observar. Sin lenguaje clínico ni la palabra "rezago".
 */
export function resumenFicha(
  nombre: string,
  nucleos: NucleoVista[],
  observar: SugerenciaObservacion | null,
): string {
  const conEvidencia = nucleos.filter((n) => n.nivel !== null);
  if (conEvidencia.length === 0) {
    return `Todavía no hay registros de ${nombre}. Registra algo que le hayas visto hacer y Huellita lo ordena.`;
  }
  const marcado = nucleos.find((n) => n.revisarAvance);
  const candidatos = conEvidencia.filter((n) => !n.revisarAvance);
  const mejor = (candidatos.length > 0 ? candidatos : conEvidencia).reduce((a, b) =>
    (b.nivel ?? 0) > (a.nivel ?? 0) ? b : a,
  );
  const primera = `Avanza bien en ${mejor.nombre}.`;
  // Si un núcleo está en "revisar avance", eso es lo primero que la tía debe ver.
  if (marcado && marcado.nucleo !== mejor.nucleo) {
    return `${primera} Conviene acompañar de cerca ${marcado.nombre}.`;
  }
  const porObservar = observar ? nombreNucleo(observar.nucleo) : null;
  if (!porObservar || porObservar === mejor.nombre) return primera;
  return `${primera} Conviene observar más ${porObservar}.`;
}

/**
 * Orden de "Cómo va": primero los núcleos en "revisar avance", luego los que
 * tienen registros y al final los que aún no tienen. Dentro de cada grupo se
 * mantiene el orden de la rúbrica.
 */
export function ordenarNucleosFicha(nucleos: NucleoVista[]): NucleoVista[] {
  const grupo = (n: NucleoVista) => (n.revisarAvance ? 0 : n.nivel !== null ? 1 : 2);
  return nucleos
    .map((n, i) => ({ n, i }))
    .sort((a, b) => grupo(a.n) - grupo(b.n) || a.i - b.i)
    .map(({ n }) => n);
}

export interface RegistroVista {
  id: string;
  fecha: string;
  fechaCorta: string;
  nucleo: NucleoId;
  nombreNucleo: string;
  /** Sigla del núcleo para la tira de registros ("LC"). */
  sigla: string;
  nivel: Nivel;
  /** Color del nivel (punto de la línea de tiempo). */
  color: string;
  autora: string;
  cita: string;
  /** Tipo y foto de la evidencia, para la tira de registros de la ficha. */
  formato?: Formato;
  foto?: string;
}

/**
 * Historial de un niño/a, de lo más reciente a lo más antiguo.
 * @param nombreAutora resuelve el ID de la tía que validó a su nombre visible.
 */
export function historialVista(
  evaluaciones: EvaluacionValidada[],
  nombreAutora: (id: string | undefined) => string,
  evidenciaDe: (id: string) => { formato: Formato; foto?: string } | undefined = () => undefined,
): RegistroVista[] {
  return evaluaciones.map((e) => ({
    formato: evidenciaDe(e.evidenciaId)?.formato,
    foto: evidenciaDe(e.evidenciaId)?.foto,
    id: e.sugerenciaId,
    fecha: e.fecha,
    fechaCorta: fechaCorta(e.fecha),
    nucleo: e.nucleo,
    nombreNucleo: nombreNucleo(e.nucleo),
    sigla: siglaNucleo(e.nucleo),
    nivel: e.nivel,
    color: colorNivel(e.nivel),
    autora: nombreAutora(e.validadaPor),
    cita: e.cita,
  }));
}


/** Una nota de la sala (observacion general) ya guardada, para listarla y editarla. */
export interface NotaSalaVista {
  sugerenciaId: string;
  evidenciaId: string;
  fecha: string;
  fechaCorta: string;
  /** Texto mostrado: el de la evidencia si existe, si no la cita. */
  texto: string;
  autora: string;
}

/**
 * Notas de la sala validadas (aceptadas o cambiadas), de la mas reciente a la
 * mas antigua. Son las observaciones generales que no son de un nino en
 * particular. El texto sale de la evidencia (lo transcrito/escrito) y, si no
 * esta, de la cita de la sugerencia.
 */
export function notasSalaVista(
  sugerencias: Sugerencia[],
  nombreAutora: (id: string | undefined) => string,
  textoEvidencia: (id: string) => string | undefined = () => undefined,
  fechaEvidencia: (id: string) => string | undefined = () => undefined,
): NotaSalaVista[] {
  return sugerencias
    .filter((s) => s.tipo === 'nota_sala' && (s.estado === 'aceptada' || s.estado === 'cambiada'))
    .map((s) => {
      const fecha = fechaEvidencia(s.evidenciaId) ?? s.validadaEn ?? '';
      return {
        sugerenciaId: s.id,
        evidenciaId: s.evidenciaId,
        fecha,
        fechaCorta: fecha ? fechaCorta(fecha) : '',
        texto: textoEvidencia(s.evidenciaId) ?? s.cita,
        autora: nombreAutora(s.validadaPor),
      };
    })
    .sort((a, b) => (a.fecha < b.fecha ? 1 : a.fecha > b.fecha ? -1 : 0));
}