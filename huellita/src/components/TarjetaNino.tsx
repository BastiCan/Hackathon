import { Flag } from 'lucide-react';
import { etiquetaTarjeta, type TarjetaNinoVista } from '../lib/vistas';
import { Avatar } from './Avatar';
import { ChipNivel } from './ChipNivel';

/**
 * Tarjeta de la grilla: avatar con iniciales y aro de frescura, nombre de pila,
 * chip de nivel general y bandera ámbar si hay que revisar avance.
 */
export function TarjetaNino({
  tarjeta,
  onAbrir,
}: {
  tarjeta: TarjetaNinoVista;
  onAbrir: (id: string) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onAbrir(tarjeta.id)}
      aria-label={etiquetaTarjeta(tarjeta)}
      className="relative flex min-h-[124px] flex-col items-center gap-[6px] rounded-tarjeta border border-linea bg-papel px-[6px] pb-[10px] pt-3 active:scale-[0.98]"
    >
      {tarjeta.revisarAvance ? (
        <span className="absolute right-2 top-2 text-ambar">
          <Flag aria-hidden="true" className="h-[22px] w-[22px]" strokeWidth={2} />
        </span>
      ) : null}
      <Avatar iniciales={tarjeta.iniciales} frescura={tarjeta.frescura} />
      <span className="text-[15px] font-bold">{tarjeta.nombre}</span>
      <ChipNivel nivel={tarjeta.nivelGeneral} />
    </button>
  );
}
