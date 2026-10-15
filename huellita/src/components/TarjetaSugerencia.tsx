import { Camera, Check, Mic, Pencil, PencilLine, X } from 'lucide-react';
import type { ReactNode } from 'react';
import type { NotaConError, NotaPendiente } from '../app/hooks';
import { nombreNivel, nombreNucleo } from '../lib/rubrica';
import type { Certeza, Formato } from '../lib/tipos';
import { textoCerteza } from '../lib/vistas';
import { Boton } from './Boton';
import { NumeroNivel } from './ChipNivel';

const COLORES_POSTIT = ['#FFE873', '#FFB8D2', '#D6F27C'];
const ROTACIONES = [-1.2, 0.9, -0.5, 1.1];

const CLASE_CERTEZA: Record<Certeza, string> = {
  alta: 'bg-[#E3F4EA] text-[#1D6B3E]',
  media: 'bg-[#FFF3CF] text-[#7A5600]',
  baja: 'bg-[#ECEFF5] text-[#56618A]',
};

function IconoFormato({ formato }: { formato: Formato }) {
  const Icono = formato === 'foto' ? Camera : formato === 'audio' ? Mic : Pencil;
  return <Icono aria-hidden="true" className="h-4 w-4 flex-none" />;
}

/** Post-it con la nota original de la tía, tal como la escribió. */
function PostIt({
  indice,
  origen,
  formato,
  cita,
}: {
  indice: number;
  origen: string;
  formato: Formato;
  cita: string;
}) {
  return (
    <div
      className="postit px-[18px] pb-[18px] pt-[22px]"
      style={{
        background: COLORES_POSTIT[indice % COLORES_POSTIT.length],
        transform: `rotate(${ROTACIONES[indice % ROTACIONES.length]}deg)`,
      }}
    >
      {/* 0,82 de opacidad: con 0,7 el origen no llega a AA sobre el post-it rosa. */}
      <p className="mb-[6px] flex items-center gap-[6px] text-[13px] text-[rgba(30,42,85,0.82)]">
        <IconoFormato formato={formato} />
        {origen}
      </p>
      <q className="block font-mano text-[20px] leading-[1.35]">{cita}</q>
    </div>
  );
}

function Lectura({ children }: { children: ReactNode }) {
  return (
    <div className="relative -mt-[6px] mx-[10px] flex flex-col gap-[10px] rounded-b-tarjeta border border-linea bg-papel p-[14px]">
      {children}
    </div>
  );
}

/**
 * Una sugerencia: la nota original arriba y lo que Huellita leyó pegado debajo,
 * con los 3 botones de la tía (Guardar, Cambiar y descartar).
 */
export function TarjetaSugerencia({
  nota,
  indice,
  saliendo = false,
  onGuardar,
  onCambiar,
  onDescartar,
}: {
  nota: NotaPendiente;
  indice: number;
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

  return (
    <article className={`mb-[26px] ${saliendo ? 'saliendo' : ''}`}>
      <PostIt indice={indice} origen={nota.origen} formato={formato} cita={s.cita} />
      <Lectura>
        {esNota ? (
          <>
            <span className="text-[12px] font-bold uppercase tracking-[0.06em] text-tinta-2">
              Nota de la sala
            </span>
            <p className="border-l-[3px] border-linea pl-[10px] text-[15px] text-tinta-2">
              No es una evaluación de un niño o niña. Se guarda en el diario de la sala.
            </p>
            <div className="grid grid-cols-[1fr_44px] gap-2">
              <Boton variante="pri" compacto className="min-w-0 overflow-hidden" onClick={onGuardar}>
                Guardar en la sala
              </Boton>
              <BotonDescartar onClick={onDescartar} />
            </div>
          </>
        ) : (
          <>
            <div className="flex items-center justify-between gap-2">
              <span className="inline-flex items-center gap-2 font-bold">
                <span
                  aria-hidden="true"
                  className="grid h-[30px] w-[30px] flex-none place-items-center rounded-full bg-integra-claro font-display text-[13px] text-integra-oscuro"
                >
                  {nota.inicialesNino ?? '?'}
                </span>
                {nombre}
                {nota.nombreNino && s.nombreDetectado && s.nombreDetectado !== nota.nombreNino ? (
                  <span className="text-[14px] font-normal text-tinta-2">
                    (decía “{s.nombreDetectado}”)
                  </span>
                ) : null}
              </span>
              <span
                className={`flex-none rounded-full px-[10px] py-[3px] text-[13px] font-bold ${
                  CLASE_CERTEZA[s.certeza]
                }`}
              >
                {textoCerteza(s.certeza)}
              </span>
            </div>

            {s.nivel && s.nucleo ? (
              <div className="flex items-center gap-[10px]">
                <NumeroNivel nivel={s.nivel} />
                <div>
                  <strong>{nombreNivel(s.nivel)}</strong>
                  <br />
                  <span className="text-[14px] text-tinta-2">{nombreNucleo(s.nucleo)}</span>
                </div>
              </div>
            ) : null}

            {s.conducta ? (
              <p className="border-l-[3px] border-linea pl-[10px] text-[15px] text-tinta-2">
                {s.conducta}
              </p>
            ) : null}

            <div className="grid grid-cols-[1.2fr_1fr_44px] gap-2">
              <Boton variante="ok" compacto className="min-w-0 overflow-hidden" onClick={onGuardar}>
                <Check aria-hidden="true" className="hidden h-[18px] w-[18px] min-[380px]:block" />
                Guardar
              </Boton>
              <Boton variante="sec" compacto className="min-w-0 overflow-hidden" onClick={onCambiar}>
                <PencilLine
                  aria-hidden="true"
                  className="hidden h-[18px] w-[18px] min-[380px]:block"
                />
                Cambiar
              </Boton>
              <BotonDescartar onClick={onDescartar} />
            </div>
          </>
        )}
      </Lectura>
    </article>
  );
}

/** Evidencia que Huellita no pudo leer: escribirla o descartarla. */
export function TarjetaError({
  nota,
  indice,
  onEscribir,
  onDescartar,
}: {
  nota: NotaConError;
  indice: number;
  onEscribir: () => void;
  onDescartar: () => void;
}) {
  return (
    <article className="mb-[26px]">
      <PostIt
        indice={indice}
        origen={nota.origen}
        formato={nota.evidencia.formato}
        cita="No pudimos leer esta nota."
      />
      <Lectura>
        <p className="text-[15px] text-tinta-2">
          Puedes escribirla con tus palabras y Huellita la ordena igual.
        </p>
        <div className="grid grid-cols-[1fr_44px] gap-2">
          <Boton variante="pri" compacto className="min-w-0 overflow-hidden" onClick={onEscribir}>
            Escribirla
          </Boton>
          <BotonDescartar onClick={onDescartar} />
        </div>
      </Lectura>
    </article>
  );
}

function BotonDescartar({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Descartar"
      className="grid min-h-tactil place-items-center rounded-[12px] border-[1.5px] border-linea bg-papel"
    >
      <X aria-hidden="true" className="h-[22px] w-[22px]" />
    </button>
  );
}
