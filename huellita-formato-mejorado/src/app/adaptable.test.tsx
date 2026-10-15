// @vitest-environment jsdom
/**
 * Diseño adaptable: celular y computador (`.kiro/ordenes/adaptable-escritorio.md`).
 *
 * jsdom no aplica media queries ni calcula layout, así que aquí se comprueba
 * lo que sí se puede verificar en el código:
 *
 * 1. en celular siguen existiendo la barra inferior fija y, en la ficha, la
 *    barra de captura, y las dos se esconden desde 1024 px (`lg:hidden`);
 * 2. en escritorio aparece la barra lateral con los mismos destinos y, en la
 *    ficha, los mismos 4 botones de captura, sin duplicar la lista de destinos;
 * 3. las pantallas declaran su grilla de escritorio con clases `lg:`;
 * 4. las hojas inferiores se vuelven diálogo centrado y el aviso se va a la
 *    esquina en `lg:`;
 * 5. nada queda con ancho fijo que provoque scroll horizontal: el contenido
 *    usa `min-w-0` y las fotos `max-w-full`.
 */
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { almacenMemoria, DataServiceLocal } from '../services/datos';
import { IAServiceSimulado } from '../services/ia';
import { Rutas } from './App';
import { destinos } from './destinos';
import { ProveedorServicios } from './servicios';

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

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

function uno(selector: string): HTMLElement {
  const el = contenedor.querySelector<HTMLElement>(selector);
  if (!el) throw new Error(`No hay ningún elemento "${selector}"`);
  return el;
}

/** Barra inferior del celular. */
function barraInferior(): HTMLElement {
  return uno('nav[aria-label="Principal"]');
}

