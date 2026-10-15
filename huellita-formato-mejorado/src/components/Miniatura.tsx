import { Mic, Pencil } from 'lucide-react';
import { urlFoto } from '../lib/fotos';
import type { Formato, NucleoId } from '../lib/tipos';
import { nombreNucleo } from '../lib/rubrica';
import { ambitoDe, CLASE_ETIQUETA } from './ambitos';

/**
 * Miniatura de una evidencia: la foto real del post-it, derecha y sin adornos.
 * Las notas escritas o dictadas no inventan una imagen: muestran su tipo.
 */
export function Miniatura({
  formato,
  foto,
  tamano = 60,
  className = '',
}: {
  formato: Formato;
  foto?: string;
  tamano?: number;
  className?: string;
}) {
  const url = urlFoto(foto);
  if (url) {
    return (
      <img
        src={url}
        alt="Foto de la nota"
        width={tamano}
        height={tamano}
        className={`flex-none rounded-[4px] border border-linea object-cover ${className}`}
        style={{ width: tamano, height: tamano }}
      />
    );
  }
  const Icono = formato === 'audio' ? Mic : Pencil;
  return (
    <span
      aria-hidden="true"
      className={`grid flex-none place-items-center rounded-[4px] border border-linea bg-fondo text-tinta-2 ${className}`}
      style={{ width: tamano, height: tamano }}
    >
      <span className="flex flex-col items-center gap-[2px] text-[11px]">
        <Icono className="h-[18px] w-[18px]" />
        {formato === 'audio' ? 'Audio' : 'Nota'}
      </span>
    </span>
  );
}

/** Etiqueta del núcleo con el color suave de su ámbito. */
export function EtiquetaNucleo({ nucleo, corta = false }: { nucleo: NucleoId; corta?: boolean }) {
  return (
    <span
      className={`inline-block rounded-[3px] px-[6px] py-[1px] text-[12px] font-medium ${
        CLASE_ETIQUETA[ambitoDe(nucleo)]
      }`}
    >
      {corta ? nucleo : nombreNucleo(nucleo)}
    </span>
  );
}
