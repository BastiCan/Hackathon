import { Camera, Mic, Pencil } from 'lucide-react';
import type { Formato } from '../lib/tipos';
import { useCaptura } from './captura';

/** Nombre del grupo de captura, el mismo en el celular y en el computador. */
export function etiquetaRegistrar(nombreNino?: string): string {
  return nombreNino ? `Registrar para ${nombreNino}` : 'Registrar';
}

/**
 * Los 3 botones de captura: Foto, Grabar (al centro, en rojo como una
 * grabadora) y Escribir. En el celular van en fila dentro del dock; en el
 * computador, en columna dentro del bloque "Registrar" de la barra lateral.
 */
export function BotonesCaptura({ columna = false }: { columna?: boolean }) {
  const abrir = useCaptura();
  return (
    <div className={columna ? 'grid gap-2' : 'grid grid-cols-[1fr_1.3fr_1fr] gap-2'}>
      <BotonCaptura formato="foto" etiqueta="Foto" onAbrir={abrir} />
      <BotonCaptura formato="audio" etiqueta="Grabar" onAbrir={abrir} principal />
      <BotonCaptura formato="texto" etiqueta="Escribir" onAbrir={abrir} />
    </div>
  );
}

/**
 * Barra de captura del celular, siempre al alcance del pulgar sobre la
 * navegación. En el computador (`lg:`) se esconde: los mismos botones aparecen
 * arriba de la barra lateral.
 */
export function Dock({ nombreNino }: { nombreNino?: string }) {
  return (
    <div
      role="group"
      aria-label={etiquetaRegistrar(nombreNino)}
      className="sobre-barra fixed left-1/2 z-10 w-full max-w-tia -translate-x-1/2 border-t border-linea bg-papel md:max-w-[640px] lg:hidden"
    >
      {nombreNino ? (
        <p className="rotulo px-4 pt-[6px] text-center">Registrar para {nombreNino}</p>
      ) : null}
      <div className="px-3 py-2">
        <BotonesCaptura />
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
      className={`flex min-h-[48px] items-center justify-center gap-2 rounded-boton text-[16px] font-bold ${
        principal
          ? 'bg-grabar text-white shadow-tarjeta'
          : 'border border-linea bg-papel text-integra'
      }`}
    >
      <Icono aria-hidden="true" className="h-[20px] w-[20px]" />
      {etiqueta}
    </button>
  );
}
