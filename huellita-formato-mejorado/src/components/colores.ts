/**
 * Colores que el código necesita como valor (manchas, puntos y aros), siempre
 * tomados de la paleta oficial del manual de imagen corporativa de Integra.
 * Lo que se puede resolver con una clase de Tailwind usa el token, no estos
 * valores (ver `tailwind.config.js`).
 *
 * El aro del avatar mide hace cuánto no hay registro, nunca el desempeño del
 * niño/a (ver `.kiro/steering/producto.md`).
 */
import { colorNivel } from '../lib/rubrica';
import type { ColorFrescura, Nivel } from '../lib/tipos';

/** Paleta oficial (versión RGB para pantallas) y sus manchas. */
export const PALETA = {
  /** Pantone 300C. */
  azul: '#0063BD',
  /** Pantone 485C. */
  rojo: '#DD271D',
  /** Pantone 116C. */
  amarillo: '#FFCD07',
  /** Pantone 368C. */
  verde: '#67BC27',
  /** Mancha rosada de la gráfica institucional. */
  rosado: '#E43C84',
  /** Rosado oscurecido, para fondos con texto blanco (AA). */
  rosadoOscuro: '#C01E63',
  /** Mancha naranja: "por revisar" y "revisar avance". */
  naranjo: '#F07818',
  /** Naranjo oscuro para texto e íconos (AA sobre blanco y naranjo suave). */
  naranjoTexto: '#9A4708',
  /** Gris 80%: textos secundarios. */
  gris: '#58585A',
} as const;

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

/** "Revisar avance": la mancha naranja, en su versión oscura para íconos. */
export const NARANJO_TEXTO = PALETA.naranjoTexto;

export const TINTA = '#22262E';

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
 * claros o medios y piden tinta; del 7 al 9 son oscuros y piden blanco. Así el
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
