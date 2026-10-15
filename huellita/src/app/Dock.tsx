import { Camera, Mic, Pencil } from 'lucide-react';
import type { Formato } from '../lib/tipos';
import { useCaptura } from './captura';

const DEGRADADO = 'linear-gradient(to top, #F3F6FB 70%, rgba(243, 246, 251, 0))';
const BORDE_SUAVE = 'linear-gradient(to top, #F3F6FB, rgba(243, 246, 251, 0))';

/**
 * Dock de captura, siempre al alcance del pulgar sobre la barra inferior:
 * Foto y Texto a los lados y Audio al centro, destacado.
 */
export function Dock({ nombreNino }: { nombreNino?: string }) {
  const abrir = useCaptura();
  return (
    <div
      role="group"
      aria-label={nombreNino ? `Registrar para ${nombreNino}` : 'Registrar'}
      // En la ficha el dock lleva rótulo, así que el fondo va parejo para que
      // el texto se lea sobre el contenido.
      style={{ background: nombreNino ? '#F3F6FB' : DEGRADADO }}
      className="fixed bottom-[72px] left-1/2 z-10 w-full max-w-tia -translate-x-1/2 px-6 pb-[14px] pt-3"
    >
      {nombreNino ? (
        <>
          <span
            aria-hidden="true"
            style={{ background: BORDE_SUAVE }}
            className="pointer-events-none absolute -top-4 left-0 right-0 h-4"
          />
          <p className="mb-1 text-center text-[13px] font-bold text-tinta-2">
            Registrar para {nombreNino}
          </p>
        </>
      ) : null}
      <div className="flex items-center justify-center gap-7">
        <BotonCaptura formato="foto" etiqueta="Foto" onAbrir={abrir} />
        <BotonCaptura formato="audio" etiqueta="Audio" onAbrir={abrir} principal />
        <BotonCaptura formato="texto" etiqueta="Texto" onAbrir={abrir} />
      </div>
    </div>
  );
}

function BotonCaptura({
  formato,
  etiqueta,
  principal = false,
  onAbrir,
}: {
  formato: Formato;
  etiqueta: string;
  principal?: boolean;
  onAbrir: (formato: Formato) => void;
}) {
  const Icono = formato === 'foto' ? Camera : formato === 'audio' ? Mic : Pencil;
  return (
    <button
      type="button"
      onClick={() => onAbrir(formato)}
      className="flex min-h-tactil flex-col items-center gap-1 text-[13px] font-bold text-tinta-2"
    >
      <span
        className={
          principal
            ? 'grid h-[76px] w-[76px] place-items-center rounded-full bg-integra text-white shadow-[0_0_0_6px_#E7EEFA]'
            : 'grid h-[54px] w-[54px] place-items-center rounded-full border-[1.5px] border-linea bg-papel text-tinta'
        }
      >
        <Icono aria-hidden="true" className={principal ? 'h-[30px] w-[30px]' : 'h-[22px] w-[22px]'} />
      </span>
      {etiqueta}
    </button>
  );
}
