import { Camera, Check, Mic, Pencil, PencilLine } from 'lucide-react';
import { useState, type ReactNode } from 'react';
import type { NotaConError, NotaPendiente } from '../app/hooks';
import { urlFoto } from '../lib/fotos';
import { nombreNivel } from '../lib/rubrica';
import type { Certeza, Evidencia, Formato } from '../lib/tipos';
import { textoCerteza } from '../lib/vistas';
import { Boton } from './Boton';
import { NumeroNivel } from './ChipNivel';
import { PALETA } from './colores';
import { HojaInferior } from './HojaInferior';
import { Mancha } from './Mancha';
import { EtiquetaNucleo } from './Miniatura';

const CLASE_CERTEZA: Record<Certeza, string> = {
  alta: 'text-guardar',
  media: 'text-naranjo-texto',
  baja: 'text-tinta-2',
};

const EXPLICACION_CERTEZA: Record<Certeza, string> = {
  alta: '',
  media: ': revisa el nivel',
  baja: ': revisa el nombre y el nivel',
};

function IconoFormato({ formato }: { formato: Formato }) {
  const Icono = formato === 'foto' ? Camera : formato === 'audio' ? Mic : Pencil;
  return <Icono aria-hidden="true" className="h-4 w-4 flex-none" />;
}

/** "EVI-00325" → "0325": número del registro, como en un libro de registro. */
function numeroRegistro(evidencia?: Evidencia): string | null {
  const m = evidencia ? /(\d+)$/.exec(evidencia.id) : null;
  return m ? m[1].slice(-4).padStart(4, '0') : null;
}

/**
 * Cabecera de un registro: número, tipo y origen, la foto real del post-it (si
 * la hay) y lo que Huellita leyó. La foto se puede ampliar.
 */
function Original({
  evidencia,
  formato,
  origen,
  leido,
}: {
  evidencia?: Evidencia;
  formato: Formato;
  origen: string;
  leido: string;
}) {
  const [ampliada, setAmpliada] = useState(false);
  const url = urlFoto(evidencia?.foto);
  const numero = numeroRegistro(evidencia);
  return (
    <div className="border-b border-linea bg-fondo px-3 pb-3 pt-[10px]">
      <p className="mb-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px] text-tinta-2">
        <IconoFormato formato={formato} />
        {numero ? <span className="font-bold uppercase">N.º {numero}</span> : null}
        <span>{origen}</span>
      </p>
      {url ? (
        <div className="relative mb-2">
          {/* La mancha rosada del manual, puro adorno, detrás de la foto. */}
          <Mancha
            color={PALETA.rosado}
            forma="b"
            opacidad={0.18}
            className="-left-4 -top-4 h-24 w-24"
          />
          <Mancha
            color={PALETA.rosado}
            forma="c"
            opacidad={0.14}
            className="-bottom-5 -right-3 h-20 w-20"
          />
          <button
            type="button"
            onClick={() => setAmpliada(true)}
            aria-label="Ver la foto en grande"
            className="relative block min-h-tactil w-full overflow-hidden rounded-chip border border-linea bg-papel"
          >
            <img
              src={url}
              alt="Foto del post-it"
              className="mx-auto block max-h-[220px] w-auto max-w-full lg:max-h-[300px]"
            />
          </button>
        </div>
      ) : null}
      <p className="rotulo mb-1">Huellita leyó</p>
      <p className="border-l-[3px] border-rosado pl-[10px] text-[16px] text-tinta">“{leido}”</p>
      {ampliada && url ? (
        <HojaInferior titulo="Foto del post-it" onCerrar={() => setAmpliada(false)}>
          <img src={url} alt="Foto del post-it en grande" className="mt-2 w-full rounded-chip" />
        </HojaInferior>
      ) : null}
    </div>
  );
}

function Fila({ etiqueta, children }: { etiqueta: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-[84px_1fr] items-start gap-2 py-[3px] text-[15px]">
      <dt className="text-tinta-2">{etiqueta}</dt>
      <dd>{children}</dd>
    </div>
  );
}

/**
 * Un registro por revisar: la nota original (con su foto) arriba y lo que
 * Huellita propone abajo, como una ficha. La tía confirma, corrige o descarta.
 */
