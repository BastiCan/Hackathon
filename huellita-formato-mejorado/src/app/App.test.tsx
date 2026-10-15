// @vitest-environment jsdom
/**
 * Prueba de humo de las pantallas: se montan con un `DataServiceLocal` en
 * memoria (sin tocar `localStorage` del navegador) y una IA sin latencia, para
 * comprobar que Inicio, Sala, Revisar y la ficha se dibujan y que validar una
 * nota la saca de Revisar.
 */
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { colorNivel } from '../lib/rubrica';
import type { Nivel } from '../lib/tipos';
import { almacenMemoria, DataServiceLocal } from '../services/datos';
import { IAServiceSimulado } from '../services/ia';
import { Rutas } from './App';
import { ALT_LOGO } from './Encabezado';
import { ProveedorServicios } from './servicios';

// React 18 pide esta marca para que `act` no avise en cada render.
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

function texto(): string {
  return contenedor.textContent ?? '';
}

/**
 * Imágenes de la pantalla sin contar el logo oficial del encabezado, para
 * seguir exigiendo cero fotos de niños y niñas.
 */
function imagenesSinLogo(): HTMLImageElement[] {
  return [...contenedor.querySelectorAll('img')].filter(
    (img) => img.getAttribute('alt') !== ALT_LOGO,
  );
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
    elemento.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
}

/** Elige una opción de un `<select>` como lo haría la tía. */
async function elegir(selector: HTMLSelectElement, valor: string) {
  await act(async () => {
    selector.value = valor;
    selector.dispatchEvent(new Event('change', { bubbles: true }));
  });
}

/** Escribe en un `<textarea>` controlado por React. */
async function escribir(area: HTMLTextAreaElement, valor: string) {
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')!.set!.call(area, valor);
    area.dispatchEvent(new Event('input', { bubbles: true }));
  });
}

/** Deja pasar la transición de salida de una nota resuelta (160 ms). */
async function esperarSalida() {
  await act(async () => {
    await new Promise((listo) => setTimeout(listo, 220));
  });
}

