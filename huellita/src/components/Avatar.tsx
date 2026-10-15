import type { CSSProperties } from 'react';
import type { ColorFrescura } from '../lib/tipos';
import { COLOR_FRESCURA } from './colores';

/**
 * Avatar circular con iniciales. Nunca se muestran fotos de caras de niños o
 * niñas (privacidad.md 2). El aro de color indica la frescura del registro.
 */
export function Avatar({
  iniciales,
  frescura,
  tamano = 54,
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
    fontSize: Math.round(tamano / 3),
    ...(frescura ? ({ '--aro': COLOR_FRESCURA[frescura] } as CSSProperties) : {}),
  };
  return (
    <span
      aria-hidden="true"
      style={estilo}
      className={`grid flex-none place-items-center rounded-full bg-integra-claro font-display font-semibold text-integra-oscuro ${
        frescura ? 'aro' : ''
      } ${className}`}
    >
      {iniciales}
    </span>
  );
}