export function TarjetaSugerencia({
  nota,
  saliendo = false,
  onGuardar,
  onCambiar,
  onDescartar,
}: {
  nota: NotaPendiente;
  indice?: number;
  /** Transición breve mientras la nota se guarda o se descarta. */
  saliendo?: boolean;
  onGuardar: () => void;
  onCambiar: () => void;
  onDescartar: () => void;
}) {
  const { sugerencia: s } = nota;
  const formato = nota.evidencia?.formato ?? 'texto';
  const esNota = s.tipo === 'nota_sala';
  const nombre = nota.nombreNino ?? s.nombreDetectado ?? 'Por confirmar';
  const leido = nota.evidencia?.textoExtraido ?? s.cita;

  return (
    <article
      className={`mb-4 overflow-hidden rounded-tarjeta border border-linea bg-papel shadow-tarjeta lg:mb-0 ${
        saliendo ? 'saliendo' : ''
      }`}
    >
      <Original evidencia={nota.evidencia} formato={formato} origen={nota.origen} leido={leido} />
      <div className="px-3 pb-3 pt-2">
        {esNota ? (
          <>
            <p className="rotulo mb-1">Nota de la sala</p>
            <p className="mb-3 text-[15px] text-tinta-2">
              No es una evaluación de un niño o niña. Se guarda en el diario de la sala.
            </p>
            <div className="grid grid-cols-[1fr_auto] gap-2">
              <Boton variante="pri" compacto onClick={onGuardar}>
                Guardar en la sala
              </Boton>
              <BotonDescartar onClick={onDescartar} />
            </div>
          </>
        ) : (
          <>
            <dl className="mb-3">
              <Fila etiqueta="Niño/a">
                <b>{nombre}</b>
                {nota.nombreNino && s.nombreDetectado && s.nombreDetectado !== nota.nombreNino ? (
                  <span className="text-tinta-2"> (escrito “{s.nombreDetectado}”)</span>
                ) : null}
              </Fila>
              {s.nucleo ? (
                <Fila etiqueta="Núcleo">
                  <EtiquetaNucleo nucleo={s.nucleo} />
                </Fila>
              ) : null}
              {s.nivel ? (
                <Fila etiqueta="Nivel">
                  <span className="inline-flex items-center gap-2">
                    <NumeroNivel nivel={s.nivel} nucleo={s.nucleo} tamano={22} />
                    {nombreNivel(s.nivel)}
                  </span>
                </Fila>
              ) : null}
              {s.conducta ? <Fila etiqueta="Conducta">{s.conducta}</Fila> : null}
              <Fila etiqueta="Confianza">
                <span className={`font-bold ${CLASE_CERTEZA[s.certeza]}`}>
                  {textoCerteza(s.certeza)}
                  <span className="font-normal text-tinta">{EXPLICACION_CERTEZA[s.certeza]}</span>
                </span>
              </Fila>
            </dl>

            <div className="grid grid-cols-3 gap-2">
              <Boton variante="ok" compacto className="min-w-0 overflow-hidden" onClick={onGuardar}>
                <Check aria-hidden="true" className="hidden h-[18px] w-[18px] min-[380px]:block" />
                Confirmar
              </Boton>
              <Boton variante="sec" compacto className="min-w-0 overflow-hidden" onClick={onCambiar}>
                <PencilLine
                  aria-hidden="true"
                  className="hidden h-[18px] w-[18px] min-[380px]:block"
                />
                Corregir
              </Boton>
              <BotonDescartar onClick={onDescartar} conTexto />
            </div>
          </>
        )}
      </div>
    </article>
  );
}

/** Evidencia que Huellita no pudo leer: escribirla o descartarla. */
export function TarjetaError({
  nota,
  onEscribir,
  onDescartar,
}: {
  nota: NotaConError;
  indice?: number;
  onEscribir: () => void;
  onDescartar: () => void;
}) {
  return (
    <article className="mb-4 overflow-hidden rounded-tarjeta border border-linea bg-papel shadow-tarjeta lg:mb-0">
      <Original
        evidencia={nota.evidencia}
        formato={nota.evidencia.formato}
        origen={nota.origen}
        leido="No pudimos leer esta nota."
      />
      <div className="px-3 pb-3 pt-2">
        <p className="mb-3 text-[15px] text-tinta-2">
          Puedes escribirla con tus palabras y Huellita la ordena igual.
        </p>
        <div className="grid grid-cols-[1fr_auto] gap-2">
          <Boton variante="pri" compacto onClick={onEscribir}>
            Escribirla
          </Boton>
          <BotonDescartar onClick={onDescartar} />
        </div>
      </div>
    </article>
  );
}

function BotonDescartar({ onClick }: { onClick: () => void; conTexto?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Descartar"
      className="grid min-h-tactil place-items-center rounded-boton border border-linea bg-papel px-3 text-[15px] font-bold text-tinta-2"
    >
      Descartar
    </button>
  );
}
