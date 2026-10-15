import { ChevronDown } from 'lucide-react';
import { useState } from 'react';
import logoOficial from '../assets/marca/logo-mineduc-integra.png';
import { HojaMenu } from '../components/HojaMenu';
import type { Sala, Usuaria } from '../lib/tipos';

/**
 * Texto alternativo del logo oficial. Es la única imagen de la app que no es la
 * foto de una nota: las pruebas de privacidad la excluyen por este `alt`.
 */
export const ALT_LOGO = 'Ministerio de Educación, Gobierno de Chile · Integra';

/**
 * Encabezado institucional, como en los sistemas del Estado: barra blanca con
 * el logo oficial (Ministerio de Educación · Gobierno de Chile e Integra), la
 * usuaria a la derecha (abre su menú) y la franja con los 4 colores del logo.
 *
 * El logo va sobre blanco porque el archivo tiene fondo blanco; nunca sobre el
 * azul de Integra.
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
      {/* La barra blanca llega al borde de la ventana; su contenido se centra
          hasta 1280 px, como en los sistemas del Estado. */}
      <div className="border-b border-linea bg-papel">
        <div className="mx-auto flex min-h-[56px] w-full items-center justify-between gap-3 px-4 py-2 lg:max-w-[1280px] lg:px-7">
          <LogoOficial />
          {usuaria ? (
            <button
              type="button"
              onClick={() => setMenu(true)}
              aria-label={`Menú de ${usuaria.nombre}`}
              className="flex min-h-tactil min-w-0 items-center gap-1 text-right text-[13px] leading-[1.2] text-tinta"
            >
              <span className="min-w-0">
                <span className="block truncate font-bold">{usuaria.nombre}</span>
                <span className="block truncate text-tinta-2 max-[359px]:hidden">{cargo}</span>
              </span>
              <ChevronDown aria-hidden="true" className="h-4 w-4 flex-none text-tinta-2" />
            </button>
          ) : null}
        </div>
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

/**
 * Logo oficial Mineduc + Integra. Alto fijo y ancho automático para que nunca
 * se deforme; `object-contain` evita que se recorte si el espacio se achica.
 */
export function LogoOficial({ className = 'h-9 sm:h-11' }: { className?: string }) {
  return (
    <img
      src={logoOficial}
      alt={ALT_LOGO}
      className={`w-auto flex-none object-contain object-left ${className}`}
    />
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
