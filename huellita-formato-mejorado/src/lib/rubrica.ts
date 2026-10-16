/**
 * Carga y consulta de `data/rubrica_e1.json`: la ruta de 9 niveles y 5 dominios
 * del dataset E-1, la misma que usa el BFF local (`huellita-web`). Se genera con
 * `scripts/generar_datos_e1.py` desde el dataset sintético E-1, así el modo
 * local y el modo AWS muestran los mismos núcleos, niveles y conductas.
 *
 * La rúbrica es la única fuente de verdad: aquí no se escriben a mano niveles,
 * descripciones ni conductas observables (ver `.kiro/steering/rubrica.md`).
 */
import rubricaJson from '@data/rubrica_e1.json';
import type { CeldaRubrica, Manifestacion, Nivel, NivelInfo, NucleoId, NucleoInfo } from './tipos';

interface NivelJson {
  nivel: number;
  nombre: string;
  tramo_bcep: string;
  grupo_orientativo: string;
  edad_orientativa: string;
}

interface CeldaJson {
  nivel: number;
  nombre: string;
  descriptor: string;
  conductas_observables: string[];
  oa_referencia?: string[];
}

interface NucleoJson {
  codigo: string;
  nucleo: string;
  ambito: string;
  niveles: CeldaJson[];
}

interface RubricaJson {
  nota?: string;
  niveles: NivelJson[];
  rubrica: NucleoJson[];
}

const datos = rubricaJson as unknown as RubricaJson;

/** Sigla de 2 letras de la planilla, derivada del código del núcleo. */
const SIGLAS: Record<NucleoId, string> = {
  motor_grueso: 'MG',
  motor_fino: 'MF',
  lenguaje_comunicacion: 'LC',
  socioemocional: 'SE',
  cognitivo: 'CO',
};

/**
 * Un color por nivel, del cálido (1) al azul oscuro (9), en la familia de los
 * colores del logo de Integra. Cada uno cumple contraste AA con su color de
 * texto (`colorTextoNivel`): tinta del 1 al 7 y blanco en el 8 y el 9.
 * Definidos en `.kiro/steering/interfaz.md`.
 */
const COLORES_NIVEL: Record<Nivel, string> = {
  1: '#EF7A6A',
  2: '#F59E4C',
  3: '#F7CB4D',
  4: '#B7D351',
  5: '#72BE5B',
  6: '#3FB3A3',
  7: '#56A3E3',
  8: '#2F6BC4',
  9: '#233F86',
};

/** "0–2 meses" → { desde: 0, hasta: 2 }. Acepta guion normal o medio. */
function rangoEdad(texto: string): { desde: number; hasta: number } {
  const m = /(\d+)\s*[–—-]\s*(\d+)/.exec(texto);
  if (!m) throw new Error(`Rango de edad no reconocido en la rúbrica: "${texto}"`);
  return { desde: Number(m[1]), hasta: Number(m[2]) };
}

/**
 * Descripción integradora por nivel: el descriptor del primer núcleo
 * (motor grueso) en ese nivel, que en el dataset E-1 resume la ruta del tramo.
 */
const DESCRIPCION_POR_NIVEL = new Map<number, string>();
for (const celdaNivel of datos.rubrica[0]?.niveles ?? []) {
  DESCRIPCION_POR_NIVEL.set(celdaNivel.nivel, celdaNivel.descriptor);
}

const NIVELES: NivelInfo[] = datos.niveles
  .map((n) => {
    const { desde, hasta } = rangoEdad(n.edad_orientativa);
    return {
      nivel: n.nivel as Nivel,
      nombre: n.nombre,
      descripcion: DESCRIPCION_POR_NIVEL.get(n.nivel) ?? n.nombre,
      edadMinMeses: desde,
      edadMaxMeses: hasta,
      edadOrientativa: n.edad_orientativa,
    };
  })
  .sort((a, b) => a.nivel - b.nivel);

const NUCLEOS: NucleoInfo[] = datos.rubrica.map((n) => ({
  codigo: n.codigo as NucleoId,
  sigla: SIGLAS[n.codigo as NucleoId] ?? n.codigo,
  nombre: n.nucleo,
}));

