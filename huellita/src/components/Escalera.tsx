import { colorNivel } from '../lib/rubrica';
import type { Nivel } from '../lib/tipos';

const ESCALONES: Nivel[] = [1, 2, 3, 4, 5, 6, 7, 8];

/**
 * Escalera de 8 escalones, como la lámina de la rúbrica de Integra, pintada
 * hasta el nivel actual con su color. Decorativa: el nivel se dice en texto.
 */
export function Escalera({ nivel }: { nivel: Nivel | null }) {
  return (
    <span aria-hidden="true" className="col-start-2 row-span-2 flex h-[26px] items-end gap-[3px]">
      {ESCALONES.map((escalon) => (
        <i
          key={escalon}
          className="block w-[9px] rounded-[2px] bg-cuadricula"
          style={{
            height: 6 + escalon * 2.5,
            ...(nivel && escalon <= nivel ? { background: colorNivel(nivel) } : {}),
          }}
        />
      ))}
    </span>
  );
}
