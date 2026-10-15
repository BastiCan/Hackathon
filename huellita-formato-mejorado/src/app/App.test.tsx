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
import semillaJson from '@data/semilla.json';
import type { Semilla } from '../lib/tipos';
import { almacenMemoria, DataServiceLocal } from '../services/datos';
import { IAServiceSimulado } from '../services/ia';
import { Rutas } from './App';
import { ALT_LOGO } from './Encabezado';
import { ProveedorOpciones } from './opciones';
import { ProveedorServicios } from './servicios';

// React 18 pide esta marca para que `act` no avise en cada render.
(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let contenedor: HTMLDivElement;
let raiz: Root;
let datos: DataServiceLocal;

/**
 * Monta la versión con agenda. Se declara con `ProveedorOpciones` en vez de confiar en
 * `CONFIG`: así estas pruebas dan igual aunque el entorno traiga `VITE_AGENDA=false`
 * (la versión AWS tiene las suyas en `version-aws.test.tsx`).
 */
async function montar(ruta: string) {
  await act(async () => {
    raiz.render(
      <ProveedorServicios datos={datos} ia={new IAServiceSimulado({ latenciaMs: 0 })}>
        <ProveedorOpciones agenda>
          <MemoryRouter initialEntries={[ruta]}>
            <Rutas />
          </MemoryRouter>
        </ProveedorOpciones>
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

/** Deja pasar la transición de salida de una nota resuelta (160 ms). */
async function esperarSalida() {
  await act(async () => {
    await new Promise((listo) => setTimeout(listo, 220));
  });
}

/**
 * La semilla con dos registros bajos seguidos de Pedro en Lenguaje y
 * comunicación (nivel 7 con 30 y 31 meses, cuando lo esperado es 9): así se
 * puede probar la bandera "revisar avance", que el historial del dataset no trae.
 */
function semillaConRevisarAvance(): Semilla {
  const base = JSON.parse(JSON.stringify(semillaJson)) as Semilla;
  const registros = [
    { id: 'EVI-T0001', fecha: '2026-09-28T10:00:00-03:00' },
    { id: 'EVI-T0002', fecha: '2026-10-08T10:00:00-03:00' },
  ];
  for (const r of registros) {
    base.evidencias.push({
      id: r.id,
      salaId: 'SG-A',
      autorId: 'EDU-0001',
      creadaEn: r.fecha,
      formato: 'texto',
      textoExtraido: 'Pedro pidió agua con una sola palabra.',
      estado: 'lista',
    });
    base.sugerencias.push({
      id: `SUG-${r.id}`,
      evidenciaId: r.id,
      salaId: 'SG-A',
      tipo: 'evaluacion',
      ninoId: 'NINO-00253',
      nucleo: 'lenguaje_comunicacion',
      nivel: 7,
      cita: 'Pedro pidió agua con una sola palabra.',
      certeza: 'alta',
      estado: 'aceptada',
      validadaPor: 'EDU-0001',
      validadaEn: r.fecha,
    });
  }
  return base;
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
});

describe('Agenda', () => {
  it('muestra el encabezado oficial, la semana, el aviso y la jornada', async () => {
    await montar('/');
    // El encabezado lleva el logo oficial Mineduc + Integra, no un sello dibujado.
    const logo = contenedor.querySelector(`header img[alt="${ALT_LOGO}"]`);
    expect(logo).not.toBeNull();
    expect(logo!.getAttribute('src')).toBeTruthy();
    expect(texto()).toContain('Agenda · Sala A');
    expect(texto()).toContain('Jueves 15 de octubre');
    expect(texto()).toContain('por revisar');
    expect(texto()).toContain('registro IEA (noviembre)');
    expect(texto()).toContain('Experiencia de aprendizaje');
    expect(contenedor.querySelectorAll('[aria-label="Días de la semana"] button')).toHaveLength(5);
    // La foto real del post-it de las tortugas aparece en la agenda de hoy.
    expect(contenedor.querySelectorAll('img[alt="Foto de la nota"]').length).toBeGreaterThan(0);
  });

  it('cambia de día con la semana', async () => {
    await montar('/');
    const lunes = contenedor.querySelector<HTMLButtonElement>('[aria-label^="lun 12"]');
    expect(lunes).not.toBeNull();
    await tocar(lunes!);
    expect(texto()).toContain('Lunes 12 de octubre');
    expect(texto()).toContain('Volver a hoy');
  });

  it('un día que aún no llega lo dice, sin inventar registros', async () => {
    await montar('/');
    await tocar(contenedor.querySelector<HTMLButtonElement>('[aria-label^="vie 16"]')!);
    expect(texto()).toContain('Ese día todavía no llega.');
  });
});

describe('Sala', () => {
  it('muestra la planilla con una fila por niño/a y su nivel por núcleo', async () => {
    await montar('/sala');
    expect(texto()).toContain('Planilla de la sala');
    expect(texto()).toContain('Sala A');
    expect(texto()).toContain('Josefa');
    expect(texto()).toContain('Martina M.');
    expect(texto()).toContain('Observados en 30 días');
    expect(contenedor.querySelectorAll('tbody tr')).toHaveLength(13);
    // Una columna por núcleo (los 5 dominios), más el nombre y el último registro.
    const encabezados = [...contenedor.querySelectorAll('thead th')].map((th) => th.textContent);
    expect(encabezados).toEqual(['Niño/a', 'MG', 'MF', 'LC', 'SE', 'CO', 'Último']);
    // Nunca fotos de niños ni niñas (solo el logo del encabezado).
    expect(imagenesSinLogo()).toHaveLength(0);
  });

  it('el filtro revisar avance queda vacío con el historial del dataset', async () => {
    await montar('/sala');
    await tocar(botonPor('Revisar avance'));
    expect(contenedor.querySelectorAll('tbody tr')).toHaveLength(0);
    expect(texto()).toContain('Ninguno en este filtro.');
  });

  it('filtra por revisar avance', async () => {
    datos = new DataServiceLocal({ semilla: semillaConRevisarAvance(), almacen: almacenMemoria() });
    await datos.cambiarUsuaria('EDU-0001');
    await montar('/sala');
    await tocar(botonPor('Revisar avance'));
    expect(contenedor.querySelectorAll('tbody tr')).toHaveLength(1);
    expect(texto()).toContain('Pedro');
  });

  it('abre la leyenda de los colores', async () => {
    await montar('/sala');
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
    expect(texto()).toContain('¿Está bien lo que leyó Huellita?');
    expect(texto()).toContain('Huellita leyó');
    expect(texto()).toContain('Confianza');
    expect(texto()).toContain('Confirmar');
    expect(texto()).toContain('Corregir');
    expect(texto()).toContain('Descartar');
    // Nombre que no calzó exacto: queda lo que estaba escrito en la nota.
    expect(texto()).toContain('escrito “Naya”');
    expect(texto()).toContain('Baja');
    expect(texto()).toMatch(/N\.º \d{4}/);
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
  it('muestra el resumen, los núcleos, qué observar y los registros', async () => {
    await montar('/nino/NINO-00008');
    expect(texto()).toContain('Josefa');
    expect(texto()).toContain('Para observar esta semana');
    // Lenguaje y comunicación es su núcleo con el registro más antiguo.
    expect(texto()).toContain('Conviene observar más Lenguaje y comunicación');
    expect(texto()).toContain('Cómo va · por ámbito');
    expect(texto()).toContain('Desarrollo personal y social');
    expect(texto()).toContain('Comunicación integral');
    expect(texto()).toContain('Cognitivo');
    expect(texto()).toContain('Registros');
    expect(texto()).toContain('Registrar para Josefa');
  });

  it('marca revisar avance con el nivel esperado para su edad', async () => {
    datos = new DataServiceLocal({ semilla: semillaConRevisarAvance(), almacen: almacenMemoria() });
    await datos.cambiarUsuaria('EDU-0001');
    await montar('/nino/NINO-00253');
    expect(texto()).toContain('Conviene acompañar de cerca Lenguaje y comunicación');
    expect(texto()).toContain('revisar avance (esperado 9)');
  });

  it('abre el detalle de un núcleo con el nivel actual y el siguiente', async () => {
    await montar('/nino/NINO-00008');
    await tocar(botonPor('Lenguaje y comunicación'));
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
    expect(texto()).toContain('Salas del jardín');
    expect(texto()).toContain('Sala A');
    expect(texto()).toContain('Sala B');
    expect(texto()).toContain('2 de 13 observados en 30 días');
    expect(texto()).toContain('Ninguno por revisar');
    expect(texto()).toContain('Menos registrado:');
    // Nunca fotos de niños ni niñas (solo el logo del encabezado).
    expect(imagenesSinLogo()).toHaveLength(0);
  });

  it('abre una sala en modo lectura, sin captura ni pila de pendientes', async () => {
    await montar('/directora/sala/SG-A');
    expect(texto()).toContain('Vista de la directora · solo lectura');
    expect(texto()).toContain('Sala A');
    expect(contenedor.querySelector('[aria-label="Registrar"]')).toBeNull();
    expect(contenedor.querySelectorAll('tbody tr')).toHaveLength(13);
  });

  it('mueve de sala a un niño/a con confirmación', async () => {
    await montar('/directora/sala/SG-A');
    await tocar(botonPor('Josefa'));
    expect(texto()).toContain('Ver su ficha');
    await tocar(botonPor('Mover de sala'));
    expect(texto()).toContain('Nueva sala');
    await tocar(botonPor('Mover'));
    expect((await datos.nino('NINO-00008')).salaId).toBe('SG-B');
    expect(texto()).toContain('ahora está en Sala B');
  });

  it('da de baja a un niño/a solo después de confirmar', async () => {
    await montar('/directora/sala/SG-A');
    await tocar(botonPor('Josefa'));
    await tocar(botonPor('Dar de baja'));
    expect(texto()).toContain('¿Dar de baja a Josefa?');
    // Mientras no confirme, nada cambia.
    expect((await datos.nino('NINO-00008')).activo).toBe(true);
    await tocar(botonPor('Sí, dar de baja'));
    expect((await datos.nino('NINO-00008')).activo).toBe(false);
  });
});

describe('Acceso por rol', () => {
  it('una tía no entra a la vista directora', async () => {
    await montar('/directora');
    // Redirige a su agenda.
    expect(texto()).toContain('Agenda · Sala A');
    expect(texto()).not.toContain('Salas del jardín');
  });

  it('la barra inferior solo muestra Directora a la directora', async () => {
    await montar('/');
    expect(contenedor.querySelector('a[href="/directora"]')).toBeNull();
    await datos.cambiarUsuaria('USR-CARMEN');
    await montar('/');
    expect(contenedor.querySelector('a[href="/directora"]')).not.toBeNull();
  });
});
