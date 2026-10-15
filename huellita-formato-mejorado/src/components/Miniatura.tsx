import { Mic, Pencil } from 'lucide-react';
import { urlFoto } from '../lib/fotos';
import type { Formato, NucleoId } from '../lib/tipos';
import { nombreNucleo } from '../lib/rubrica';
import { abreviatura, ambitoDe, CLASE_ETIQUETA } from './ambitos';
import { PALETA } from './colores';
import { Mancha } from './Mancha';

/**
 * Miniatura de una evidencia: la foto real del post-it, derecha y sin adornos.
 * Las notas escritas o dictadas no inventan una imagen: muestran su tipo.
 * Con `conMancha`, asoma una manchita rosada por detrás (el acento cálido del
 * manual para las notas), puro adorno.
 */
export function Miniatura({
  formato,
  foto,
  tamano = 60,
  className = '',
  conMancha = false,
}: {
  formato: Formato;
  foto?: string;
  tamano?: number;
  className?: string;
  conMancha?: boolean;
}) {
  const url = urlFoto(foto);
  const contenido = url ? (
    <img
      src={url}
      alt="Foto de la nota"
      width={tamano}
      height={tamano}
      className={`relative flex-none rounded-chip border border-linea object-cover ${className}`}
      style={{ width: tamano, height: tamano }}
    />
  ) : (
    <span
      aria-hidden="true"
      className={`relative grid flex-none place-items-center rounded-chip border border-linea bg-fondo text-tinta-2 ${className}`}
      style={{ width: tamano, height: tamano }}
    >
      <span className="flex flex-col items-center gap-[2px] text-[12px]">
        <Icono formato={formato} />
        {formato === 'audio' ? 'Audio' : 'Nota'}
      </span>
    </span>
  );

  if (!conMancha) return contenido;
  return (
    <span className="relative flex flex-none" style={{ width: tamano, height: tamano }}>
      <Mancha
        color={PALETA.rosado}
        forma="a"
        opacidad={0.45}
        className="-bottom-[5px] -left-[5px] h-6 w-6"
      />
      {contenido}
    </span>
  );
}

function Icono({ formato }: { formato: Formato }) {
  const Componente = formato === 'audio' ? Mic : Pencil;
  return <Componente className="h-[18px] w-[18px]" />;
}

/** Etiqueta del núcleo con el color suave de su ámbito. */
export function EtiquetaNucleo({ nucleo, corta = false }: { nucleo: NucleoId; corta?: boolean }) {
  return (
    <span
      className={`inline-block rounded-chip px-[7px] py-[1px] text-[13px] font-bold ${
        CLASE_ETIQUETA[ambitoDe(nucleo)]
      }`}
    >
      {corta ? abreviatura(nucleo) : nombreNucleo(nucleo)}
    </span>
  );
}
