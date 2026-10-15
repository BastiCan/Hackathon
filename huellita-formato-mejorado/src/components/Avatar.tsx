import type { CSSProperties } from 'react';
import type { ColorFrescura } from '../lib/tipos';
import { COLOR_FRESCURA } from './colores';

/**
 * Avatar circular con iniciales. Nunca se muestran fotos de caras de niños o
 * niñas (privacidad.md 2). Si se indica la frescura, lleva un borde de ese
 * color: solo mide hace cuánto no hay registro, no cómo le va al niño/a.
 */
export function Avatar({
  iniciales,
  frescura,
  tamano = 44,
  className = '',
}: {
  iniciales: string;
  frescura?: ColorFrescura;
  tamano?: number;
  className?: string;
}) {
  const estilo: CSSProperties = {
    width: tamano,
    height: tamano,
    fontSize: Math.round(tamano / 2.8),
    ...(frescura ? { boxShadow: `0 0 0 2px #fff, 0 0 0 4px ${COLOR_FRESCURA[frescura]}` } : {}),
  };
  return (
    <span
      aria-hidden="true"
      style={estilo}
      className={`grid flex-none place-items-center rounded-full bg-integra-claro font-bold text-integra-oscuro ${className}`}
    >
      {iniciales}
    </span>
  );
}
