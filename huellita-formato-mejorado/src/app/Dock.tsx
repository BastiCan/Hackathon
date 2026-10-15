import { Camera, FileAudio, Mic, Pencil, type LucideIcon } from 'lucide-react';
import { useCaptura, type AccionCaptura } from './captura';

/** Nombre del grupo de captura, el mismo en el celular y en el computador. */
export function etiquetaRegistrar(nombreNino?: string): string {
  return nombreNino ? `Registrar para ${nombreNino}` : 'Registrar';
}

interface OpcionCaptura {
  accion: AccionCaptura;
  etiqueta: string;
  /** Una línea de ayuda, solo en los botones grandes de Inicio. */
  ayuda: string;
  icono: LucideIcon;
  /** Grabar va destacado en rojo, como una grabadora. */
  principal?: boolean;
}

/** Las 4 formas de registrar, en el mismo orden en toda la app. */
export const OPCIONES_CAPTURA: OpcionCaptura[] = [
  { accion: 'foto', etiqueta: 'Subir foto', ayuda: 'De la cámara o la galería', icono: Camera },
  { accion: 'grabar', etiqueta: 'Grabar audio', ayuda: 'Hasta 60 segundos', icono: Mic, principal: true },
  { accion: 'escribir', etiqueta: 'Escribir', ayuda: 'Una nota corta', icono: Pencil },
  { accion: 'subir-audio', etiqueta: 'Subir audio', ayuda: 'Una nota de voz ya grabada', icono: FileAudio },
];

/**
 * Cómo se disponen los botones:
 * - `fila`: los 4 en fila, ícono sobre el texto (dock del celular, en la ficha);
 * - `columna`: uno bajo otro (bloque "Registrar" de la barra lateral);
 * - `grande`: tarjetas de 2 × 2 con una línea de ayuda (pantalla de Inicio).
 */
export type DisposicionCaptura = 'fila' | 'columna' | 'grande';

const CONTENEDOR: Record<DisposicionCaptura, string> = {
  fila: 'grid grid-cols-4 gap-2',
  columna: 'grid gap-2',
  grande: 'grid grid-cols-2 gap-3 lg:grid-cols-4',
};

export function BotonesCaptura({ disposicion = 'fila' }: { disposicion?: DisposicionCaptura }) {
  const abrir = useCaptura();
  return (
    <div className={CONTENEDOR[disposicion]}>
      {OPCIONES_CAPTURA.map((opcion) => (
        <BotonCaptura
          key={opcion.accion}
          opcion={opcion}
          disposicion={disposicion}
          onAbrir={abrir}
        />
      ))}
    </div>
  );
}

/**
 * Barra de captura del celular, siempre al alcance del pulgar sobre la
 * navegación (en la ficha del niño/a). En el computador (`lg:`) se esconde: los
 * mismos botones aparecen arriba de la barra lateral.
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
  opcion,
  disposicion,
  onAbrir,
}: {
  opcion: OpcionCaptura;
  disposicion: DisposicionCaptura;
  onAbrir: (accion: AccionCaptura) => void;
}) {
  const { icono: Icono, principal } = opcion;
  const color = principal
    ? 'bg-grabar text-white shadow-tarjeta'
    : 'border border-linea bg-papel text-integra';

  if (disposicion === 'grande') {
    return (
      <button
        type="button"
        onClick={() => onAbrir(opcion.accion)}
        className={`flex min-h-[96px] flex-col items-start justify-between gap-2 rounded-tarjeta p-3 text-left shadow-tarjeta ${color}`}
      >
        <span
          className={`grid h-10 w-10 place-items-center rounded-full ${
            principal ? 'bg-white/20' : 'bg-integra-claro'
          }`}
        >
          <Icono aria-hidden="true" className="h-[22px] w-[22px]" />
        </span>
        <span>
          <span className="block text-[17px] font-bold leading-tight">{opcion.etiqueta}</span>
          <span className={`block text-[13px] ${principal ? 'text-white' : 'text-tinta-2'}`}>
            {opcion.ayuda}
          </span>
        </span>
      </button>
    );
  }

  if (disposicion === 'columna') {
    return (
      <button
        type="button"
        onClick={() => onAbrir(opcion.accion)}
        className={`flex min-h-[48px] items-center justify-center gap-2 rounded-boton px-3 text-[16px] font-bold ${color}`}
      >
        <Icono aria-hidden="true" className="h-[20px] w-[20px]" />
        {opcion.etiqueta}
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={() => onAbrir(opcion.accion)}
      className={`flex min-h-[56px] flex-col items-center justify-center gap-[2px] rounded-boton px-1 text-center text-[13px] font-bold leading-tight ${color}`}
    >
      <Icono aria-hidden="true" className="h-[20px] w-[20px]" />
      {opcion.etiqueta}
    </button>
  );
}
