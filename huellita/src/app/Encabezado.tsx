import { ChevronDown } from 'lucide-react';
import { useState } from 'react';
import { HojaMenu } from '../components/HojaMenu';
import type { Sala, Usuaria } from '../lib/tipos';

/**
 * Encabezado institucional, como en los sistemas del Estado: franja azul con el
 * sello de Gobierno de Chile e Integra, la usuaria a la derecha (abre su menú) y
 * una franja con los 4 colores del logo de Integra.
 *
 * El sello se dibuja con texto y una bandera simple; en producción se reemplaza
 * por los logos oficiales del Kit Digital (kitdigital.gob.cl) y de Integra.
 */
export function Encabezado({
  usuaria,
  salas,
  salaActual,
}: {
  usuaria?: Usuaria;
  salas?: Sala[];
  salaActual?: Sala;
}) {
  const [menu, setMenu] = useState(false);
  const cargo = usuaria?.rol === 'directora' ? 'Directora' : 'Educadora de párvulos';

  return (
    <header>
      <div className="flex min-h-[44px] items-center justify-between bg-integra px-4 py-[6px] text-white">
        <SelloInstitucional />
        {usuaria ? (
          <button
            type="button"
            onClick={() => setMenu(true)}
            aria-label={`Menú de ${usuaria.nombre}`}
            className="flex min-h-tactil items-center gap-1 text-right text-[12px] leading-[1.2]"
          >
            <span>
              <span className="block font-medium">{usuaria.nombre}</span>
              <span className="block opacity-80">{cargo}</span>
            </span>
            <ChevronDown aria-hidden="true" className="h-4 w-4 flex-none" />
          </button>
        ) : null}
      </div>
      <FranjaLogo />
      {menu && usuaria && salas && salaActual ? (
        <HojaMenu
          usuaria={usuaria}
          salas={salas}
          salaActual={salaActual}
          onCerrar={() => setMenu(false)}
        />
      ) : null}
    </header>
  );
}

export function SelloInstitucional() {
  return (
    <div className="flex items-center gap-2 text-[10px] leading-[1.1]">
      <span
        aria-hidden="true"
        className="flex h-[20px] w-[14px] flex-col overflow-hidden border border-white/60"
      >
        <i className="flex-1 bg-[#0F69C4]" />
        <i className="flex-1 bg-white" />
        <i className="flex-1 bg-[#E22C2C]" />
      </span>
      <span>
        Gobierno
        <br />
        de Chile
      </span>
      <span aria-hidden="true" className="mx-1 h-[22px] w-px bg-white/40" />
      <span className="text-[13px] font-bold tracking-[0.08em]">INTEGRA</span>
    </div>
  );
}

/** Franja con los 4 colores del logo de Integra. */
export function FranjaLogo() {
  return (
    <div aria-hidden="true" className="flex h-[4px]">
      <i className="flex-1 bg-logo-rojo" />
      <i className="flex-1 bg-logo-amarillo" />
      <i className="flex-1 bg-logo-azul" />
      <i className="flex-1 bg-logo-verde" />
    </div>
  );
}
