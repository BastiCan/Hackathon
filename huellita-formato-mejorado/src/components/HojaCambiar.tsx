import { useState } from 'react';
import type { CambiosValidacion } from '../services/datos';
import { celda, codigosNucleos, nombreNucleo, niveles } from '../lib/rubrica';
import type { Nino, Nivel, NucleoId, Sugerencia } from '../lib/tipos';
import { Boton } from './Boton';
import { NumeroNivel } from './ChipNivel';
import { HojaInferior } from './HojaInferior';

/**
 * Hoja "Cambiar": la tía corrige niño/a, núcleo y nivel. Cada nivel muestra su
 * descriptor, que sale de la rúbrica (requisito 3.3).
 */
export function HojaCambiar({
  sugerencia,
  ninos,
  onGuardar,
  onCerrar,
}: {
  sugerencia: Sugerencia;
  ninos: Nino[];
  onGuardar: (cambios: CambiosValidacion) => void;
  onCerrar: () => void;
}) {
  const [ninoId, setNinoId] = useState<string>(sugerencia.ninoId ?? ninos[0]?.id ?? '');
  const [nucleo, setNucleo] = useState<NucleoId>(sugerencia.nucleo ?? codigosNucleos()[0]);
  const [nivel, setNivel] = useState<Nivel>(sugerencia.nivel ?? 1);

  return (
    <HojaInferior titulo="Corregir evaluación" onCerrar={onCerrar}>
      <label className="mt-[10px] block text-[15px] text-tinta-2">
        Niño o niña
        <select
          value={ninoId}
          onChange={(e) => setNinoId(e.target.value)}
          className="mt-1 min-h-tactil w-full rounded-campo border border-linea bg-papel px-[10px] py-2 text-base text-tinta"
        >
          {ninos.map((n) => (
            <option key={n.id} value={n.id}>
              {n.nombre} {n.apellidoInicial}
            </option>
          ))}
        </select>
      </label>

      <label className="mt-[10px] block text-[15px] text-tinta-2">
        Núcleo
        <select
          value={nucleo}
          onChange={(e) => setNucleo(e.target.value as NucleoId)}
          className="mt-1 min-h-tactil w-full rounded-campo border border-linea bg-papel px-[10px] py-2 text-base text-tinta"
        >
          {codigosNucleos().map((c) => (
            <option key={c} value={c}>
              {nombreNucleo(c)}
            </option>
          ))}
        </select>
      </label>

      <div role="radiogroup" aria-label="Nivel" className="my-[10px] flex flex-col gap-2">
        {niveles().map((info) => (
          <button
            key={info.nivel}
            type="button"
            role="radio"
            aria-checked={info.nivel === nivel}
            onClick={() => setNivel(info.nivel)}
            className={`flex min-h-tactil items-center gap-3 rounded-tarjeta border p-[10px] text-left ${
              info.nivel === nivel ? 'border-integra bg-integra-claro' : 'border-linea'
            }`}
          >
            <NumeroNivel nivel={info.nivel} nucleo={nucleo} tamano={26} />
            <span>
              <strong>{info.nombre}</strong>
              <small className="block text-[13px] text-tinta-2">
                {celda(nucleo, info.nivel).descriptor}
              </small>
            </span>
          </button>
        ))}
      </div>

      <Boton
        ancho
        variante="pri"
        disabled={!ninoId}
        onClick={() => onGuardar({ ninoId, nucleo, nivel })}
      >
        Guardar corrección
      </Boton>
    </HojaInferior>
  );
}
