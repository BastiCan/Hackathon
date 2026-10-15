import { describe, expect, it } from 'vitest';
import {
  detectarFormatoAudio,
  MAX_BYTES_AUDIO,
  mensajeProblemaAudio,
  pesoLegible,
  revisarAudio,
} from './audio';

/** Primeros bytes de un archivo: texto ASCII y bytes sueltos. */
function bytes(...partes: (string | number[])[]): Uint8Array {
  const lista: number[] = [];
  for (const p of partes) {
    if (typeof p === 'string') for (const c of p) lista.push(c.charCodeAt(0));
    else lista.push(...p);
  }
  while (lista.length < 16) lista.push(0);
  return new Uint8Array(lista);
}

describe('detectarFormatoAudio (mismas firmas que el transcriptor)', () => {
  it('reconoce los formatos que acepta Transcribe', () => {
    expect(detectarFormatoAudio(bytes([0x1a, 0x45, 0xdf, 0xa3]))).toBe('webm');
    expect(detectarFormatoAudio(bytes('OggS'))).toBe('ogg');
    expect(detectarFormatoAudio(bytes([0, 0, 0, 0x20], 'ftypM4A '))).toBe('m4a');
    expect(detectarFormatoAudio(bytes([0, 0, 0, 0x18], 'ftypmp42'))).toBe('mp4');
    expect(detectarFormatoAudio(bytes('RIFF', [0x24, 0, 0, 0], 'WAVE'))).toBe('wav');
    expect(detectarFormatoAudio(bytes('fLaC'))).toBe('flac');
    expect(detectarFormatoAudio(bytes('#!AMR'))).toBe('amr');
    expect(detectarFormatoAudio(bytes('ID3'))).toBe('mp3');
    expect(detectarFormatoAudio(bytes([0xff, 0xfb, 0x90, 0x64]))).toBe('mp3');
  });

  it('rechaza lo que no es audio, aunque se llame .mp3', () => {
    expect(detectarFormatoAudio(bytes('%PDF-1.7'))).toBeNull();
    expect(detectarFormatoAudio(bytes([0xff, 0xd8, 0xff, 0xe0]))).toBeNull(); // JPEG
    expect(detectarFormatoAudio(bytes('RIFF', [0, 0, 0, 0], 'AVI '))).toBeNull();
    expect(detectarFormatoAudio(new Uint8Array([]))).toBeNull();
  });
});

describe('revisarAudio', () => {
  it('acepta un audio chico con firma válida', async () => {
    const audio = new Blob([bytes('OggS')], { type: '' });
    expect(await revisarAudio(audio)).toEqual({ ok: true, formato: 'ogg' });
  });

  it('avisa si está vacío, si pasa los 4 MB o si no es audio', async () => {
    expect(await revisarAudio(new Blob([]))).toEqual({ ok: false, problema: 'vacio' });
    const grande = new Blob([new Uint8Array(MAX_BYTES_AUDIO + 1)]);
    expect(await revisarAudio(grande)).toEqual({ ok: false, problema: 'grande' });
    const foto = new Blob([bytes([0xff, 0xd8, 0xff, 0xe0])], { type: 'audio/mpeg' });
    expect(await revisarAudio(foto)).toEqual({ ok: false, problema: 'formato' });
  });

  it('el tope es el mismo del transcriptor: 4 MiB', () => {
    expect(MAX_BYTES_AUDIO).toBe(4_194_304);
  });
});

describe('mensajes para la tía', () => {
  it('son claros y sin jerga técnica', () => {
    expect(mensajeProblemaAudio('vacio')).toBe('Ese archivo está vacío. Elige otro audio.');
    expect(mensajeProblemaAudio('grande', 6 * 1024 * 1024)).toBe(
      'Ese audio pesa 6 MB y el máximo es 4 MB. Elige uno más corto.',
    );
    expect(mensajeProblemaAudio('formato')).toContain('m4a, mp3, wav, ogg, webm, flac o amr');
  });

  it('escribe el peso en KB o MB', () => {
    expect(pesoLegible(2048)).toBe('2 KB');
    expect(pesoLegible(1.5 * 1024 * 1024)).toBe('1,5 MB');
  });
});
