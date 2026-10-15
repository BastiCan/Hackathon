// @vitest-environment jsdom
/**
 * Ajustes de la versión AWS (tarea 3 del plan de integración): agenda oculta,
 * foto desactivable y audio de hasta 5 minutos a 48 kbps. Las pantallas se
 * montan con `ProveedorOpciones`, como si la app se hubiera compilado con
 * `VITE_AGENDA=false`.
 */
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { formatoReloj, HojaAudio, textoMaximo } from '../components/Captura';
import { almacenMemoria, DataServiceLocal } from '../services/datos';
import { IAServiceSimulado } from '../services/ia';
import { Rutas } from './App';
import { AUDIO_MAX_MINIMO, leerConfig, MAX_BYTES_AUDIO } from './config';
import { destinos } from './destinos';
import { ProveedorOpciones } from './opciones';
import { ProveedorServicios } from './servicios';

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let contenedor: HTMLDivElement;
let raiz: Root;
let datos: DataServiceLocal;

/** Un servicio de datos que, como el de AWS, todavía no recibe fotos. */
class DatosSinFoto extends DataServiceLocal {
  readonly admiteFoto = false;
}

async function montar(ruta: string, agenda = false) {
  await act(async () => {
    raiz.render(
      <ProveedorOpciones agenda={agenda}>
        <ProveedorServicios datos={datos} ia={new IAServiceSimulado({ latenciaMs: 0 })}>
          <MemoryRouter initialEntries={[ruta]}>
            <Rutas />
          </MemoryRouter>
        </ProveedorServicios>
      </ProveedorOpciones>,
    );
  });
}

function texto(): string {
  return contenedor.textContent ?? '';
}

function botonPor(nombre: string): HTMLButtonElement {
  const botones = [...contenedor.querySelectorAll('button')];
  const encontrado =
    botones.find((b) => (b.textContent ?? '').trim() === nombre) ??
    botones.find((b) => (b.textContent ?? '').includes(nombre));
  if (!encontrado) throw new Error(`No hay botón con el texto "${nombre}"`);
  return encontrado as HTMLButtonElement;
}

async function tocar(elemento: HTMLElement) {
  await act(async () => {
    elemento.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
  });
}

beforeEach(async () => {
  datos = new DataServiceLocal({ almacen: almacenMemoria() });
  await datos.cambiarUsuaria('EDU-0001');
  contenedor = document.createElement('div');
  document.body.appendChild(contenedor);
  raiz = createRoot(contenedor);
});

