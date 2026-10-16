// @vitest-environment jsdom
/**
 * El guion de `DEMO.md` corrido de principio a fin después de "Reiniciar demo"
 * (tarea 13). Lo que no existe en jsdom (cámara y micrófono) se captura
 * llamando a `capturar()`, que es exactamente lo que hacen las hojas de Foto y
 * Audio al enviar; el resto del recorrido pasa por la interfaz.
 */
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { capturar } from '../services/captura';
import { almacenMemoria, DataServiceLocal } from '../services/datos';
import { IAServiceSimulado } from '../services/ia';
import { Rutas } from './App';
import { ProveedorServicios } from './servicios';

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let contenedor: HTMLDivElement;
let raiz: Root;
let datos: DataServiceLocal;
let ia: IAServiceSimulado;

async function montar(ruta: string) {
  await act(async () => {
    raiz.render(
      <ProveedorServicios datos={datos} ia={ia}>
        <MemoryRouter initialEntries={[ruta]}>
          <Rutas />
        </MemoryRouter>
      </ProveedorServicios>,
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

/** Destino de la barra inferior ("Mi sala", "Revisar", "Directora"). */
function destinoPor(nombre: string): HTMLAnchorElement {
  const enlaces = [...contenedor.querySelectorAll('nav a')];
  const encontrado = enlaces.find((a) => (a.textContent ?? '').includes(nombre));
  if (!encontrado) throw new Error(`No hay destino "${nombre}" en la barra`);
  return encontrado as HTMLAnchorElement;
}

async function tocar(elemento: HTMLElement) {
  await act(async () => {
    // `cancelable` deja que React Router haga `preventDefault` y jsdom no
    // intente navegar de verdad.
    elemento.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
  });
}

/** Deja pasar la transición de salida de una nota resuelta. */
async function esperarSalida() {
  await act(async () => {
    await new Promise((listo) => setTimeout(listo, 220));
  });
}

/** Captura como lo hacen las hojas de Foto y Audio (archivo en memoria). */
async function capturarArchivo(formato: 'foto' | 'audio') {
  const archivo = new Blob(['archivo-de-la-demo'], {
    type: formato === 'foto' ? 'image/jpeg' : 'audio/webm',
  });
  await act(async () => {
    const { procesada } = await capturar(formato, archivo, undefined, undefined, { datos, ia });
    await procesada;
  });
}

beforeEach(async () => {
  datos = new DataServiceLocal({ almacen: almacenMemoria() });
  ia = new IAServiceSimulado({ latenciaMs: 0 });
  // Paso 0: "Reiniciar demo" deja los datos como en la semilla.
  await datos.reiniciarDemo();
  contenedor = document.createElement('div');
  document.body.appendChild(contenedor);
  raiz = createRoot(contenedor);
});

afterEach(() => {
  act(() => raiz.unmount());
  contenedor.remove();
});

describe('guion de la demo', () => {
  it('se puede correr completo después de reiniciar', async () => {
    // 1. Entrar como tía Ana: su inicio de hoy y la planilla de la sala.
    await montar('/entrada');
    expect(texto()).toContain('¿Quién entra hoy?');
    await tocar(botonPor('Tía Ana'));
    expect(texto()).toContain('Inicio · Sala A');
    expect(texto()).toContain('por revisar');
    // Tía Ana tiene una sola sala: Inicio dice dónde registra, sin selector.
    expect(contenedor.querySelector('#titulo-registrar')?.textContent).toBe('Registrar en Sala A');
    expect(texto()).toContain('Subir audio');
    await tocar(destinoPor('Sala'));
    expect(contenedor.querySelector('[aria-label^="Josefa"]')).not.toBeNull();
    expect(contenedor.querySelectorAll('tbody tr')).toHaveLength(13);
    // Cada número lleva el color de su nivel; el lector de pantalla lo nombra.
    expect(texto()).toMatch(/Nivel \d/);

    // 2. Foto del post-it: llega a Revisar el guion de Josefa.
    await capturarArchivo('foto');
    await tocar(destinoPor('Revisar'));
    expect(texto()).toContain('¿Está bien lo que leyó Huellita?');
    expect(texto()).toContain('se agacha y recoge los individuales');
    expect(texto()).toContain('Josefa');
    expect(texto()).toContain('Alta');
    // La foto de ejemplo del post-it queda guardada y se muestra.
    expect(contenedor.querySelector('img[alt="Foto del post-it"]')).not.toBeNull();

    // 3. Confirmarla y verla en la ficha de Josefa.
    await tocar(botonPor('Confirmar'));
    await esperarSalida();
    expect(texto()).toContain('Guardado en la ficha de Josefa');
    await tocar(destinoPor('Sala'));
    await tocar(contenedor.querySelector<HTMLButtonElement>('[aria-label^="Josefa"]')!);
    expect(texto()).toContain('Registrar para Josefa');
    expect(texto()).toContain('se agacha y recoge los individuales');
    expect(texto()).toContain('Socioemocional');

    // 4. Otra foto: guion de Emilio y corrección del nivel con "Corregir".
    await capturarArchivo('foto');
    await tocar(destinoPor('Revisar'));
    expect(texto()).toContain('clasificó las hojas del otoño');
    expect(texto()).toContain('Emilio');
    const antesEmilio = (await datos.sugerencias({ ninoId: 'NINO-00453' })).find(
      (s) => s.estado === 'pendiente',
    );
    const nivelPropuesto = antesEmilio?.nivel;
    await tocar(botonPor('Corregir'));
    expect(texto()).toContain('Corregir evaluación');
    // Se corrige a un nivel distinto del propuesto para comprobar el cambio.
    await tocar(botonPor('Combinación y participación')); // nivel 8
    await tocar(botonPor('Guardar corrección'));
    await esperarSalida();
    expect(texto()).toContain('Corregido y guardado');
    const deEmilio = await datos.sugerencias({ ninoId: 'NINO-00453' });
    const cambiada = deEmilio.find((s) => s.estado === 'cambiada');
    expect(cambiada?.nivel).toBe(8);
    expect(cambiada?.original?.nivel).toBe(nivelPropuesto);

    // 5. Subir audio: una nota de voz grupal se ofrece guardar en la sala, no
    //    evaluar a un niño/a.
    await capturarArchivo('audio');
    expect(texto()).toContain('Nota de la sala');
    expect(texto()).toContain('bajó la asistencia');
    await tocar(botonPor('Guardar en la sala'));
    await esperarSalida();
    expect(texto()).toContain('Nota guardada');

    // 6. Entrar como directora y ver el avance de las salas del jardín.
    await tocar(destinoPor('Inicio'));
    await tocar(contenedor.querySelector<HTMLButtonElement>('[aria-label^="Menú de"]')!);
    await tocar(botonPor('Cambiar de usuaria'));
    expect(texto()).toContain('¿Quién entra hoy?');
    await tocar(botonPor('Directora Carmen'));
    await tocar(destinoPor('Directora'));
    expect(texto()).toContain('Salas');
    expect(texto()).toContain('Sala B');
    expect(texto()).toContain('observados en 30 días');
    await tocar(botonPor('Sala A'));
    expect(texto()).toContain('Vista de la directora · solo lectura');
  });
});
