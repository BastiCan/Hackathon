import { Mic } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { AUDIO_MAX_POR_DEFECTO, MAX_BYTES_AUDIO } from '../app/config';
import { Boton } from './Boton';
import { HojaInferior } from './HojaInferior';

/** 48 kbps: 5 minutos de voz caben en unos 1,8 MB, bajo el tope del transcriptor. */
const BITS_POR_SEGUNDO = 48_000;
/** MediaRecorder entrega un trozo por segundo, así lo grabado no depende de un solo evento. */
const TROZO_MS = 1000;

/** Segundos como reloj: 75 → "1:15". */
export function formatoReloj(segundos: number): string {
  const s = Math.max(0, Math.floor(segundos));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

/** 300 → "Máximo 5 minutos"; 270 → "Máximo 4 minutos y 30 segundos". */
export function textoMaximo(segundos: number): string {
  const minutos = Math.floor(segundos / 60);
  const resto = segundos % 60;
  const partes: string[] = [];
  if (minutos > 0) partes.push(`${minutos} ${minutos === 1 ? 'minuto' : 'minutos'}`);
  if (resto > 0) partes.push(`${resto} segundos`);
  return `Máximo ${partes.join(' y ')}`;
}

/** Grabadora a 48 kbps; si el navegador no acepta la opción, con la calidad que traiga. */
function crearGrabadora(flujo: MediaStream): MediaRecorder {
  try {
    return new MediaRecorder(flujo, { audioBitsPerSecond: BITS_POR_SEGUNDO });
  } catch {
    return new MediaRecorder(flujo);
  }
}

/**
 * Foto: abre la cámara trasera (o el selector en escritorio), muestra la vista
 * previa y envía. El archivo nunca sale del dispositivo (privacidad.md 3).
 */
export function HojaFoto({
  onEnviar,
  onCerrar,
}: {
  onEnviar: (archivo: Blob) => void;
  onCerrar: () => void;
}) {
  const [vista, setVista] = useState<string | null>(null);
  const archivo = useRef<Blob | null>(null);
  const entrada = useRef<HTMLInputElement>(null);
  const yaAbierta = useRef(false);

  // Se intenta abrir la cámara al tiro; si el navegador lo bloquea, queda el
  // botón visible.
  useEffect(() => {
    if (yaAbierta.current) return;
    yaAbierta.current = true;
    entrada.current?.click();
  }, []);

  useEffect(() => () => {
    if (vista) URL.revokeObjectURL(vista);
  }, [vista]);

  return (
    <HojaInferior titulo="Foto de tu nota" onCerrar={onCerrar}>
      <p className="mb-[14px] mt-1 text-[15px] text-tinta-2">
        Encuadra el post-it o la hoja completa.
      </p>
      <input
        ref={entrada}
        type="file"
        accept="image/*"
        capture="environment"
        className="sr-only"
        aria-label="Tomar la foto de la nota"
        onChange={(e) => {
          const elegido = e.target.files?.[0];
          if (!elegido) return;
          archivo.current = elegido;
          setVista((anterior) => {
            if (anterior) URL.revokeObjectURL(anterior);
            return URL.createObjectURL(elegido);
          });
        }}
      />
      {vista ? (
        <img
          src={vista}
          alt="Vista previa de la nota fotografiada"
          className="mb-[14px] max-h-[46vh] w-full rounded-tarjeta border border-linea object-contain"
        />
      ) : (
        <div className="mb-[14px] grid aspect-[4/3] place-items-center rounded-tarjeta border border-dashed border-linea bg-fondo px-6 text-center text-[15px] text-tinta-2">
          Saca una foto del post-it o de la nota. La foto queda guardada en el registro.
        </div>
      )}
      <Boton
        ancho
        variante={vista ? 'pri' : 'sec'}
        onClick={() => {
          if (!vista) {
            entrada.current?.click();
            return;
          }
          if (archivo.current) onEnviar(archivo.current);
        }}
      >
        {vista ? 'Enviar foto' : 'Abrir la cámara'}
      </Boton>
    </HojaInferior>
  );
}

/**
 * Audio: graba de inmediato, cuenta los segundos desde que el micrófono
 * empieza a grabar y se detiene con un toque o al llegar al tope (5 minutos por
 * omisión). Si no hay micrófono, ofrece escribir la nota. Si la grabación quedó
 * más pesada de lo que acepta el transcriptor, no la envía y lo dice.
 */
export function HojaAudio({
  onEnviar,
  onCerrar,
  onEscribir,
  maximoSegundos = AUDIO_MAX_POR_DEFECTO,
  maximoBytes = MAX_BYTES_AUDIO,
}: {
  onEnviar: (archivo: Blob) => void;
  onCerrar: () => void;
  onEscribir: () => void;
  maximoSegundos?: number;
  maximoBytes?: number;
}) {
  const [segundos, setSegundos] = useState(0);
  const [grabando, setGrabando] = useState(false);
  const [sinMicrofono, setSinMicrofono] = useState(false);
  const [muyLarga, setMuyLarga] = useState(false);
  const grabadora = useRef<MediaRecorder | null>(null);
  const pistas = useRef<MediaStream | null>(null);
  const trozos = useRef<Blob[]>([]);
  const enviado = useRef(false);
  const iniciada = useRef(false);

  useEffect(() => {
    if (iniciada.current) return;
    iniciada.current = true;
    let cancelado = false;

    const grabar = async () => {
      try {
        const flujo = await navigator.mediaDevices.getUserMedia({ audio: true });
        if (cancelado) {
          flujo.getTracks().forEach((p) => p.stop());
          return;
        }
        pistas.current = flujo;
        const rec = crearGrabadora(flujo);
        grabadora.current = rec;
        rec.ondataavailable = (e) => {
          if (e.data.size > 0) trozos.current.push(e.data);
        };
        // El reloj parte cuando el micrófono de verdad empieza a grabar, no
        // mientras el navegador pide el permiso.
        rec.onstart = () => {
          if (!cancelado) setGrabando(true);
        };
        rec.onstop = () => {
          flujo.getTracks().forEach((p) => p.stop());
          if (enviado.current) return;
          enviado.current = true;
          const audio = new Blob(trozos.current, { type: rec.mimeType || 'audio/webm' });
          trozos.current = [];
          if (audio.size > maximoBytes) {
            setMuyLarga(true);
            return;
          }
          onEnviar(audio);
        };
        rec.start(TROZO_MS);
      } catch {
        // Sin permiso o sin micrófono: mensaje claro, nunca trazas técnicas.
        if (!cancelado) setSinMicrofono(true);
      }
    };

    void grabar();
    return () => {
      cancelado = true;
      enviado.current = true;
      if (grabadora.current?.state === 'recording') grabadora.current.stop();
      pistas.current?.getTracks().forEach((p) => p.stop());
    };
  }, [onEnviar, maximoBytes]);

  useEffect(() => {
    if (!grabando) return;
    const reloj = window.setInterval(() => setSegundos((s) => s + 1), 1000);
    return () => window.clearInterval(reloj);
  }, [grabando]);

  const detener = () => {
    if (grabadora.current?.state === 'recording') {
      setGrabando(false);
      grabadora.current.stop();
    } else {
      onCerrar();
    }
  };

  // Al llegar al tope se envía solo.
  useEffect(() => {
    if (grabando && segundos >= maximoSegundos) detener();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [segundos]);

  if (sinMicrofono) {
    return (
      <HojaInferior titulo="No pudimos usar el micrófono" onCerrar={onCerrar}>
        <p className="mb-[14px] mt-1 text-[15px] text-tinta-2">
          Revisa el permiso del micrófono o escribe la nota, que funciona igual.
        </p>
        <Boton ancho variante="pri" onClick={onEscribir}>
          Escribir la nota
        </Boton>
      </HojaInferior>
    );
  }

  if (muyLarga) {
    return (
      <HojaInferior titulo="No pudimos enviar el audio" onCerrar={onCerrar}>
        <p className="mb-[14px] mt-1 text-[15px] text-tinta-2">
          La grabación es muy larga para enviarla. Graba una más corta.
        </p>
        <Boton ancho variante="pri" onClick={onEscribir}>
          Escribir la nota
        </Boton>
      </HojaInferior>
    );
  }

  const transcurrido = Math.min(segundos, maximoSegundos);

  return (
    <HojaInferior etiqueta="Grabando audio" onCerrar={detener}>
      <div className="flex flex-col items-center gap-[14px] py-4">
        <h2>{grabando || segundos > 0 ? 'Grabando…' : 'Preparando el micrófono…'}</h2>
        <div className="grid h-24 w-24 animate-late place-items-center rounded-full bg-grabar text-white">
          <Mic aria-hidden="true" className="h-8 w-8" />
        </div>
        <span className="text-[34px] font-bold tabular-nums" role="timer">
          {formatoReloj(transcurrido)}
        </span>
        <p className="text-center text-[15px] text-tinta-2">
          Cuenta qué hizo y quién. {textoMaximo(maximoSegundos)} · quedan{' '}
          {formatoReloj(maximoSegundos - transcurrido)}.
        </p>
        <Boton ancho variante="pri" onClick={detener}>
          Listo, enviar
        </Boton>
      </div>
    </HojaInferior>
  );
}

/** Texto: área de texto con el foco puesto y un botón Enviar. */
export function HojaTexto({
  onEnviar,
  onCerrar,
}: {
  onEnviar: (texto: string) => void;
  onCerrar: () => void;
}) {
  const [texto, setTexto] = useState('');
  const area = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    area.current?.focus();
  }, []);

  return (
    <HojaInferior titulo="Escribe lo que viste" onCerrar={onCerrar}>
      <label className="sr-only" htmlFor="nota-texto">
        Nota
      </label>
      <textarea
        id="nota-texto"
        ref={area}
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
        placeholder="Martina armó una torre de 6 bloques y contó hasta 5"
        className="my-3 min-h-[130px] w-full resize-y rounded-campo border border-linea p-3 text-base text-tinta"
      />
      <Boton ancho variante="pri" disabled={texto.trim().length === 0} onClick={() => onEnviar(texto)}>
        Enviar
      </Boton>
    </HojaInferior>
  );
}
