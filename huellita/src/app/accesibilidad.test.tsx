// @vitest-environment jsdom
/**
 * Revisión automática de accesibilidad (tarea 10). jsdom no calcula layout, así
 * que aquí se comprueba lo que sí se puede verificar en el código:
 *
 * 1. todo control tiene nombre accesible (texto o `aria-label`);
 * 2. todo control declara un área táctil de 44 px o más;
 * 3. ninguna pantalla muestra imágenes de niños o niñas;
 * 4. las hojas inferiores son diálogos modales y atrapan el foco.
 */
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { almacenMemoria, DataServiceLocal } from '../services/datos';
import { IAServiceSimulado } from '../services/ia';
import { Rutas } from './App';
import { ProveedorServicios } from './servicios';

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const RUTAS_TIA = ['/', '/revisar', '/nino/NINO-00001', '/entrada'];
const RUTAS_DIRECTORA = ['/directora', '/directora/sala/SALA-MMA'];

/** Clases con las que un control declara al menos 44 px de alto. */
const ALTO_SUFICIENTE = [
  'min-h-tactil', // 44 px
  'h-11', // 44 px
  'h-[54px]',
  'h-[76px]',
  'h-24', // 96 px (botón de grabar)
  'flex-1', // destinos de la barra inferior, que mide 72 px
  'nino', // tarjeta de niño/a: 124 px de alto mínimo
];

let contenedor: HTMLDivElement;
let raiz: Root;
let datos: DataServiceLocal;

async function montar(ruta: string) {
  await act(async () => {
    raiz.render(
      <ProveedorServicios datos={datos} ia={new IAServiceSimulado({ latenciaMs: 0 })}>
        <MemoryRouter initialEntries={[ruta]}>
          <Rutas />
        </MemoryRouter>
      </ProveedorServicios>,
    );
  });
}

async function tocar(elemento: HTMLElement) {
  await act(async () => {
    elemento.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
}

function controles(): HTMLElement[] {
  return [...contenedor.querySelectorAll<HTMLElement>('button, a[href], select, textarea')];
}

function nombreAccesible(el: HTMLElement): string {
  return (el.getAttribute('aria-label') ?? el.textContent ?? '').trim();
}

function declaraAreaTactil(el: HTMLElement): boolean {
  const clases = el.className ?? '';
  const altoMinimo = /min-h-\[(\d+)px\]/.exec(clases);
  if (altoMinimo && Number(altoMinimo[1]) >= 44) return true;
  const alto = /(?:^|\s)h-\[(\d+)px\]/.exec(clases);
  if (alto && Number(alto[1]) >= 44) return true;
  return ALTO_SUFICIENTE.some((c) => clases.split(/\s+/).includes(c));
}

beforeEach(async () => {
  datos = new DataServiceLocal({ almacen: almacenMemoria() });
  await datos.cambiarUsuaria('USR-ANA');
  contenedor = document.createElement('div');
  document.body.appendChild(contenedor);
  raiz = createRoot(contenedor);
});

afterEach(() => {
  act(() => raiz.unmount());
  contenedor.remove();
});

describe('nombre accesible', () => {
  for (const ruta of RUTAS_TIA) {
    it(`todos los controles de ${ruta} se pueden nombrar`, async () => {
      await montar(ruta);
      const sinNombre = controles().filter((el) => nombreAccesible(el).length === 0);
      expect(sinNombre.map((el) => el.outerHTML.slice(0, 120))).toEqual([]);
    });
  }

  it('los controles de la directora también', async () => {
    await datos.cambiarUsuaria('USR-CARMEN');
    for (const ruta of RUTAS_DIRECTORA) {
      await montar(ruta);
      const sinNombre = controles().filter((el) => nombreAccesible(el).length === 0);
      expect(sinNombre.map((el) => el.outerHTML.slice(0, 120))).toEqual([]);
    }
  });

  it('las hojas inferiores declaran su nombre y son modales', async () => {
    await montar('/');
    const ayuda = contenedor.querySelector<HTMLButtonElement>(
      '[aria-label="Qué significan los colores"]',
    );
    await tocar(ayuda!);
    const dialogo = contenedor.querySelector('[role="dialog"]');
    expect(dialogo?.getAttribute('aria-modal')).toBe('true');
    expect(dialogo?.getAttribute('aria-label')).toBe('Qué significan los colores');
  });
});

describe('áreas táctiles', () => {
  for (const ruta of RUTAS_TIA) {
    it(`los controles de ${ruta} declaran 44 px o más`, async () => {
      await montar(ruta);
      const chicos = controles().filter((el) => !declaraAreaTactil(el));
      expect(chicos.map((el) => el.outerHTML.slice(0, 120))).toEqual([]);
    });
  }

  it('el dock de captura mantiene los tamaños del prototipo', async () => {
    await montar('/');
    const dock = contenedor.querySelector('[aria-label="Registrar"]');
    expect(dock).not.toBeNull();
    // Foto y Texto de 54 px; Audio al centro de 76 px.
    expect(dock!.querySelectorAll('.h-\\[54px\\]')).toHaveLength(2);
    expect(dock!.querySelectorAll('.h-\\[76px\\]')).toHaveLength(1);
  });
});

describe('privacidad en pantalla', () => {
  for (const ruta of RUTAS_TIA) {
    it(`${ruta} no muestra imágenes de niños ni niñas`, async () => {
      await montar(ruta);
      expect(contenedor.querySelectorAll('img')).toHaveLength(0);
    });
  }
});

describe('foco', () => {
  it('el tabulador se queda dentro de la hoja abierta', async () => {
    await montar('/');
    await tocar(
      contenedor.querySelector<HTMLButtonElement>('[aria-label="Qué significan los colores"]')!,
    );
    const dialogo = contenedor.querySelector<HTMLElement>('[role="dialog"]')!;
    expect(document.activeElement).toBe(dialogo);

    // Con el foco en el diálogo, Shift+Tab va al último control de la hoja.
    const enfocables = [...dialogo.querySelectorAll<HTMLElement>('button, a[href], select')];
    await act(async () => {
      document.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'Tab', shiftKey: true, bubbles: true }),
      );
    });
    expect(dialogo.contains(document.activeElement)).toBe(true);
    expect(document.activeElement).toBe(enfocables[enfocables.length - 1]);
  });

  it('Escape cierra la hoja', async () => {
    await montar('/');
    await tocar(
      contenedor.querySelector<HTMLButtonElement>('[aria-label="Qué significan los colores"]')!,
    );
    expect(contenedor.querySelector('[role="dialog"]')).not.toBeNull();
    await act(async () => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    });
    expect(contenedor.querySelector('[role="dialog"]')).toBeNull();
  });
});
