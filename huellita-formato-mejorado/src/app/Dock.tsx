import { Camera, Mic, Pencil } from 'lucide-react';
import type { Formato } from '../lib/tipos';
import { useCaptura } from './captura';

/**
 * Barra de captura, siempre al alcance del pulgar sobre la navegación: Foto,
 * Grabar (al centro, en rojo como una grabadora) y Escribir.
 */
export function Dock({ nombreNino }: { nombreNino?: string }) {
  const abrir = useCaptura();
  return (
    <div
      role="group"
      aria-label={nombreNino ? `Registrar para ${nombreNino}` : 'Registrar'}
      className="fixed bottom-[64px] left-1/2 z-10 w-full max-w-tia -translate-x-1/2 border-t border-linea bg-papel"
    >
      {nombreNino ? (
        <p className="rotulo px-4 pt-[6px] text-center">Registrar para {nombreNino}</p>
      ) : null}
      <div className="grid grid-cols-[1fr_1.3fr_1fr] gap-2 px-3 py-2">
        <BotonCaptura formato="foto" etiqueta="Foto" onAbrir={abrir} />
        <BotonCaptura formato="audio" etiqueta="Grabar" onAbrir={abrir} principal />
        <BotonCaptura formato="texto" etiqueta="Escribir" onAbrir={abrir} />
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
      className={`flex min-h-[48px] items-center justify-center gap-2 rounded-tarjeta text-[15px] font-medium ${
        principal
          ? 'bg-grabar text-white'
          : 'border border-[#C9D2DE] bg-papel text-integra'
      }`}
    >
      <Icono aria-hidden="true" className="h-[20px] w-[20px]" />
      {etiqueta}
    </button>
  );
}
