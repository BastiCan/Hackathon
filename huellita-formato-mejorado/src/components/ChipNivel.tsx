import { colorNivel, niveles } from '../lib/rubrica';
import type { Nivel } from '../lib/tipos';
import { colorTextoNivel } from './colores';

/**
 * Número de nivel en un chip de esquinas amables (10 px), pintado con el color
 * de su nivel: un color distinto para cada uno de los 9 niveles, el mismo en
 * toda la app. El número va siempre visible, así el nivel nunca depende solo
 * del color. Una manchita clara asoma en la esquina, como en la gráfica
 * institucional del manual.
 *
 * "Revisar avance" no cambia el color del nivel: suma un aro naranjo oscuro
 * alrededor del chip (y la bandera junto al nombre, en la planilla y la ficha).
 */
export function NumeroNivel({
  nivel,
  revisar = false,
  tamano = 24,
}: {
  nivel: Nivel;
  revisar?: boolean;
  tamano?: number;
}) {
  return (
    <span
      aria-hidden="true"
      data-nivel={nivel}
      className={`tabular relative inline-grid flex-none place-items-center overflow-hidden rounded-chip font-bold ${
        revisar ? 'ring-2 ring-naranjo-texto ring-offset-1' : 'ring-1 ring-inset ring-black/10'
      }`}
      style={{
        width: tamano,
        height: tamano,
        fontSize: Math.round(tamano * 0.58),
        background: colorNivel(nivel),
        color: colorTextoNivel(nivel),
      }}
    >
      <i
        aria-hidden="true"
        className="pointer-events-none absolute rounded-full bg-white"
        style={{
          opacity: 0.35,
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

/** Nivel general del niño/a en su color, o "Sin nivel". */
export function ChipNivel({ nivel }: { nivel: Nivel | null }) {
  if (nivel === null) {
    return <span className="text-[13px] text-tinta-3">Sin nivel</span>;
  }
  return (
    <span className="inline-flex items-center gap-1 text-[13px] text-tinta-2">
      <NumeroNivel nivel={nivel} tamano={18} />
      <span className="sr-only">Nivel {nivel}</span>
    </span>
  );
}

/** Los 9 niveles en fila, del 1 al 9, para las leyendas. */
export function FilaNiveles({ tamano = 18 }: { tamano?: number }) {
  return (
    <span aria-hidden="true" className="inline-flex flex-wrap items-center gap-[3px]">
      {niveles().map((n) => (
        <NumeroNivel key={n.nivel} nivel={n.nivel} tamano={tamano} />
      ))}
    </span>
  );
}
