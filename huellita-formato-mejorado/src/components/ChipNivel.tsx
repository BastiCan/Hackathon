import type { Nivel, NucleoId } from '../lib/tipos';
import { ambitoDe, CLASE_ETIQUETA } from './ambitos';

/**
 * Número de nivel en un cuadrado pequeño. Con núcleo, toma el color suave de su
 * ámbito; sin núcleo (nivel general), va en azul Integra. Si el núcleo está en
 * "revisar avance", va en ámbar.
 */
export function NumeroNivel({
  nivel,
  nucleo,
  revisar = false,
  tamano = 24,
}: {
  nivel: Nivel;
  nucleo?: NucleoId;
  revisar?: boolean;
  tamano?: number;
}) {
  const clase = revisar
    ? 'bg-[#FFE7B8] text-[#7A4A00] ring-1 ring-ambar'
    : nucleo
      ? CLASE_ETIQUETA[ambitoDe(nucleo)]
      : 'bg-integra text-white';
  return (
    <span
      aria-hidden="true"
      className={`tabular inline-grid flex-none place-items-center rounded-[4px] font-bold ${clase}`}
      style={{ width: tamano, height: tamano, fontSize: Math.round(tamano * 0.55) }}
    >
      {nivel}
    </span>
  );
}

/** Nivel general del niño/a como texto corto ("Nivel 4"), o "Sin nivel". */
export function ChipNivel({ nivel }: { nivel: Nivel | null }) {
  if (nivel === null) {
    return <span className="text-[12px] text-tinta-3">Sin nivel</span>;
  }
  return (
    <span className="inline-flex items-center gap-1 text-[12px] text-tinta-2">
      <NumeroNivel nivel={nivel} tamano={18} />
    </span>
  );
}
