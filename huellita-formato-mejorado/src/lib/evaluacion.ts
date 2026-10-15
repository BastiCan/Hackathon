/**
 * Reglas de cálculo de Huellita. Todas las funciones son puras y reciben la
 * fecha "hoy" por parámetro para que la demo y las pruebas sean reproducibles
 * (ver `.kiro/steering/rubrica.md` y `data/semilla.json` → `fechaDemo`).
 */
import { codigosNucleos, conductas as conductasDe, niveles, nivelSiguiente } from './rubrica';
import type {
  ColorFrescura,
  EvaluacionValidada,
  Evidencia,
  Nino,
  Nivel,
  NucleoId,
  ResumenSala,
  Sugerencia,
  SugerenciaObservacion,
} from './tipos';

const MS_POR_DIA = 86_400_000;

interface PartesFecha {
  anio: number;
  mes: number;
  dia: number;
}

/** Lee la parte de fecha de un ISO (`YYYY-MM-DD` o `YYYY-MM-DDTHH:mm:ss`). */
function partes(iso: string): PartesFecha {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) throw new Error(`Fecha ISO no reconocida: "${iso}"`);
  return { anio: Number(m[1]), mes: Number(m[2]), dia: Number(m[3]) };
}

/** Día calendario como milisegundos UTC, para restar fechas sin zonas horarias. */
function aDiaUTC(iso: string): number {
  const { anio, mes, dia } = partes(iso);
  return Date.UTC(anio, mes - 1, dia);
}

/** Días calendario completos entre dos fechas (negativo si `hasta` es anterior). */
export function diasEntre(desde: string, hasta: string): number {
  return Math.round((aDiaUTC(hasta) - aDiaUTC(desde)) / MS_POR_DIA);
}

/** Meses completos cumplidos entre la fecha de nacimiento y la fecha de referencia. */
export function edadMeses(fechaNacimiento: string, hoy: string): number {
  const n = partes(fechaNacimiento);
  const h = partes(hoy);
  let meses = (h.anio - n.anio) * 12 + (h.mes - n.mes);
  if (h.dia < n.dia) meses -= 1;
  return Math.max(0, meses);
}

/** Edad en años y meses, para mostrar en la ficha ("3 años 2 meses"). */
export function edadAniosMeses(fechaNacimiento: string, hoy: string): { anios: number; meses: number } {
  const total = edadMeses(fechaNacimiento, hoy);
  return { anios: Math.floor(total / 12), meses: total % 12 };
}

/**
 * Niveles cuyo rango de edad orientativa contiene la edad, con la misma regla
 * del backend (`integra-backend/.kiro/steering/dominio.md`): los bordes son
 * inclusivos, así que en un borde caben dos (12 meses → [5, 6]). Sobre el
 * último rango (36 meses) queda el último nivel; bajo el primero, el primero.
 */
export function nivelesEsperados(edadEnMeses: number): Nivel[] {
  const lista = niveles();
  const dentro = lista
    .filter((n) => edadEnMeses >= n.edadMinMeses && edadEnMeses <= n.edadMaxMeses)
    .map((n) => n.nivel);
  if (dentro.length > 0) return dentro;
  return [edadEnMeses < lista[0].edadMinMeses ? lista[0].nivel : lista[lista.length - 1].nivel];
}

/** La edad pasa el último rango de la rúbrica (más de 36 meses). */
export function fueraDeRangoRubrica(edadEnMeses: number): boolean {
  const lista = niveles();
  return edadEnMeses > lista[lista.length - 1].edadMaxMeses;
}

/**
 * Nivel esperado por edad: el menor de `nivelesEsperados`. Es el mismo piso que
 * usa el backend para "bajo lo esperado" (nivel < mínimo), así que en un borde
 * de rango nunca se le pide de más a un niño/a.
 */
export function nivelEsperado(edadEnMeses: number): Nivel {
  return Math.min(...nivelesEsperados(edadEnMeses)) as Nivel;
}

/** Nivel esperado para la edad que tenía el niño/a en una fecha dada. */
export function nivelEsperadoEnFecha(fechaNacimiento: string, fecha: string): Nivel {
  return nivelEsperado(edadMeses(fechaNacimiento, fecha));
}

