/**
 * Colores de frescura y sus textos. El aro del avatar mide hace cuánto no hay
 * registro, nunca el desempeño del niño/a (ver `.kiro/steering/producto.md`).
 */
import { colorNivel } from '../lib/rubrica';
import type { ColorFrescura, Nivel } from '../lib/tipos';

export const COLOR_FRESCURA: Record<ColorFrescura, string> = {
  verde: '#2E9E5B',
  amarillo: '#E0A800',
  rojo: '#D64545',
};

export const TEXTO_FRESCURA: Record<ColorFrescura, string> = {
  verde: 'Registrado en las últimas 2 semanas',
  amarillo: 'Entre 2 semanas y 1 mes sin registro',
  rojo: 'Más de 1 mes sin registro',
};

export const AMBAR = '#B86E00';

export const TINTA = '#1E2A55';

/** Mezcla un color con blanco: `proporcion` 0,22 deja un pastel del original. */
export function mezclarConBlanco(hex: string, proporcion: number): string {
  const n = Number.parseInt(hex.replace('#', ''), 16);
  const canales = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((c) =>
    Math.round(c * proporcion + 255 * (1 - proporcion)),
  );
  return `#${canales.map((c) => c.toString(16).padStart(2, '0')).join('')}`;
}

/**
 * Color de texto legible sobre el color de un nivel. Los niveles 1 a 6 son
 * claros o medios y piden tinta; el 7 y el 8 son oscuros y piden blanco. Así el
 * número grande de nivel cumple contraste AA sin cambiar la paleta (tarea 10).
 */
export function colorTextoNivel(nivel: Nivel): string {
  return nivel >= 7 ? '#FFFFFF' : TINTA;
}

/** Fondo pastel del chip "N4": el color del nivel aclarado para llevar texto. */
export function colorChipNivel(nivel: Nivel): { fondo: string; borde: string } {
  const color = colorNivel(nivel);
  return { fondo: mezclarConBlanco(color, 0.24), borde: color };
}