/** Barra lateral del computador. */
function barraLateral(): HTMLElement {
  return uno('nav[aria-label="Secciones"]').parentElement as HTMLElement;
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

describe('celular (menos de 1024 px)', () => {
  it('mantiene la barra inferior fija y el hueco que reserva abajo', async () => {
    await montar('/');
    const barra = barraInferior();
    expect(barra.className).toContain('fixed');
    expect(barra.className).toContain('bottom-0');
    // Zona segura del iPhone.
    expect(barra.className).toContain('barra-segura');
    // En Inicio los botones van en la pantalla: el hueco es solo el de la barra.
    expect(uno('main').className).toContain('hueco-barra');
  });

  it('en la ficha el contenido deja el hueco de la barra más el dock', async () => {
    await montar('/nino/NINO-00001');
    // `hueco-dock-nino` cuando ya cargó el nombre del niño/a.
    expect(uno('main').className).toMatch(/hueco-dock(-nino)?\b/);
  });

  it('en Inicio los botones de registrar no se duplican', async () => {
    await montar('/');
    expect(contenedor.querySelector('[aria-label^="Registrar"]')).toBeNull();
    const enPantalla = uno('section[aria-labelledby="titulo-registrar"]');
    expect(enPantalla.querySelectorAll('button')).toHaveLength(4);
  });

  it('en la ficha mantiene la barra de captura con sus 4 botones sobre la barra inferior', async () => {
    await montar('/nino/NINO-00001');
    const docks = [
      ...contenedor.querySelectorAll<HTMLElement>('[aria-label="Registrar para Josefa"]'),
    ];
    // Uno en la barra lateral (escritorio) y otro fijo abajo (celular).
    expect(docks).toHaveLength(2);
    const fijo = docks.find((d) => d.className.includes('fixed'));
    expect(fijo).toBeDefined();
    expect(fijo!.className).toContain('sobre-barra');
    for (const dock of docks) {
      expect(dock.querySelectorAll('.bg-grabar')).toHaveLength(1);
      expect([...dock.querySelectorAll('button')].map((b) => (b.textContent ?? '').trim())).toEqual([
        'Subir foto',
        'Grabar audio',
        'Escribir',
        'Subir audio',
      ]);
    }
  });

  it('sin captura (Revisar) el hueco es solo el de la barra', async () => {
    await montar('/revisar');
    expect(uno('main').className).toContain('hueco-barra');
    expect(contenedor.querySelector('[aria-label="Registrar"]')).toBeNull();
  });
});

describe('escritorio (desde 1024 px)', () => {
  it('la barra inferior y la barra de captura se esconden en lg', async () => {
    await montar('/nino/NINO-00001');
    expect(barraInferior().className).toContain('lg:hidden');
    const fijo = [
      ...contenedor.querySelectorAll<HTMLElement>('[aria-label="Registrar para Josefa"]'),
    ].find((d) => d.className.includes('fixed'));
    expect(fijo!.className).toContain('lg:hidden');
  });

  it('la barra lateral solo se muestra en lg y lleva los mismos destinos', async () => {
    await montar('/');
    const lateral = barraLateral();
    expect(lateral.className).toContain('hidden');
    expect(lateral.className).toContain('lg:flex');
    expect(lateral.className).toContain('w-[232px]');

    const esperados = destinos(false).map((d) => d.a);
    const enLateral = [...lateral.querySelectorAll('a')].map((a) => a.getAttribute('href'));
    expect(enLateral).toEqual(esperados);
    // La barra inferior usa exactamente la misma lista.
    const enBarra = [...barraInferior().querySelectorAll('a')].map((a) => a.getAttribute('href'));
    expect(enBarra).toEqual(esperados);
  });

  it('la barra lateral marca el destino actual en azul con la manchita rosada', async () => {
    await montar('/revisar');
    const actual = barraLateral().querySelector<HTMLElement>('a[aria-current="page"]');
    expect(actual).not.toBeNull();
    expect(actual!.getAttribute('href')).toBe('/revisar');
    expect(actual!.className).toContain('bg-integra-claro');
    expect(actual!.className).toContain('text-integra');
    expect(actual!.querySelectorAll('.bg-rosado')).toHaveLength(1);
  });

  it('la barra lateral muestra el contador de pendientes en Revisar', async () => {
    await montar('/');
    const revisar = barraLateral().querySelector<HTMLElement>('a[href="/revisar"]')!;
    expect(revisar.textContent).toContain('por revisar');
    expect(revisar.querySelectorAll('.bg-aviso-globo')).toHaveLength(1);
  });

  it('la directora ve su destino en la barra lateral y la tía no', async () => {
    await montar('/');
    expect(barraLateral().querySelector('a[href="/directora"]')).toBeNull();
    await datos.cambiarUsuaria('USR-CARMEN');
    await montar('/');
    expect(barraLateral().querySelector('a[href="/directora"]')).not.toBeNull();
  });

  it('el encabezado llega al borde y centra su contenido hasta 1280 px', async () => {
    await montar('/');
    const interior = uno('header img').parentElement as HTMLElement;
    expect(interior.className).toContain('lg:max-w-[1280px]');
    expect(interior.className).toContain('mx-auto');
  });

  it('el contenido se limita a 1000 px y la columna del celular se suelta', async () => {
    await montar('/');
    const principal = uno('main');
    expect(principal.className).toContain('lg:max-w-[1000px]');
    expect(principal.className).toContain('min-w-0');
    expect(principal.className).toContain('lg:px-7');
    // La columna de 480 px deja de limitar en escritorio.
    const columna = principal.closest('.alto-pantalla') as HTMLElement;
    expect(columna.className).toContain('max-w-tia');
    expect(columna.className).toContain('md:max-w-[640px]');
    expect(columna.className).toContain('lg:max-w-none');
  });
});

describe('pantallas en escritorio', () => {
  it('el inicio se abre en dos columnas', async () => {
    await montar('/');
    const semana = uno('[aria-label="Días de la semana"]').parentElement as HTMLElement;
    const grilla = semana.parentElement as HTMLElement;
    expect(grilla.className).toContain('lg:grid');
    expect(grilla.className).toContain('lg:grid-cols-[minmax(0,1fr)_300px]');
    // La semana y los botones a la izquierda; el aviso de pendientes a la derecha.
    expect(semana.className).toContain('lg:col-start-1');
    expect(uno('section[aria-labelledby="titulo-registrar"]').className).toContain('lg:col-start-1');
    expect(uno('.aviso').parentElement!.className).toContain('lg:col-start-2');
    // En escritorio los 4 botones van en una fila.
    const botones = uno('section[aria-labelledby="titulo-registrar"] button').parentElement!;
    expect(botones.className).toContain('lg:grid-cols-4');
  });

  it('la planilla de la sala ocupa el ancho sin truncar los nombres', async () => {
    await montar('/sala');
    const tabla = uno('table');
    expect(tabla.className).toContain('w-full');
    expect(tabla.className).toContain('lg:text-[15px]');
    // El desplazamiento horizontal queda solo en celular.
    expect(tabla.parentElement!.className).toContain('overflow-x-auto');
    expect(tabla.parentElement!.className).toContain('lg:overflow-x-visible');
    const nombre = uno('tbody th span');
    expect(nombre.className).toContain('truncate');
    expect(nombre.className).toContain('lg:max-w-none');
  });

  it('Revisar reparte las tarjetas en dos columnas', async () => {
    await montar('/revisar');
    const tarjeta = uno('article');
    const grilla = tarjeta.parentElement as HTMLElement;
    expect(grilla.className).toContain('lg:grid');
    expect(grilla.className).toContain('lg:grid-cols-2');
    expect(grilla.className).toContain('lg:items-start');
    // Sin margen entre tarjetas en escritorio: el espacio lo da la grilla.
    expect(tarjeta.className).toContain('mb-4');
    expect(tarjeta.className).toContain('lg:mb-0');
  });

  it('la ficha del niño o niña se abre en dos columnas', async () => {
    await montar('/nino/NINO-00001');
    const grilla = uno('.aviso').parentElement!.parentElement as HTMLElement;
    expect(grilla.className).toContain('lg:grid');
    expect(grilla.className).toContain('lg:grid-cols-2');
  });

  it('la directora ve las salas en tres columnas', async () => {
    await datos.cambiarUsuaria('USR-CARMEN');
    await montar('/directora');
    expect(uno('[aria-label="Salas del jardín"]').className).toContain('lg:grid-cols-3');
  });

  it('la entrada es una tarjeta centrada con la lista en dos columnas', async () => {
    await montar('/entrada');
    const lista = uno('ul');
    expect(lista.className).toContain('lg:grid-cols-2');
    const tarjeta = lista.closest('.alto-pantalla') as HTMLElement;
    expect(tarjeta.className).toContain('lg:w-[560px]');
    expect(tarjeta.className).toContain('lg:rounded-tarjeta');
  });
});

describe('hojas y avisos', () => {
  it('la hoja inferior se vuelve diálogo centrado en escritorio', async () => {
    await montar('/sala');
    await tocar(uno('[aria-label="Qué significan los colores"]'));
    const dialogo = uno('[role="dialog"]');
    expect(dialogo.className).toContain('lg:max-w-[520px]');
    // Las 4 esquinas redondeadas, no solo las de arriba.
    expect(dialogo.className).toContain('lg:rounded-hoja');
    const velo = dialogo.parentElement as HTMLElement;
    expect(velo.className).toContain('items-end');
    expect(velo.className).toContain('lg:items-center');
  });

  it('el aviso se va abajo a la derecha con 380 px en escritorio', async () => {
    await montar('/revisar');
    const confirmar = [...contenedor.querySelectorAll('button')].find((b) =>
      (b.textContent ?? '').trim().startsWith('Confirmar'),
    )!;
    await tocar(confirmar as HTMLElement);
    await act(async () => {
      await new Promise((listo) => setTimeout(listo, 220));
    });
    const globo = uno('[role="status"]').parentElement as HTMLElement;
    expect(globo.className).toContain('lg:right-6');
    expect(globo.className).toContain('lg:w-[380px]');
    expect(globo.className).toContain('aviso-flotante');
  });
});

describe('sin scroll horizontal', () => {
  const RUTAS = ['/', '/sala', '/revisar', '/nino/NINO-00001'];

  for (const ruta of RUTAS) {
    it(`${ruta} no deja anchos fijos ni fotos sin tope`, async () => {
      await montar(ruta);
      // Ninguna imagen puede pasarse del ancho de su columna: o declara un
      // tope (`max-w-full`, `w-full`, `w-auto`) o es una miniatura con un
      // ancho fijo chico (56 u 84 px).
      for (const img of contenedor.querySelectorAll<HTMLImageElement>('img')) {
        const clases = img.className;
        const anchoFijo = Number.parseInt(img.style.width, 10);
        const acotada =
          clases.includes('max-w-full') ||
          clases.includes('w-full') ||
          clases.includes('w-auto') ||
          (Number.isFinite(anchoFijo) && anchoFijo <= 120);
        expect(acotada, img.outerHTML.slice(0, 120)).toBe(true);
      }
      // El contenido puede encogerse dentro de la grilla de escritorio.
      expect(uno('main').className).toContain('min-w-0');
    });
  }
});
