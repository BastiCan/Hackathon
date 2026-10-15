/**
 * Revisión de privacidad de la Fase 1 (tarea 12). Deja fijas, como pruebas, las
 * reglas de `.kiro/steering/privacidad.md` que se pueden comprobar en el código:
 *
 * - no hay `console.*` con datos de niños/as (no hay `console.*` en absoluto);
 * - en las URLs solo viajan IDs, nunca nombres;
 * - a la IA solo se le pasa ID, nombre de pila y niveles ya calculados;
 * - las fotos y audios no se guardan: quedan en memoria y se borran al procesar;
 * - los datos de prueba no traen RUT ni apellidos completos.
 */
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath, URL } from 'node:url';
import { describe, expect, it } from 'vitest';
import semillaJson from '@data/semilla.json';
import type { Semilla } from '../lib/tipos';
import { capturar } from './captura';
import { almacenMemoria, CLAVE_ALMACEN, DataServiceLocal, type Almacen } from './datos';
import type { ContextoIA, IAService } from './ia';

const RAIZ_SRC = fileURLToPath(new URL('..', import.meta.url));

function archivosFuente(carpeta: string): string[] {
  return readdirSync(carpeta).flatMap((nombre) => {
    const ruta = join(carpeta, nombre);
    if (statSync(ruta).isDirectory()) return archivosFuente(ruta);
    const esFuente = /\.tsx?$/.test(nombre) && !/\.test\.tsx?$/.test(nombre);
    return esFuente ? [ruta] : [];
  });
}

const fuentes = archivosFuente(RAIZ_SRC).map((ruta) => ({
  ruta: ruta.slice(RAIZ_SRC.length).replace(/\\/g, '/'),
  texto: readFileSync(ruta, 'utf8'),
}));

describe('código', () => {
  it('no usa console en ninguna parte', () => {
    const conConsole = fuentes.filter((f) => /\bconsole\s*\./.test(f.texto));
    expect(conConsole.map((f) => f.ruta)).toEqual([]);
  });

  it('no pone datos de niños en la URL', () => {
    const conDatos = fuentes.filter((f) => /[?&](nino|nombre|name|edad)=/.test(f.texto));
    expect(conDatos.map((f) => f.ruta)).toEqual([]);
  });

  it('no hay rastros de reconocimiento facial', () => {
    const prohibidas = /(IndexFaces|SearchFaces|CompareFaces|faceId)/i;
    expect(fuentes.filter((f) => prohibidas.test(f.texto)).map((f) => f.ruta)).toEqual([]);
  });
});

describe('datos de prueba', () => {
  const semilla = semillaJson as unknown as Semilla;

  it('no traen RUT ni apellidos completos', () => {
    const crudo = JSON.stringify(semilla);
    expect(/\brut\b/i.test(crudo)).toBe(false);
    // De cada niño/a solo se guarda la inicial del apellido ("M.").
    expect(semilla.ninos.every((n) => /^[A-ZÁÉÍÓÚÑ]\.$/.test(n.apellidoInicial))).toBe(true);
  });

  it('identifican a cada niño/a con un ID seudónimo', () => {
    expect(semilla.ninos.every((n) => /^NINO-\d{5}$/.test(n.id))).toBe(true);
  });
});

/** IA de prueba que guarda el contexto que recibió. */
class IAEspia implements IAService {
  contexto: ContextoIA | null = null;
  archivo: Blob | undefined;

  async procesar(_evidencia: never, archivo: Blob | undefined, contexto: ContextoIA) {
    this.contexto = contexto;
    this.archivo = archivo;
    return [];
  }
}

async function servicios(): Promise<{ datos: DataServiceLocal; ia: IAEspia; almacen: Almacen }> {
  const almacen = almacenMemoria();
  const datos = new DataServiceLocal({ almacen });
  await datos.cambiarUsuaria('USR-ANA');
  return { datos, ia: new IAEspia(), almacen };
}

describe('lo que recibe la IA', () => {
  it('solo lleva ID, nombre de pila y niveles ya calculados', async () => {
    const { datos, ia } = await servicios();
    const { procesada } = await capturar('texto', undefined, 'Josefa ordenó los individuales.', undefined, {
      datos,
      ia: ia as unknown as IAService,
    });
    await procesada;

    expect(ia.contexto).not.toBeNull();
    const claves = new Set(ia.contexto!.ninos.flatMap((n) => Object.keys(n)));
    expect([...claves].sort()).toEqual(['id', 'nivelEsperado', 'nivelesActuales', 'nombre']);
    const crudo = JSON.stringify(ia.contexto);
    expect(crudo).not.toContain('fechaNacimiento');
    expect(crudo).not.toContain('apellido');
  });
});

describe('fotos y audios', () => {
  it('no se guardan: viajan en memoria y la evidencia solo conserva el texto', async () => {
    const { datos, ia, almacen } = await servicios();
    const foto = new Blob(['datos-binarios-de-la-foto'], { type: 'image/jpeg' });
    const { evidencia, procesada } = await capturar('foto', foto, undefined, undefined, {
      datos,
      ia: ia as unknown as IAService,
    });
    await procesada;

    // La IA sí recibe el archivo (en la Fase 3 lo lee Bedrock), pero el
    // almacenamiento local nunca lo ve.
    expect(ia.archivo).toBe(foto);
    const guardado = almacen.leer(CLAVE_ALMACEN) ?? '';
    expect(guardado).not.toContain('datos-binarios-de-la-foto');
    expect(guardado).not.toContain('blob:');
    const guardadas = await datos.evidencias({ ids: [evidencia.id] });
    expect(Object.keys(guardadas[0])).not.toContain('archivo');
  });
});
