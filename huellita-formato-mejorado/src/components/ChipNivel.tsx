import { ambitoDe, CLASE_ETIQUETA, COLOR_AMBITO } from './ambitos';
import { PALETA } from './colores';
import type { Nivel, NucleoId } from '../lib/tipos';

/**
 * Número de nivel en un chip pequeño de esquinas amables (10 px), con una
 * manchita del color de su ámbito asomando en la esquina superior derecha, como
 * la gráfica institucional del manual. Con núcleo toma el color suave de su
 * ámbito; sin núcleo (nivel general), va en azul Integra. Si el núcleo está en
 * "revisar avance", va en naranjo.
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
    ? 'bg-naranjo-suave text-naranjo-texto ring-1 ring-naranjo'
    : nucleo
      ? CLASE_ETIQUETA[ambitoDe(nucleo)]
      : 'bg-integra text-white';
  const mancha = revisar
    ? PALETA.naranjo
    : nucleo
      ? COLOR_AMBITO[ambitoDe(nucleo)]
      : '#FFFFFF';
  return (
    <span
      aria-hidden="true"
      className={`tabular relative inline-grid flex-none place-items-center overflow-hidden rounded-chip font-bold ${clase}`}
      style={{ width: tamano, height: tamano, fontSize: Math.round(tamano * 0.58) }}
    >
      <i
        aria-hidden="true"
        className="pointer-events-none absolute rounded-full"
        style={{
          background: mancha,
          opacity: 0.5,
          width: Math.round(tamano * 0.42),
          height: Math.round(tamano * 0.42),
          top: -Math.round(tamano * 0.16),
          right: -Math.round(tamano * 0.16),
        }}
      />
      <span className="relative">{nivel}</span>
    </span>
  );
}

/** Nivel general del niño/a como texto corto ("Nivel 4"), o "Sin nivel". */
export function ChipNivel({ nivel }: { nivel: Nivel | null }) {
  if (nivel === null) {
    return <span className="text-[13px] text-tinta-3">Sin nivel</span>;
  }
  return (
    <span className="inline-flex items-center gap-1 text-[13px] text-tinta-2">
      <NumeroNivel nivel={nivel} tamano={18} />
    </span>
  );
}