/** "#2F6BC4" → "rgb(47, 107, 196)", como jsdom escribe los colores. */
function rgb(hex: string): string {
  const n = Number.parseInt(hex.slice(1), 16);
  return `rgb(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255})`;
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

describe('Inicio', () => {
  it('muestra el encabezado oficial, la semana, el aviso y los botones para registrar', async () => {
    await montar('/');
    // El encabezado lleva el logo oficial Mineduc + Integra, no un sello dibujado.
    const logo = contenedor.querySelector(`header img[alt="${ALT_LOGO}"]`);
    expect(logo).not.toBeNull();
    expect(logo!.getAttribute('src')).toBeTruthy();
    expect(texto()).toContain('Inicio · Medio Menor A');
    expect(texto()).toContain('Jueves 15 de octubre');
    expect(texto()).toContain('3 por revisar');
    expect(texto()).toContain('registro IEA (noviembre)');
    expect(contenedor.querySelectorAll('[aria-label="Días de la semana"] li')).toHaveLength(5);
    // La jornada de la agenda ya no está: en su lugar van los botones.
    expect(texto()).not.toContain('Experiencia de aprendizaje');
    const botones = [
      ...contenedor.querySelectorAll('section[aria-labelledby="titulo-registrar"] button'),
    ].map((b) => b.textContent ?? '');
    expect(botones).toHaveLength(4);
    ['Subir foto', 'Grabar audio', 'Escribir', 'Subir audio'].forEach((etiqueta, i) =>
      expect(botones[i]).toContain(etiqueta),
    );
  });

  it('la semana dice cuántos registros hay cada día y cuántos faltan por revisar', async () => {
    await montar('/');
    const dias = [...contenedor.querySelectorAll('[aria-label="Días de la semana"] li')].map(
      (li) => li.querySelector('.sr-only')?.textContent ?? '',
    );
    expect(dias[3]).toMatch(/^jueves 15, hoy: \d+ registros, 3 por revisar$/);
    expect(dias[4]).toBe('viernes 16: todavía no llega');
  });

  it('el aviso de pendientes lleva a Revisar', async () => {
    await montar('/');
    await tocar(botonPor('3 por revisar'));
    expect(texto()).toContain('¿Está bien lo que leyó Huellita?');
  });

  it('el selector cambia la sala donde queda el registro', async () => {
    await montar('/');
    const selector = contenedor.querySelector<HTMLSelectElement>('#sala-registro');
    expect(selector).not.toBeNull();
    // La tía ve solo sus salas.
    expect([...selector!.options].map((o) => o.textContent)).toEqual([
      'Medio Menor A',
      'Medio Menor B',
    ]);
    await elegir(selector!, 'SALA-MMB');
    expect((await datos.salaActual()).id).toBe('SALA-MMB');
    expect(texto()).toContain('Inicio · Medio Menor B');
    expect(texto()).toContain('Ahora registras en Medio Menor B');
  });

  it('lo que se escribe queda en la sala elegida', async () => {
    await montar('/');
    await elegir(contenedor.querySelector<HTMLSelectElement>('#sala-registro')!, 'SALA-MMB');
    await tocar(botonPor('Escribir'));
    expect(texto()).toContain('Escribe lo que viste');
    await escribir(
      contenedor.querySelector<HTMLTextAreaElement>('#nota-texto')!,
      'Renata construye una torre de cuatro bloques estables.',
    );
    await tocar(botonPor('Enviar'));
    await act(async () => {
      await new Promise((listo) => setTimeout(listo, 30));
    });
    const deMMB = await datos.evidencias({ salaId: 'SALA-MMB' });
    expect(deMMB.some((e) => e.textoExtraido?.startsWith('Renata construye'))).toBe(true);
    expect(texto()).toContain('Listo, lo verás en Revisar');
  });

  it('una tía con una sola sala ve dónde queda el registro, sin selector', async () => {
    await datos.cambiarUsuaria('USR-ROSA');
    await montar('/');
    expect(contenedor.querySelector('#sala-registro')).toBeNull();
    expect(contenedor.querySelector('#titulo-registrar')?.textContent).toBe(
      'Registrar en Medio Menor A',
    );
  });

  it('Subir audio abre la hoja para elegir una nota de voz', async () => {
    await montar('/');
    await tocar(botonPor('Subir audio'));
    const dialogo = contenedor.querySelector('[role="dialog"]');
    expect(dialogo?.getAttribute('aria-label')).toBe('Subir un audio');
    expect(texto()).toContain('hasta 4 MB');
    const entrada = dialogo!.querySelector<HTMLInputElement>('input[type="file"]');
    expect(entrada?.accept).toContain('audio/*');
    expect(entrada?.accept).toContain('.m4a');
  });

  it('Subir foto deja sacar la foto o elegirla de la galería', async () => {
    await montar('/');
    await tocar(botonPor('Subir foto'));
    expect(texto()).toContain('Foto de tu nota');
    expect(texto()).toContain('Tomar foto');
    expect(texto()).toContain('Elegir de la galería');
    const entradas = [...contenedor.querySelectorAll<HTMLInputElement>('[role="dialog"] input')];
    // Una entrada abre la cámara directo y la otra deja elegir (sin `capture`).
    expect(entradas.map((e) => e.getAttribute('capture'))).toEqual([null, 'environment']);
  });
});

describe('Sala', () => {
  it('muestra la planilla con una fila por niño/a y su nivel en los 5 núcleos', async () => {
    await montar('/sala');
    expect(texto()).toContain('Planilla de la sala');
    expect(texto()).toContain('Medio Menor A');
    expect(texto()).toContain('Josefa');
    expect(texto()).toContain('Observados en 30 días');
    expect(contenedor.querySelectorAll('tbody tr')).toHaveLength(18);
    // Niño/a + 5 núcleos + último registro.
    const encabezados = [...contenedor.querySelectorAll('thead th')].map((th) =>
      (th.textContent ?? '').trim(),
    );
    expect(encabezados).toEqual(['Niño/a', 'MG', 'MF', 'LC', 'SE', 'CO', 'Último']);
    // Nunca fotos de niños ni niñas (solo el logo del encabezado).
    expect(imagenesSinLogo()).toHaveLength(0);
  });

  it('pinta cada número con el color de su nivel, sin depender solo del color', async () => {
    await montar('/sala');
    const chips = [...contenedor.querySelectorAll<HTMLElement>('tbody [data-nivel]')];
    expect(chips.length).toBeGreaterThan(50);
    const vistos = new Set<string>();
    for (const chip of chips) {
      const nivel = Number(chip.dataset.nivel) as Nivel;
      expect(chip.style.background).toBe(rgb(colorNivel(nivel)));
      expect(chip.textContent).toBe(String(nivel));
      vistos.add(chip.dataset.nivel!);
    }
    // En la sala hay varios niveles distintos, cada uno con su color.
    expect(vistos.size).toBeGreaterThan(2);
    // Y el lector de pantalla oye el nivel de cada celda.
    expect(texto()).toContain('Nivel 7, revisar avance');
  });

  it('filtra por revisar avance', async () => {
    await montar('/sala');
    await tocar(botonPor('Revisar avance'));
    expect(contenedor.querySelectorAll('tbody tr')).toHaveLength(1);
    expect(texto()).toContain('Josefa');
  });

  it('abre la leyenda de los colores con los 9 niveles', async () => {
    await montar('/sala');
    const ayuda = contenedor.querySelector<HTMLButtonElement>(
      '[aria-label="Qué significan los colores"]',
    );
    expect(ayuda).not.toBeNull();
    await tocar(ayuda!);
    const dialogo = contenedor.querySelector('[role="dialog"]')!;
    expect(dialogo.querySelectorAll('[data-nivel]')).toHaveLength(9);
    expect(texto()).toContain('Atención y regulación inicial');
    expect(texto()).toContain('Secuencias y autonomía creciente');
    expect(texto()).toContain('Más de 1 mes sin registro');
    expect(texto()).toContain('No mide cómo le va al niño o niña');
  });
});

describe('Revisar', () => {
  it('muestra las notas con su cita, certeza y acciones', async () => {
    await montar('/revisar');
    expect(texto()).toContain('¿Está bien lo que leyó Huellita?');
    expect(texto()).toContain('Huellita leyó');
    expect(texto()).toContain('Confianza');
    expect(texto()).toContain('Confirmar');
    expect(texto()).toContain('Corregir');
    expect(texto()).toContain('Descartar');
    // Nombre que no calzó exacto: queda lo que estaba escrito en la nota.
    expect(texto()).toContain('escrito “Agus”');
    expect(texto()).toContain('Baja');
    expect(texto()).toMatch(/N\.º \d{4}/);
    // Núcleos y niveles de la rúbrica del backend.
    expect(texto()).toContain('Motor grueso');
    expect(texto()).toContain('Secuencias y autonomía creciente');
  });

  it('Corregir ofrece los 9 niveles con las conductas del núcleo', async () => {
    await montar('/revisar');
    await tocar(botonPor('Corregir'));
    const opciones = contenedor.querySelectorAll('[role="dialog"] [role="radio"]');
    expect(opciones).toHaveLength(9);
    expect(opciones[8].textContent).toContain('Secuencias y autonomía creciente');
  });

  it('al guardar una nota, sale de la lista y avisa', async () => {
    await montar('/revisar');
    const antes = (await datos.sugerencias({ estado: ['pendiente'] })).length;
    await tocar(botonPor('Confirmar'));
    await esperarSalida();
    const despues = (await datos.sugerencias({ estado: ['pendiente'] })).length;
    expect(despues).toBe(antes - 1);
    expect(texto()).toContain('Guardado en la ficha de');
    expect(texto()).toContain('Deshacer');
  });

  it('acepta todas las seguras de una vez', async () => {
    await montar('/revisar');
    await tocar(botonPor('Confirmar los de confianza alta'));
    await esperarSalida();
    const pendientes = await datos.sugerencias({ estado: ['pendiente'] });
    expect(pendientes.every((s) => s.certeza !== 'alta' || s.tipo === 'nota_sala')).toBe(true);
    expect(texto()).toContain('Deshacer');
  });
});

describe('Ficha', () => {
  it('muestra el resumen, los 5 núcleos, qué observar y los registros', async () => {
    await montar('/nino/NINO-00001');
    expect(texto()).toContain('Josefa');
    expect(texto()).toContain('Para observar esta semana');
    expect(texto()).toContain('Conviene acompañar de cerca Lenguaje y comunicación');
    expect(texto()).toContain('Cómo va · por núcleo');
    expect(texto()).toContain('Motor grueso');
    expect(texto()).toContain('Sin registros aún');
    expect(texto()).toContain('Cognitivo');
    expect(texto()).toContain('revisar avance (esperado 9)');
    expect(texto()).toContain('Registros');
    expect(texto()).toContain('Registrar para Josefa');
    const nucleos = contenedor.querySelectorAll('[aria-label="Nivel por núcleo"] li');
    expect(nucleos).toHaveLength(5);
  });

  it('abre el detalle de un núcleo con el nivel actual y el siguiente', async () => {
    await montar('/nino/NINO-00001');
    await tocar(botonPor('Lenguaje y comunicación'));
    expect(texto()).toContain('Ahora: Representación y combinación inicial');
    expect(texto()).toContain('Siguiente: Combinación y participación');
  });
});

describe('Directora', () => {
  beforeEach(async () => {
    await datos.cambiarUsuaria('USR-CARMEN');
  });

  it('muestra una tarjeta por sala con los observados de 30 días', async () => {
    await montar('/directora');
    expect(texto()).toContain('Salas del jardín');
    expect(texto()).toContain('Medio Menor A');
    expect(texto()).toContain('Medio Menor B');
    expect(texto()).toContain('Sala Cuna Mayor');
    expect(texto()).toContain('16 de 18 observados en 30 días');
    expect(texto()).toContain('1 por revisar avance');
    expect(texto()).toContain('Menos registrado: Motor grueso');
    // Nunca fotos de niños ni niñas (solo el logo del encabezado).
    expect(imagenesSinLogo()).toHaveLength(0);
  });

  it('abre una sala en modo lectura, sin captura ni pila de pendientes', async () => {
    await montar('/directora/sala/SALA-MMA');
    expect(texto()).toContain('Vista de la directora · solo lectura');
    expect(texto()).toContain('Medio Menor A');
    expect(contenedor.querySelector('[aria-label="Registrar"]')).toBeNull();
    expect(contenedor.querySelectorAll('tbody tr')).toHaveLength(18);
    // La misma planilla, con los colores de nivel.
    expect(contenedor.querySelectorAll('tbody [data-nivel]').length).toBeGreaterThan(50);
  });

  it('mueve de sala a un niño/a con confirmación', async () => {
    await montar('/directora/sala/SALA-MMA');
    await tocar(botonPor('Josefa'));
    expect(texto()).toContain('Ver su ficha');
    await tocar(botonPor('Mover de sala'));
    expect(texto()).toContain('Nueva sala');
    await tocar(botonPor('Mover'));
    expect((await datos.nino('NINO-00001')).salaId).toBe('SALA-MMB');
    expect(texto()).toContain('ahora está en Medio Menor B');
  });

  it('da de baja a un niño/a solo después de confirmar', async () => {
    await montar('/directora/sala/SALA-MMA');
    await tocar(botonPor('Josefa'));
    await tocar(botonPor('Dar de baja'));
    expect(texto()).toContain('¿Dar de baja a Josefa?');
    // Mientras no confirme, nada cambia.
    expect((await datos.nino('NINO-00001')).activo).toBe(true);
    await tocar(botonPor('Sí, dar de baja'));
    expect((await datos.nino('NINO-00001')).activo).toBe(false);
  });

  it('en Inicio puede registrar en cualquiera de las salas del jardín', async () => {
    await montar('/');
    const selector = contenedor.querySelector<HTMLSelectElement>('#sala-registro')!;
    expect(selector.options).toHaveLength(3);
  });
});

describe('Acceso por rol', () => {
  it('una tía no entra a la vista directora', async () => {
    await montar('/directora');
    // Redirige a su inicio.
    expect(texto()).toContain('Inicio · Medio Menor A');
    expect(texto()).not.toContain('Salas del jardín');
  });

  it('la barra inferior solo muestra Directora a la directora', async () => {
    await montar('/');
    expect(contenedor.querySelector('a[href="/directora"]')).toBeNull();
    await datos.cambiarUsuaria('USR-CARMEN');
    await montar('/');
    expect(contenedor.querySelector('a[href="/directora"]')).not.toBeNull();
  });

  it('la navegación dice Inicio, ya no Agenda', async () => {
    await montar('/');
    const destinos = [...contenedor.querySelectorAll('nav[aria-label="Principal"] a')].map((a) =>
      (a.textContent ?? '').trim(),
    );
    expect(destinos[0]).toBe('Inicio');
    expect(destinos.some((d) => d.startsWith('Agenda'))).toBe(false);
  });
});