/** Evaluaciones de un núcleo, de la más reciente a la más antigua. */
function porFechaDesc(evaluaciones: EvaluacionValidada[]): EvaluacionValidada[] {
  return [...evaluaciones].sort((a, b) => (a.fecha < b.fecha ? 1 : a.fecha > b.fecha ? -1 : 0));
}

/**
 * Nivel actual de cada núcleo = nivel de la evaluación validada más reciente.
 * Los núcleos sin evidencia quedan en `null` (nunca en 0).
 */
export function nivelActualPorNucleo(
  evaluaciones: EvaluacionValidada[],
): Record<NucleoId, Nivel | null> {
  const resultado = {} as Record<NucleoId, Nivel | null>;
  for (const nucleo of codigosNucleos()) resultado[nucleo] = null;

  const masReciente = new Map<NucleoId, EvaluacionValidada>();
  for (const ev of evaluaciones) {
    const actual = masReciente.get(ev.nucleo);
    if (!actual || ev.fecha > actual.fecha) masReciente.set(ev.nucleo, ev);
  }
  for (const [nucleo, ev] of masReciente) resultado[nucleo] = ev.nivel;
  return resultado;
}

/** Mediana redondeada hacia abajo de los niveles de los núcleos con evidencia. */
export function nivelGeneral(nivelesPorNucleo: Record<NucleoId, Nivel | null>): Nivel | null {
  const valores = Object.values(nivelesPorNucleo)
    .filter((n): n is Nivel => n !== null)
    .sort((a, b) => a - b);
  if (valores.length === 0) return null;
  const medio = Math.floor(valores.length / 2);
  const mediana =
    valores.length % 2 === 1 ? valores[medio] : (valores[medio - 1] + valores[medio]) / 2;
  return Math.floor(mediana) as Nivel;
}

/**
 * Núcleos con bandera "revisar avance": las 2 últimas evaluaciones validadas del
 * núcleo, de fechas distintas, tienen cada una un nivel ≤ (nivel esperado para la
 * edad que tenía el niño/a **en la fecha de esa evidencia**) − 2.
 * Con una sola evaluación nunca se marca.
 */
export function revisarAvance(
  evaluaciones: EvaluacionValidada[],
  fechaNacimiento: string,
): NucleoId[] {
  const marcados: NucleoId[] = [];
  for (const nucleo of codigosNucleos()) {
    const delNucleo = porFechaDesc(evaluaciones.filter((e) => e.nucleo === nucleo));
    if (delNucleo.length < 2) continue;

    const ultima = delNucleo[0];
    const penultima = delNucleo[1];
    // Deben ser de fechas (días) distintas.
    if (diasEntre(penultima.fecha, ultima.fecha) === 0) continue;

    const estaBaja = (ev: EvaluacionValidada) =>
      ev.nivel <= nivelEsperadoEnFecha(fechaNacimiento, ev.fecha) - 2;

    if (estaBaja(ultima) && estaBaja(penultima)) marcados.push(nucleo);
  }
  return marcados;
}

/** Fecha de la última evaluación validada de cualquier núcleo. */
export function ultimaEvaluacion(evaluaciones: EvaluacionValidada[]): EvaluacionValidada | null {
  return porFechaDesc(evaluaciones)[0] ?? null;
}

/**
 * Frescura de la evidencia (no mide desempeño): días desde la última evaluación
 * validada. < 14 verde, 14–30 amarillo, > 30 o ninguna rojo.
 */
export function frescura(evaluaciones: EvaluacionValidada[], hoy: string): ColorFrescura {
  const ultima = ultimaEvaluacion(evaluaciones);
  if (!ultima) return 'rojo';
  const dias = diasEntre(ultima.fecha, hoy);
  if (dias < 14) return 'verde';
  if (dias <= 30) return 'amarillo';
  return 'rojo';
}

/** Días desde la última evaluación validada, o `null` si no hay ninguna. */
export function diasDesdeUltimaEvaluacion(
  evaluaciones: EvaluacionValidada[],
  hoy: string,
): number | null {
  const ultima = ultimaEvaluacion(evaluaciones);
  return ultima ? diasEntre(ultima.fecha, hoy) : null;
}

/**
 * "Observar ahora": toma el núcleo con la evidencia validada más antigua (o sin
 * evidencia) y propone 1–2 conductas observables del nivel siguiente al actual
 * de ese núcleo; si no hay evidencia, del nivel esperado por edad.
 */
