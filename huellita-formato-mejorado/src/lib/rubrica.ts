/**
 * Carga y consulta de `data/rubrica_e1.json`: la ruta de 9 niveles y 5 dominios
 * del dataset E-1, la misma que usa la IA del backend (integra-procesador). Se
 * genera con `scripts/generar_datos_e1.py`.
 * La rúbrica es la única fuente de verdad: aquí no se escriben a mano niveles,
 * descriptores ni conductas observables (ver `.kiro/steering/rubrica.md`).
 */
import rubricaJson from '@data/rubrica_e1.json';
import type { CeldaRubrica, Nivel, NivelInfo, NucleoId, NucleoInfo } from './tipos';

interface NivelJson {
  nivel: number;
  nombre: string;
  tramo_bcep: string;
  grupo_orientativo: string;
  edad_orientativa: string;
}

interface NucleoJson {
  codigo: string;
  nucleo: string;
  ambito: string;
  niveles: {
    nivel: number;
    nombre: string;
    descriptor: string;
    conductas_observables: string[];
    oa_referencia?: string[];
  }[];
}

interface RubricaJson {
  nota?: string;
  niveles: NivelJson[];
  rubrica: NucleoJson[];
}

const datos = rubricaJson as unknown as RubricaJson;

/**
 * Colores de nivel definidos en `.kiro/steering/interfaz.md`, más un morado
 * oscuro para el nivel 9 (lleva texto blanco, contraste AA).
 */
const COLORES_NIVEL: Record<Nivel, string> = {
  1: '#E8664F',
  2: '#F08A3E',
  3: '#F2C14E',
  4: '#9BC53D',
  5: '#5A9E3A',
  6: '#3A9E9A',
  7: '#3D7DD8',
  8: '#1F3B6B',
  9: '#5B3A8E',
};

/** "32–40 meses" → { desde: 32, hasta: 40 }. Acepta guion normal o medio. */
function rangoEdad(texto: string): { desde: number; hasta: number } {
  const m = /(\d+)\s*[–—-]\s*(\d+)/.exec(texto);
  if (!m) throw new Error(`Rango de edad no reconocido en la rúbrica: "${texto}"`);
  return { desde: Number(m[1]), hasta: Number(m[2]) };
}

const NIVELES: NivelInfo[] = datos.niveles
  .map((n) => {
    const { desde, hasta } = rangoEdad(n.edad_orientativa);
    return {
      nivel: n.nivel as Nivel,
      nombre: n.nombre,
      tramo: n.tramo_bcep,
      grupoOrientativo: n.grupo_orientativo,
      edadDesdeMeses: desde,
      edadHastaMeses: hasta,
      edadOrientativa: n.edad_orientativa,
    };
  })
  .sort((a, b) => a.nivel - b.nivel);

const NUCLEOS: NucleoInfo[] = datos.rubrica.map((n) => ({
  codigo: n.codigo as NucleoId,
  nombre: n.nucleo,
  ambito: n.ambito,
}));

const CELDAS = new Map<string, CeldaRubrica>();
for (const nucleo of datos.rubrica) {
  for (const celda of nucleo.niveles) {
    CELDAS.set(`${nucleo.codigo}:${celda.nivel}`, {
      nucleo: nucleo.codigo as NucleoId,
      nivel: celda.nivel as Nivel,
      nombreNivel: celda.nombre,
      descriptor: celda.descriptor,
      conductas: celda.conductas_observables,
      oaReferencia: celda.oa_referencia ?? [],
    });
  }
}

/** Los niveles con su nombre y rango de edad orientativa. */
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

/** Información de un nivel (nombre, tramo, rango de edad). */
export function nivelInfo(nivel: Nivel): NivelInfo {
  const info = NIVELES.find((n) => n.nivel === nivel);
  if (!info) throw new Error(`Nivel desconocido: ${nivel}`);
  return info;
}

/** Nombre del nivel, por ejemplo 9 → "Secuencias y autonomía creciente". */
export function nombreNivel(nivel: Nivel): string {
  return nivelInfo(nivel).nombre;
}

/** Nombre del núcleo, por ejemplo "lenguaje_comunicacion" → "Lenguaje y comunicación". */
export function nombreNucleo(nucleo: NucleoId): string {
  return NUCLEOS.find((n) => n.codigo === nucleo)?.nombre ?? nucleo;
}

/** Celda completa de la rúbrica (descriptor, conductas y OA de referencia). */
export function celda(nucleo: NucleoId, nivel: Nivel): CeldaRubrica {
  const c = CELDAS.get(`${nucleo}:${nivel}`);
  if (!c) throw new Error(`La rúbrica no tiene ${nucleo} en el nivel ${nivel}`);
  return c;
}

/** Descriptor del núcleo en ese nivel. */
export function descriptor(nucleo: NucleoId, nivel: Nivel): string {
  return celda(nucleo, nivel).descriptor;
}

/** Conductas observables del núcleo en ese nivel. */
export function conductas(nucleo: NucleoId, nivel: Nivel): string[] {
  return celda(nucleo, nivel).conductas;
}

/** Color del nivel (solo para barras y etiquetas de nivel). */
export function colorNivel(nivel: Nivel): string {
  return COLORES_NIVEL[nivel];
}

/** Todas las celdas de la rúbrica, útil para buscar conductas por texto. */
export function todasLasCeldas(): CeldaRubrica[] {
  return [...CELDAS.values()];
}

/** Nivel más alto de la rúbrica. */
const NIVEL_MAXIMO = NIVELES[NIVELES.length - 1].nivel;

/** Nivel siguiente, o el mismo si ya está en el más alto. */
export function nivelSiguiente(nivel: Nivel): Nivel {
  return (nivel < NIVEL_MAXIMO ? nivel + 1 : NIVEL_MAXIMO) as Nivel;
}
