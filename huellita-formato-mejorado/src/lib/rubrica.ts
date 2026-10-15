/**
 * Carga y consulta de la rúbrica E-1, la misma que usa el backend:
 * `data/rubrica_e1.json` es copia exacta de
 * `integra-backend/data/processed/rubrica.json` (5 núcleos × 9 niveles,
 * 90 conductas observables). `data/nucleos_e1.json` agrega solo lo que el
 * backend no trae: el nombre visible y la sigla de cada núcleo.
 *
 * La rúbrica es la única fuente de verdad: aquí no se escriben a mano niveles,
 * descripciones ni conductas observables (ver `.kiro/steering/rubrica.md`).
 */
import rubricaJson from '@data/rubrica_e1.json';
import nucleosJson from '@data/nucleos_e1.json';
import type {
  CeldaRubrica,
  Manifestacion,
  Nivel,
  NivelInfo,
  NucleoId,
  NucleoInfo,
} from './tipos';

interface NivelJson {
  nivel: number;
  nombre_nivel: string;
  edad_min_meses: number;
  edad_max_meses: number;
  descripcion: string;
}

interface ManifestacionJson {
  nivel: number;
  dominio: string;
  texto_observable: string;
}

interface RubricaJson {
  version: string;
  dominios: string[];
  niveles: NivelJson[];
  manifestaciones: Record<string, ManifestacionJson>;
}

interface NucleosJson {
  nucleos: { dominio: string; sigla: string; nombre: string }[];
}

const datos = rubricaJson as unknown as RubricaJson;
const presentacion = nucleosJson as unknown as NucleosJson;

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

const NIVELES: NivelInfo[] = datos.niveles
  .map((n) => ({
    nivel: n.nivel as Nivel,
    nombre: n.nombre_nivel,
    descripcion: n.descripcion,
    edadMinMeses: n.edad_min_meses,
    edadMaxMeses: n.edad_max_meses,
    edadOrientativa: `${n.edad_min_meses}–${n.edad_max_meses} meses`,
  }))
  .sort((a, b) => a.nivel - b.nivel);

const NUCLEOS: NucleoInfo[] = datos.dominios.map((dominio) => {
  const visible = presentacion.nucleos.find((n) => n.dominio === dominio);
  if (!visible) throw new Error(`Falta el nombre visible del núcleo "${dominio}" en nucleos_e1.json`);
  return { codigo: dominio as NucleoId, sigla: visible.sigla, nombre: visible.nombre };
});

const CELDAS = new Map<string, CeldaRubrica>();
for (const nucleo of NUCLEOS) {
  for (const info of NIVELES) {
    CELDAS.set(`${nucleo.codigo}:${info.nivel}`, {
      nucleo: nucleo.codigo,
      nivel: info.nivel,
      nombreNivel: info.nombre,
      descripcionNivel: info.descripcion,
      conductas: [],
      manifestaciones: [],
    });
  }
}
// Las conductas en el orden de su código (…-01 antes que …-02).
for (const id of Object.keys(datos.manifestaciones).sort()) {
  const m = datos.manifestaciones[id];
  const c = CELDAS.get(`${m.dominio}:${m.nivel}`);
  if (!c) throw new Error(`La manifestación ${id} apunta a un núcleo o nivel que no existe`);
  const manifestacion: Manifestacion = { id, texto: m.texto_observable };
  c.manifestaciones.push(manifestacion);
  c.conductas.push(manifestacion.texto);
}
for (const c of CELDAS.values()) {
  if (c.conductas.length === 0) {
    throw new Error(`La rúbrica no trae conductas para ${c.nucleo} en el nivel ${c.nivel}`);
  }
}

/** Versión de la rúbrica del backend ("E1-2026-10-13"). */
export function versionRubrica(): string {
  return datos.version;
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
