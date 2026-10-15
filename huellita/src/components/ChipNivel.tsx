import { colorNivel } from '../lib/rubrica';
import type { Nivel } from '../lib/tipos';
import { colorChipNivel, colorTextoNivel } from './colores';

/**
 * Etiqueta "N4" con el color del nivel. Va en pastel del mismo color con el
 * número en tinta: el relleno fuerte del prototipo con texto blanco de 12 px no
 * alcanza el contraste AA en los niveles claros (tarea 10).
 */
export function ChipNivel({ nivel }: { nivel: Nivel | null }) {
  if (nivel === null) {
    return (
      <span className="rounded-full bg-cuadricula px-2 py-[2px] text-[12px] font-bold text-tinta-2">
        Sin nivel
      </span>
    );
  }
  const { fondo, borde } = colorChipNivel(nivel);
  return (
    <span
      className="rounded-full border px-2 py-[2px] text-[12px] font-bold tracking-[0.02em] text-tinta"
      style={{ background: fondo, borderColor: borde }}
    >
      N{nivel}
    </span>
  );
}

/** Número de nivel en cuadrado de color (tarjeta de lectura y hojas). */
export function NumeroNivel({ nivel, tamano = 38 }: { nivel: Nivel; tamano?: number }) {
  return (
    <span
      aria-hidden="true"
      className="grid flex-none place-items-center rounded-[10px] font-display text-[20px] font-extrabold"
      style={{
        background: colorNivel(nivel),
        color: colorTextoNivel(nivel),
        width: tamano,
        height: tamano,
      }}
    >
      {nivel}
    </span>
  );
}
