// @vitest-environment jsdom
/**
 * Prueba de humo de las pantallas: se montan con un `DataServiceLocal` en
 * memoria (sin tocar `localStorage` del navegador) y una IA sin latencia, para
 * comprobar que Mi sala, Revisar y la ficha se dibujan y que validar una nota
 * la saca de Revisar.
 */
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { almacenMemoria, DataServiceLocal } from '../services/datos';
import { IAServiceSimulado } from '../services/ia';
import { Rutas } from './App';
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

function botonPor(nombre: string): HTMLButtonElement {
  const botones = [...contenedor.querySelectorAll('button')];
  const encontrado = botones.find((b) => (b.textContent ?? '').includes(nombre));
  if (!encontrado) throw new Error(`No hay botón con el texto "${nombre}"`);
  return encontrado as HTMLButtonElement;
}

async function tocar(elemento: HTMLElement) {
  await act(async () => {
    elemento.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
}

/** Deja pasar la transición de salida de una nota resuelta (160 ms). */
async function esperarSalida() {
  await act(async () => {
    await new Promise((listo) => setTimeout(listo, 220));
  });
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

describe('Mi sala', () => {
  it('muestra la sala, la pila de pendientes, la grilla y el resumen', async () => {
    await montar('/');
    expect(texto()).toContain('Medio Menor A');
    expect(texto()).toContain('notas por revisar');
    expect(texto()).toContain('Huellita ya las ordenó');
    expect(texto()).toContain('Josefa');
    expect(texto()).toContain('Observados este mes');
    // 18 niños/as activos de la sala, con avatar de iniciales y sin fotos.
    expect(contenedor.querySelectorAll('.grid-cols-3 > button')).toHaveLength(18);
    expect(contenedor.querySelectorAll('img')).toHaveLength(0);
  });

  it('filtra por revisar avance', async () => {
    await montar('/');
    await tocar(botonPor('Revisar avance'));
    expect(contenedor.querySelectorAll('.grid-cols-3 > button')).toHaveLength(1);
    expect(texto()).toContain('Josefa');
  });

  it('abre la leyenda del semáforo', async () => {
    await montar('/');
    const ayuda = contenedor.querySelector<HTMLButtonElement>(
      '[aria-label="Qué significan los colores"]',
    );
    expect(ayuda).not.toBeNull();
    await tocar(ayuda!);
    expect(texto()).toContain('Más de 1 mes sin registro');
    expect(texto()).toContain('No mide cómo le va al niño o niña');
  });
});

describe('Revisar', () => {
  it('muestra las notas con su cita, certeza y acciones', async () => {
    await montar('/revisar');
    expect(texto()).toContain('Confirma lo que Huellita leyó de tus notas.');
    expect(texto()).toContain('Segura');
    expect(texto()).toContain('Guardar');
    expect(texto()).toContain('Cambiar');
    // Nombre que no calzó exacto: queda con la cita de lo que decía la nota.
    expect(texto()).toContain('decía');
    expect(texto()).toContain('Poco segura');
    expect(contenedor.querySelectorAll('.postit').length).toBeGreaterThan(0);
  });

  it('al guardar una nota, sale de la lista y avisa', async () => {
    await montar('/revisar');
    const antes = (await datos.sugerencias({ estado: ['pendiente'] })).length;
    await tocar(botonPor('Guardar'));
    await esperarSalida();
    const despues = (await datos.sugerencias({ estado: ['pendiente'] })).length;
    expect(despues).toBe(antes - 1);
    expect(texto()).toContain('Guardado en la ficha de');
    expect(texto()).toContain('Deshacer');
  });

  it('acepta todas las seguras de una vez', async () => {
    await montar('/revisar');
    await tocar(botonPor('Aceptar las seguras'));
    await esperarSalida();
    const pendientes = await datos.sugerencias({ estado: ['pendiente'] });
    expect(pendientes.every((s) => s.certeza !== 'alta' || s.tipo === 'nota_sala')).toBe(true);
    expect(texto()).toContain('Deshacer');
  });
});

describe('Ficha', () => {
  it('muestra el resumen, los núcleos, qué observar y los registros', async () => {
    await montar('/nino/NINO-00001');
    expect(texto()).toContain('Josefa');
    expect(texto()).toContain('Para observar esta semana');
    expect(texto()).toContain('Cómo va');
    expect(texto()).toContain('Registros');
    expect(texto()).toContain('Registrar para Josefa');
    // 4 núcleos visibles y el botón para ver los 8.
    await tocar(botonPor('Ver los 8'));
    expect(texto()).toContain('Pensamiento Matemático');
  });

  it('abre el detalle de un núcleo con el nivel actual y el siguiente', async () => {
    await montar('/nino/NINO-00001');
    await tocar(botonPor('Lenguaje Verbal'));
    expect(texto()).toContain('Ahora:');
    expect(texto()).toContain('Siguiente:');
  });
});

describe('Directora', () => {
  beforeEach(async () => {
    await datos.cambiarUsuaria('USR-CARMEN');
  });

  it('muestra una tarjeta por sala con los observados de 30 días', async () => {
    await montar('/directora');
    expect(texto()).toContain('Salas');
    expect(texto()).toContain('Medio Menor A');
    expect(texto()).toContain('Medio Menor B');
    expect(texto()).toContain('Sala Cuna Mayor');
    expect(texto()).toContain('16 de 18 observados en 30 días');
    expect(texto()).toContain('1 por revisar avance');
    expect(texto()).toContain('Menos registrado:');
    // Nunca fotos de niños ni niñas.
    expect(contenedor.querySelectorAll('img')).toHaveLength(0);
  });

  it('abre una sala en modo lectura, sin captura ni pila de pendientes', async () => {
    await montar('/directora/sala/SALA-MMA');
    expect(texto()).toContain('Vista de la directora · solo lectura');
    expect(texto()).toContain('Medio Menor A');
    expect(texto()).not.toContain('notas por revisar');
    expect(contenedor.querySelector('[aria-label="Registrar"]')).toBeNull();
    expect(contenedor.querySelectorAll('.grid-cols-3 > button')).toHaveLength(18);
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
});

describe('Acceso por rol', () => {
  it('una tía no entra a la vista directora', async () => {
    await montar('/directora');
    // Redirige a Mi sala.
    expect(texto()).toContain('Medio Menor A');
    expect(texto()).not.toContain('Salas del jardín');
    expect(texto()).toContain('notas por revisar');
  });

  it('la barra inferior solo muestra Directora a la directora', async () => {
    await montar('/');
    expect(contenedor.querySelector('a[href="/directora"]')).toBeNull();
    await datos.cambiarUsuaria('USR-CARMEN');
    await montar('/');
    expect(contenedor.querySelector('a[href="/directora"]')).not.toBeNull();
  });
});