const CELDAS = new Map<string, CeldaRubrica>();
for (const nucleo of datos.rubrica) {
  const sigla = SIGLAS[nucleo.codigo as NucleoId] ?? nucleo.codigo;
  for (const celdaNivel of nucleo.niveles) {
    // El dataset local no trae códigos de manifestación; se derivan como en el
    // backend (MAN-L09-MG-01) para conservar el mismo formato en la interfaz.
    const manifestaciones: Manifestacion[] = celdaNivel.conductas_observables.map((texto, i) => ({
      id: `MAN-L0${celdaNivel.nivel}-${sigla}-0${i + 1}`,
      texto,
    }));
    CELDAS.set(`${nucleo.codigo}:${celdaNivel.nivel}`, {
      nucleo: nucleo.codigo as NucleoId,
      nivel: celdaNivel.nivel as Nivel,
      nombreNivel: celdaNivel.nombre,
      descripcionNivel: celdaNivel.descriptor,
      conductas: celdaNivel.conductas_observables,
      manifestaciones,
    });
  }
}
for (const c of CELDAS.values()) {
  if (c.conductas.length === 0) {
    throw new Error(`La rúbrica no trae conductas para ${c.nucleo} en el nivel ${c.nivel}`);
  }
}

/** Nota del dataset local (apoyo pedagógico, no instrumento clínico). */
export function versionRubrica(): string {
  return datos.nota ?? 'E1-local';
}

/** Los 9 niveles con su nombre, descripción y rango de edad orientativa. */
export function niveles(): NivelInfo[] {
  return NIVELES;
}

/** Los núcleos, en el orden en que vienen en los datos (son configuración). */
export function nucleos(): NucleoInfo[] {
  return NUCLEOS;
}

/** Solo los códigos de los núcleos, en el mismo orden. */
export function codigosNucleos(): NucleoId[] {
  return NUCLEOS.map((n) => n.codigo);
}

/** Información de un nivel (nombre, descripción, rango de edad). */
export function nivelInfo(nivel: Nivel): NivelInfo {
  const info = NIVELES.find((n) => n.nivel === nivel);
  if (!info) throw new Error(`Nivel desconocido: ${nivel}`);
  return info;
}

/** Nombre del nivel, por ejemplo 9 → "Secuencias y autonomía creciente". */
export function nombreNivel(nivel: Nivel): string {
  return nivelInfo(nivel).nombre;
}

/** Descripción integradora del nivel. */
export function descripcionNivel(nivel: Nivel): string {
  return nivelInfo(nivel).descripcion;
}

/** Nombre visible del núcleo, por ejemplo "motor_fino" → "Motor fino". */
export function nombreNucleo(nucleo: NucleoId): string {
  return NUCLEOS.find((n) => n.codigo === nucleo)?.nombre ?? nucleo;
}

/** Sigla de la planilla, por ejemplo "lenguaje_comunicacion" → "LC". */
export function siglaNucleo(nucleo: NucleoId): string {
  return NUCLEOS.find((n) => n.codigo === nucleo)?.sigla ?? nucleo;
}

/** Celda completa de la rúbrica (nivel y conductas observables del núcleo). */
export function celda(nucleo: NucleoId, nivel: Nivel): CeldaRubrica {
  const c = CELDAS.get(`${nucleo}:${nivel}`);
  if (!c) throw new Error(`La rúbrica no tiene ${nucleo} en el nivel ${nivel}`);
  return c;
}

/** Conductas observables del núcleo en ese nivel. */
export function conductas(nucleo: NucleoId, nivel: Nivel): string[] {
  return celda(nucleo, nivel).conductas;
}

/** Color del nivel (números, etiquetas y puntos de nivel). */
export function colorNivel(nivel: Nivel): string {
  return COLORES_NIVEL[nivel];
}

/** Todas las celdas de la rúbrica, útil para buscar conductas por texto. */
export function todasLasCeldas(): CeldaRubrica[] {
  return [...CELDAS.values()];
}

/** El nivel más alto de la rúbrica (9). */
export function nivelMaximo(): Nivel {
  return NIVELES[NIVELES.length - 1].nivel;
}

/** Nivel siguiente, o el mismo si ya está en el último. */
export function nivelSiguiente(nivel: Nivel): Nivel {
  return (nivel < nivelMaximo() ? nivel + 1 : nivel) as Nivel;
}
