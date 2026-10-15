/**
 * Mancha: las formas orgánicas y planas de la gráfica institucional de Integra
 * (manual de imagen corporativa). Son puro adorno —ablandan las esquinas de
 * las tarjetas— así que nunca llevan información: van con `aria-hidden`, sin
 * capturar toques y en posición absoluta sobre un contenedor `relative` con
 * `overflow-hidden`.
 *
 * Uso:
 * ```tsx
 * <span className="relative overflow-hidden rounded-tarjeta">
 *   <Mancha color="#FFCD07" forma="b" opacidad={0.35} className="-right-3 -top-4 h-12 w-12" />
 *   …
 * </span>
 * ```
 */
export type FormaMancha = 'a' | 'b' | 'c';

/** Tres blobs distintos, sin borde ni degradado, dibujados en una caja 0–100. */
const FORMAS: Record<FormaMancha, string> = {
  a: 'M52 6c22 2 42 18 40 42s-20 44-46 44S4 72 8 46 30 4 52 6z',
  b: 'M58 3c24 0 40 20 39 46-1 25-18 48-44 48C27 97 5 77 5 51 5 24 34 3 58 3z',
  c: 'M46 4c26-3 51 14 51 41 1 28-22 52-48 51C24 95 3 73 4 47 5 23 21 7 46 4z',
};

export function Mancha({
  color,
  forma = 'a',
  opacidad = 1,
  className = '',
}: {
  /** Color plano de la paleta (token resuelto a hex o `currentColor`). */
  color: string;
  forma?: FormaMancha;
  /** 0 a 1. En fondos grandes conviene 0,06 o menos para no estorbar. */
  opacidad?: number;
  /** Posición y tamaño: `-right-4 -top-5 h-16 w-16`. */
  className?: string;
}) {
  return (
    <svg
      aria-hidden="true"
      focusable="false"
      viewBox="0 0 100 100"
      className={`pointer-events-none absolute ${className}`}
      style={{ opacity: opacidad }}
    >
      <path d={FORMAS[forma]} fill={color} />
    </svg>
  );
}
