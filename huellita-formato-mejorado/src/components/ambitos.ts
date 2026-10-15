import type { NucleoId } from '../lib/tipos';
import { PALETA } from './colores';

/**
 * Cada núcleo (dominio del dataset E-1) se pinta con el color de su ámbito de
 * las BCEP, tomado de la paleta oficial de Integra: rojo = Desarrollo Personal y
 * Social (motor grueso, motor fino y socioemocional, como Corporalidad y
 * Movimiento e Identidad y Autonomía), amarillo = Comunicación Integral
 * (lenguaje), verde = Interacción y Comprensión del Entorno (cognitivo). El azul
 * queda para la institución y las acciones.
 */
export type AmbitoId = 'dps' | 'com' | 'ent';

const AMBITO_DE: Record<NucleoId, AmbitoId> = {
  motor_grueso: 'dps',
  motor_fino: 'dps',
  lenguaje_comunicacion: 'com',
  socioemocional: 'dps',
  cognitivo: 'ent',
};

/** Abreviatura de 2 letras de cada núcleo, la misma de los códigos de manifestación (MAN-L09-CO-02). */
const ABREVIATURA: Record<NucleoId, string> = {
  motor_grueso: 'MG',
  motor_fino: 'MF',
  lenguaje_comunicacion: 'LC',
  socioemocional: 'SE',
  cognitivo: 'CO',
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

/** Abreviatura de 2 letras del núcleo para la planilla (MG, MF, LC, SE, CO). */
export function abreviatura(nucleo: NucleoId): string {
  return ABREVIATURA[nucleo] ?? nucleo;
}
