import { Flag } from 'lucide-react';
import type { ColorFrescura } from '../lib/tipos';
import { COLOR_FRESCURA, TEXTO_FRESCURA } from './colores';
import { HojaInferior } from './HojaInferior';

const ORDEN: ColorFrescura[] = ['verde', 'amarillo', 'rojo'];

/** Leyenda del semáforo de frescura y de la bandera (requisito 4.6). */
export function HojaLeyenda({ onCerrar }: { onCerrar: () => void }) {
  return (
    <HojaInferior titulo="Qué significan los colores" onCerrar={onCerrar}>
      <ul className="mt-2">
        {ORDEN.map((color) => (
          <li key={color} className="flex items-center gap-3 py-2">
            <span
              aria-hidden="true"
              className="h-4 w-4 flex-none rounded-full"
              style={{ background: COLOR_FRESCURA[color] }}
            />
            {TEXTO_FRESCURA[color]}
          </li>
        ))}
        <li className="flex items-center gap-3 py-2">
          <Flag aria-hidden="true" className="h-[22px] w-[22px] flex-none text-ambar" />
          Revisar avance: dos registros seguidos bajo lo esperado para su edad (el nivel aparece en ámbar en la planilla)
        </li>
      </ul>
      <p className="mt-2 text-[14px] text-tinta-2">
        El punto de color junto a la fecha solo indica hace cuánto no se registra algo. No mide cómo le va al niño o
        niña.
      </p>
    </HojaInferior>
  );
}
