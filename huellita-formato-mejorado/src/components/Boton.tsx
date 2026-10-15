import type { ButtonHTMLAttributes, ReactNode } from 'react';

type Variante = 'pri' | 'sec' | 'ok';

const ESTILOS: Record<Variante, string> = {
  pri: 'bg-integra text-white',
  sec: 'bg-papel border border-integra text-integra',
  // Verde del logo de Integra, oscurecido para que el texto blanco cumpla AA.
  ok: 'bg-guardar text-white',
};

/** Botón de 44 px mínimo, en las 3 variantes del prototipo. */
export function Boton({
  variante = 'sec',
  ancho,
  compacto,
  children,
  className = '',
  ...resto
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variante?: Variante;
  ancho?: boolean;
  /** Menos relleno horizontal, para filas de 3 botones en 360 px. */
  compacto?: boolean;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      className={`inline-flex min-h-tactil items-center justify-center gap-[6px] rounded-tarjeta py-[10px] text-[15px] font-medium disabled:opacity-50 ${
        compacto ? 'px-2' : 'px-4'
      } ${ESTILOS[variante]} ${ancho ? 'w-full' : ''} ${className}`}
      {...resto}
    >
      {children}
    </button>
  );
}
