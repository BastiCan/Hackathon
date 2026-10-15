import type { NucleoId } from '../lib/tipos';
import { PALETA } from './colores';

/**
 * Cada núcleo se pinta con el color de su ámbito de las BCEP, tomado de la
 * paleta oficial de Integra: rojo = Desarrollo Personal y Social, amarillo =
 * Comunicación Integral, verde = Interacción y Comprensión del Entorno. El azul
 * queda para la institución y las acciones.
 */
export type AmbitoId = 'dps' | 'com' | 'ent';

const AMBITO_DE: Record<NucleoId, AmbitoId> = {
  IA: 'dps',
  CC: 'dps',
  CM: 'dps',
  LV: 'com',
  LA: 'com',
  EN: 'ent',
  ES: 'ent',
  PM: 'ent',
};

export const NOMBRE_AMBITO: Record<AmbitoId, string> = {
  dps: 'Desarrollo personal y social',
  com: 'Comunicación integral',
  ent: 'Interacción y comprensión del entorno',
};

/** Color fuerte del ámbito (puntos, manchas y bordes), de la paleta oficial. */
export const COLOR_AMBITO: Record<AmbitoId, string> = {
  dps: PALETA.rojo,
  com: PALETA.amarillo,
  ent: PALETA.verde,
};

/** Texto oscuro de cada ámbito (AA sobre blanco y sobre su fondo suave). */
export const TEXTO_AMBITO: Record<AmbitoId, string> = {
  dps: '#A01810',
  com: '#6B5200',
  ent: '#2B5A0C',
};

/** Etiqueta suave del ámbito: fondo claro y texto oscuro (contraste AA). */
export const CLASE_ETIQUETA: Record<AmbitoId, string> = {
  dps: 'bg-ambito-dps text-ambito-dps-texto',
  com: 'bg-ambito-com text-ambito-com-texto',
  ent: 'bg-ambito-ent text-ambito-ent-texto',
};

export function ambitoDe(nucleo: NucleoId): AmbitoId {
  return AMBITO_DE[nucleo];
}

/** Abreviatura de 2 letras del núcleo para la planilla (IA, CC, LV…). */
export function abreviatura(nucleo: NucleoId): string {
  return nucleo;
}
