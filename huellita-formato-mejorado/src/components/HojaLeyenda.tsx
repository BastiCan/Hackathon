import { Flag } from 'lucide-react';
import { niveles } from '../lib/rubrica';
import type { ColorFrescura } from '../lib/tipos';
import { NumeroNivel } from './ChipNivel';
import { COLOR_FRESCURA, TEXTO_FRESCURA } from './colores';
import { HojaInferior } from './HojaInferior';

const ORDEN: ColorFrescura[] = ['verde', 'amarillo', 'rojo'];

/**
 * Leyenda de la planilla (requisito 4.6): el color de cada nivel, el punto de
 * frescura y la bandera de "revisar avance".
 */
export function HojaLeyenda({ onCerrar }: { onCerrar: () => void }) {
  return (
    <HojaInferior titulo="Qué significan los colores" onCerrar={onCerrar}>
      <h3 className="rotulo mt-3">Nivel alcanzado en cada núcleo</h3>
      <ul className="mt-1">
        {niveles().map((n) => (
          <li key={n.nivel} className="flex items-center gap-3 py-[5px]">
            <NumeroNivel nivel={n.nivel} tamano={24} />
            <span className="text-[15px]">
              <span className="sr-only">Nivel {n.nivel}: </span>
              {n.nombre}
              <span className="text-tinta-2"> · {n.edadOrientativa}</span>
            </span>
          </li>
        ))}
      </ul>

      <h3 className="rotulo mt-4">Último registro</h3>
      <ul className="mt-1">
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
          <Flag aria-hidden="true" className="h-[22px] w-[22px] flex-none text-naranjo-texto" />
          Revisar avance: dos registros seguidos bajo lo esperado para su edad (el número de ese
          núcleo lleva un aro naranjo)
        </li>
      </ul>
      <p className="mt-2 text-[15px] text-tinta-2">
        El color del número muestra el nivel del último registro confirmado en ese núcleo. La edad de
        cada nivel es solo orientativa.
      </p>
      <p className="mt-2 text-[15px] text-tinta-2">
        El punto de color junto a la fecha solo indica hace cuánto no se registra algo. No mide cómo le va al niño o
        niña.
      </p>
    </HojaInferior>
  );
}
