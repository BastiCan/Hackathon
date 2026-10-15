/**
 * Revisión de un audio que la tía sube desde su celular o computador. Sigue las
 * mismas reglas del transcriptor del backend
 * (`servicio_transcripcion/src/transcriptor/audio.py`, rama
 * `feature/transcriptor-audio`): el formato se reconoce por los primeros bytes
 * del archivo, no por el tipo MIME ni la extensión, y el tope es de 4 MiB.
 * Así, lo que Huellita acepta aquí es lo que el transcriptor puede leer.
 */

/** Tope del transcriptor (`MAX_BYTES_AUDIO`): 4 MiB de audio. */
export const MAX_BYTES_AUDIO = 4 * 1024 * 1024;

/** Contenedores que acepta Amazon Transcribe por lotes. */
export type FormatoAudio = 'webm' | 'ogg' | 'mp4' | 'm4a' | 'wav' | 'flac' | 'amr' | 'mp3';

/**
 * Para el selector de archivos del sistema. Incluye las extensiones porque
 * algunos celulares no asocian `.m4a`, `.opus` o `.amr` con `audio/*`.
 */
export const ACEPTA_AUDIO =
  'audio/*,.m4a,.mp4,.mp3,.wav,.ogg,.oga,.opus,.webm,.flac,.amr';

/** Formatos en palabras, para los mensajes a la tía. */
export const FORMATOS_AUDIO_TEXTO = 'm4a, mp3, wav, ogg, webm, flac o amr';

function empiezaCon(bytes: Uint8Array, firma: string, desde = 0): boolean {
  if (bytes.length < desde + firma.length) return false;
  for (let i = 0; i < firma.length; i += 1) {
    if (bytes[desde + i] !== firma.charCodeAt(i)) return false;
  }
  return true;
}

/** Reconoce el formato por los primeros 12 bytes; `null` si no es uno aceptado. */
export function detectarFormatoAudio(bytes: Uint8Array): FormatoAudio | null {
  const c = bytes.subarray(0, 12);
  // EBML: WebM de MediaRecorder (Chrome, Firefox, Android).
  if (c.length >= 4 && c[0] === 0x1a && c[1] === 0x45 && c[2] === 0xdf && c[3] === 0xa3) {
    return 'webm';
  }
  // Ogg: también las notas de voz .opus de WhatsApp.
  if (empiezaCon(c, 'OggS')) return 'ogg';
  // MP4/M4A: la grabadora de Windows, Safari e iOS.
  if (empiezaCon(c, 'ftyp', 4)) return empiezaCon(c, 'M4A', 8) ? 'm4a' : 'mp4';
  if (empiezaCon(c, 'RIFF') && empiezaCon(c, 'WAVE', 8)) return 'wav';
  if (empiezaCon(c, 'fLaC')) return 'flac';
  if (empiezaCon(c, '#!AMR')) return 'amr';
  if (empiezaCon(c, 'ID3')) return 'mp3';
  // Trama MPEG capa III sin etiqueta ID3.
  if (c.length > 1 && c[0] === 0xff && (c[1] & 0xe0) === 0xe0 && (c[1] & 0x06) === 0x02) {
    return 'mp3';
  }
  return null;
}

export type ProblemaAudio = 'vacio' | 'grande' | 'formato';

export type RevisionAudio =
  | { ok: true; formato: FormatoAudio }
  | { ok: false; problema: ProblemaAudio };

/** Los primeros 12 bytes. `FileReader` queda de respaldo para Safari antiguo. */
async function leerInicio(archivo: Blob): Promise<Uint8Array> {
  const trozo = archivo.slice(0, 12);
  if (typeof trozo.arrayBuffer === 'function') return new Uint8Array(await trozo.arrayBuffer());
  return new Promise((listo, falla) => {
    const lector = new FileReader();
    lector.onload = () => listo(new Uint8Array(lector.result as ArrayBuffer));
    lector.onerror = () => falla(lector.error);
    lector.readAsArrayBuffer(trozo);
  });
}

/** Revisa tamaño y formato sin leer el archivo completo. */
export async function revisarAudio(archivo: Blob): Promise<RevisionAudio> {
  if (archivo.size === 0) return { ok: false, problema: 'vacio' };
  if (archivo.size > MAX_BYTES_AUDIO) return { ok: false, problema: 'grande' };
  const formato = detectarFormatoAudio(await leerInicio(archivo));
  return formato ? { ok: true, formato } : { ok: false, problema: 'formato' };
}

/** "3,2 MB": peso del archivo para mostrarlo a la tía. */
export function pesoLegible(bytes: number): string {
  const mb = bytes / (1024 * 1024);
  if (mb < 0.1) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${mb.toLocaleString('es-CL', { maximumFractionDigits: 1 })} MB`;
}

/** Mensaje claro, sin jerga técnica, para cada problema. */
export function mensajeProblemaAudio(problema: ProblemaAudio, bytes = 0): string {
  if (problema === 'vacio') return 'Ese archivo está vacío. Elige otro audio.';
  if (problema === 'grande') {
    return `Ese audio pesa ${pesoLegible(bytes)} y el máximo es 4 MB. Elige uno más corto.`;
  }
  return `Huellita no puede leer ese archivo. Sirven audios ${FORMATOS_AUDIO_TEXTO}.`;
}