export function observarAhora(
  evaluaciones: EvaluacionValidada[],
  nivelesActuales: Record<NucleoId, Nivel | null>,
  nivelEsperadoPorEdad: Nivel,
): SugerenciaObservacion | null {
  const nucleos = codigosNucleos();
  if (nucleos.length === 0) return null;

  const ultimaFecha = new Map<NucleoId, string>();
  for (const ev of evaluaciones) {
    const actual = ultimaFecha.get(ev.nucleo);
    if (!actual || ev.fecha > actual) ultimaFecha.set(ev.nucleo, ev.fecha);
  }

  // Primero los núcleos sin evidencia; luego el de evidencia más antigua.
  // El empate se resuelve por el orden de los núcleos en la rúbrica.
  let elegido: NucleoId = nucleos[0];
  let mejor: string | null = ultimaFecha.get(elegido) ?? null;
  for (const nucleo of nucleos.slice(1)) {
    const fecha = ultimaFecha.get(nucleo) ?? null;
    if (mejor === null) break;
    if (fecha === null || fecha < mejor) {
      elegido = nucleo;
      mejor = fecha;
    }
  }

  const actual = nivelesActuales[elegido] ?? null;
  const nivel = actual === null ? nivelEsperadoPorEdad : nivelSiguiente(actual);
  return { nucleo: elegido, nivel, conductas: conductasDe(elegido, nivel).slice(0, 2) };
}

/**
 * Resumen de la sala: cuántos niños/as tienen un registro validado en los
 * últimos 30 días (el mismo corte del semáforo y de la vista directora, para
 * que ambas pantallas den el mismo número) y cuál es el núcleo menos cubierto
 * (el que tiene evidencia validada de menos niños/as distintos; empate por el
 * orden de la rúbrica). `observadosMes` conserva su nombre por compatibilidad.
 */
export function resumenSala(
  ninos: Nino[],
  evaluaciones: EvaluacionValidada[],
  hoy: string,
): ResumenSala {
  const activos = ninos.filter((n) => n.activo);
  const idsActivos = new Set(activos.map((n) => n.id));
  const delaSala = evaluaciones.filter((e) => idsActivos.has(e.ninoId));

  const observados = new Set(
    delaSala.filter((e) => diasEntre(e.fecha, hoy) <= 30).map((e) => e.ninoId),
  );

  let nucleoMenosCubierto: NucleoId | null = null;
  let menor = Number.POSITIVE_INFINITY;
  for (const nucleo of codigosNucleos()) {
    const cubiertos = new Set(delaSala.filter((e) => e.nucleo === nucleo).map((e) => e.ninoId)).size;
    if (cubiertos < menor) {
      menor = cubiertos;
      nucleoMenosCubierto = nucleo;
    }
  }

  return { observadosMes: observados.size, total: activos.length, nucleoMenosCubierto };
}

/**
 * Convierte sugerencias validadas (aceptadas o cambiadas) en evaluaciones, con
 * la fecha de la evidencia que las originó.
 */
export function evaluacionesValidadas(
  sugerencias: Sugerencia[],
  evidencias: Evidencia[],
): EvaluacionValidada[] {
  const porId = new Map(evidencias.map((e) => [e.id, e]));
  const resultado: EvaluacionValidada[] = [];

  for (const s of sugerencias) {
    if (s.tipo !== 'evaluacion') continue;
    if (s.estado !== 'aceptada' && s.estado !== 'cambiada') continue;
    if (!s.ninoId || !s.nucleo || !s.nivel) continue;

    const evidencia = porId.get(s.evidenciaId);
    const fecha = evidencia?.creadaEn ?? s.validadaEn;
    if (!fecha) continue;

    resultado.push({
      sugerenciaId: s.id,
      evidenciaId: s.evidenciaId,
      ninoId: s.ninoId,
      salaId: s.salaId,
      nucleo: s.nucleo,
      nivel: s.nivel,
      fecha,
      conducta: s.conducta,
      cita: s.cita,
      validadaPor: s.validadaPor,
    });
  }
  return resultado;
}

/** Evaluaciones de un niño/a. */
export function evaluacionesDe(
  evaluaciones: EvaluacionValidada[],
  ninoId: string,
): EvaluacionValidada[] {
  return porFechaDesc(evaluaciones.filter((e) => e.ninoId === ninoId));
}