afterEach(() => {
  act(() => raiz.unmount());
  contenedor.remove();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('opciones de compilación', () => {
  it('sin variables queda como la Fase 1', () => {
    expect(leerConfig({})).toEqual({ datos: 'local', agenda: true, audioMaxSegundos: 300 });
  });

  it('lee la versión AWS', () => {
    const config = leerConfig({
      VITE_DATOS: 'http',
      VITE_AGENDA: 'false',
      VITE_AUDIO_MAX_SEGUNDOS: '420',
      VITE_FECHA_HOY: '2026-10-15',
    });
    expect(config).toEqual({ datos: 'http', agenda: false, audioMaxSegundos: 420, fechaHoy: '2026-10-15' });
  });

  it('nunca deja el tope de audio bajo 4 minutos', () => {
    expect(leerConfig({ VITE_AUDIO_MAX_SEGUNDOS: '60' }).audioMaxSegundos).toBe(AUDIO_MAX_MINIMO);
    expect(leerConfig({ VITE_AUDIO_MAX_SEGUNDOS: 'mucho' }).audioMaxSegundos).toBe(300);
  });
});

describe('sin agenda', () => {
  it('el inicio es Mi sala y el menú no muestra la agenda', async () => {
    await montar('/');
    expect(texto()).toContain('Planilla de la sala');
    expect(contenedor.querySelector('a[href="/"]')).toBeNull();
    expect(destinos(false, false).map((d) => d.a)).toEqual(['/sala', '/revisar']);
    const enBarra = [...contenedor.querySelectorAll('nav[aria-label="Principal"] a')].map((a) =>
      a.getAttribute('href'),
    );
    expect(enBarra).toEqual(['/sala', '/revisar']);
  });

  it('la captura acompaña a Mi sala', async () => {
    await montar('/sala');
    const docks = contenedor.querySelectorAll('[aria-label="Registrar"]');
    // Uno en la barra lateral (escritorio) y otro fijo abajo (celular).
    expect(docks).toHaveLength(2);
    expect(contenedor.querySelector('main')?.className).toContain('hueco-dock');
  });

  it('al entrar, la tía llega a Mi sala', async () => {
    await datos.reiniciarDemo();
    await montar('/entrada');
    await tocar(botonPor('Tía Ana'));
    expect(texto()).toContain('Planilla de la sala');
    expect(texto()).toContain('Sala A');
  });

  it('una tía que abre la vista directora vuelve a Mi sala', async () => {
    await montar('/directora');
    expect(texto()).toContain('Planilla de la sala');
    expect(texto()).not.toContain('Salas del jardín');
  });

  it('con la agenda visible, el inicio sigue siendo la agenda', async () => {
    await montar('/', true);
    expect(texto()).toContain('Agenda · Sala A');
  });
});

describe('sin foto', () => {
  it('si el servicio no recibe fotos, la captura solo ofrece Grabar y Escribir', async () => {
    datos = new DatosSinFoto({ almacen: almacenMemoria() });
    await datos.cambiarUsuaria('EDU-0001');
    await montar('/sala');
    for (const dock of contenedor.querySelectorAll('[aria-label="Registrar"]')) {
      const botones = [...dock.querySelectorAll('button')].map((b) => b.textContent?.trim());
      expect(botones).toEqual(['Grabar', 'Escribir']);
    }
  });
});

/** MediaRecorder de mentira: guarda las opciones y entrega un audio del tamaño pedido. */
class GrabadoraFalsa {
  static ultima: GrabadoraFalsa | null = null;
  static rechazarOpciones = false;
  static tamano = 1000;
  static opciones: MediaRecorderOptions | undefined;

  state: RecordingState = 'inactive';
  mimeType = 'audio/webm';
  ondataavailable: ((e: { data: Blob }) => void) | null = null;
  onstart: (() => void) | null = null;
  onstop: (() => void) | null = null;
  trozo?: number;

  constructor(_flujo: MediaStream, opciones?: MediaRecorderOptions) {
    if (opciones && GrabadoraFalsa.rechazarOpciones) throw new Error('NotSupportedError');
    GrabadoraFalsa.opciones = opciones;
    GrabadoraFalsa.ultima = this;
  }

  start(trozo?: number) {
    this.trozo = trozo;
    this.state = 'recording';
  }

  stop() {
    this.state = 'inactive';
    this.ondataavailable?.({ data: new Blob([new Uint8Array(GrabadoraFalsa.tamano)]) });
    this.onstop?.();
  }
}

describe('audio', () => {
  let enviados: Blob[];

  beforeEach(() => {
    enviados = [];
    GrabadoraFalsa.ultima = null;
    GrabadoraFalsa.rechazarOpciones = false;
    GrabadoraFalsa.tamano = 1000;
    GrabadoraFalsa.opciones = undefined;
    vi.stubGlobal('MediaRecorder', GrabadoraFalsa);
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia: async () => ({ getTracks: () => [{ stop: () => {} }] }) },
    });
  });

  async function abrirGrabadora(maximoSegundos = 300) {
    vi.useFakeTimers();
    await act(async () => {
      raiz.render(
        <HojaAudio
          onEnviar={(audio) => enviados.push(audio)}
          onCerrar={() => {}}
          onEscribir={() => {}}
          maximoSegundos={maximoSegundos}
        />,
      );
    });
    // Deja que se resuelva el permiso del micrófono.
    await act(async () => {
      await Promise.resolve();
    });
  }

  async function avanzar(segundos: number) {
    await act(async () => {
      vi.advanceTimersByTime(segundos * 1000);
    });
  }

  function reloj(): string {
    return contenedor.querySelector('[role="timer"]')?.textContent ?? '';
  }

  it('graba a 48 kbps en trozos de un segundo', async () => {
    await abrirGrabadora();
    expect(GrabadoraFalsa.opciones).toEqual({ audioBitsPerSecond: 48000 });
    expect(GrabadoraFalsa.ultima?.trozo).toBe(1000);
  });

  it('si el navegador no acepta la opción, graba igual', async () => {
    GrabadoraFalsa.rechazarOpciones = true;
    await abrirGrabadora();
    expect(GrabadoraFalsa.ultima?.state).toBe('recording');
  });

  it('el reloj parte cuando empieza a grabar y se envía solo al llegar a 5 minutos', async () => {
    await abrirGrabadora();
    // Mientras el micrófono no empieza (permiso, arranque), el reloj no corre.
    await avanzar(5);
    expect(reloj()).toBe('0:00');
    expect(texto()).toContain('Máximo 5 minutos');

    await act(async () => GrabadoraFalsa.ultima?.onstart?.());
    await avanzar(180);
    expect(reloj()).toBe('3:00');
    expect(texto()).toContain('quedan 2:00');
    expect(enviados).toHaveLength(0);

    await avanzar(120);
    expect(enviados).toHaveLength(1);
    expect(GrabadoraFalsa.ultima?.state).toBe('inactive');
  });

  it('una grabación de más de 4 MiB no se envía y se avisa', async () => {
    GrabadoraFalsa.tamano = MAX_BYTES_AUDIO + 1;
    await abrirGrabadora();
    await act(async () => GrabadoraFalsa.ultima?.onstart?.());
    await avanzar(10);
    await tocar(botonPor('Listo, enviar'));
    expect(enviados).toHaveLength(0);
    expect(texto()).toContain('La grabación es muy larga para enviarla. Graba una más corta.');
  });

  it('escribe el reloj y el tope en palabras', () => {
    expect(formatoReloj(0)).toBe('0:00');
    expect(formatoReloj(75)).toBe('1:15');
    expect(formatoReloj(300)).toBe('5:00');
    expect(textoMaximo(300)).toBe('Máximo 5 minutos');
    expect(textoMaximo(270)).toBe('Máximo 4 minutos y 30 segundos');
  });
});
