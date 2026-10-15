import { describe, expect, it } from 'vitest';
import semillaJson from '@data/semilla.json';
import { almacenMemoria, CLAVE_ALMACEN, DataServiceLocal } from './datos';
import { IAServiceSimulado } from './ia';
import { capturar } from './captura';
import type { Semilla } from '../lib/tipos';

const semilla = semillaJson as unknown as Semilla;

function servicios() {
  const almacen = almacenMemoria();
  const datos = new DataServiceLocal({ semilla, almacen });
  const ia = new IAServiceSimulado({ guiones: semilla.demoCapturas, latenciaMs: 0 });
  return { almacen, datos, ia };
}

describe('DataServiceLocal', () => {
  it('parte de la semilla con la primera tía y su sala', async () => {
    const { datos } = servicios();
    expect((await datos.sesion()).id).toBe('EDU-0001');
    expect((await datos.salaActual()).id).toBe('SG-A');
    expect(datos.hoy()).toBe(semilla.fechaDemo);
    expect(await datos.ninos('SG-A')).toHaveLength(13);
  });

  it('una tía ve solo sus salas y la directora, todo el jardín', async () => {
    const { datos } = servicios();
    expect((await datos.salas()).map((s) => s.id)).toEqual(['SG-A']);
    await datos.cambiarUsuaria('USR-CARMEN');
    expect(await datos.salas()).toHaveLength(2);
  });

  it('guarda en localStorage con la clave huellita:v1 y recupera el estado', async () => {
    const { almacen, datos } = servicios();
    await datos.cambiarUsuaria('EDU-0002');
    expect(almacen.leer(CLAVE_ALMACEN)).not.toBeNull();

    const otro = new DataServiceLocal({ semilla, almacen });
    expect((await otro.sesion()).id).toBe('EDU-0002');
    expect((await otro.salaActual()).id).toBe('SG-B');
  });

  it('descarta lo guardado con una semilla anterior (la de 8 núcleos)', async () => {
    const almacen = almacenMemoria();
    almacen.escribir(
      CLAVE_ALMACEN,
      JSON.stringify({ version: 1, usuariaId: 'USR-ROSA', usuariaElegida: true, salaId: 'SALA-MMA', sugerencias: [] }),
    );
    const datos = new DataServiceLocal({ semilla, almacen });
    expect((await datos.sesion()).id).toBe('EDU-0001');
    expect(await datos.usuariaElegida()).toBe(false);
    expect(await datos.sugerencias({})).toHaveLength(semilla.sugerencias.length);
  });

  it('validar deja la evaluación con autor y fecha; cambiar guarda el original', async () => {
    const { datos } = servicios();
    const [pendiente] = await datos.sugerencias({ estado: ['pendiente'] });

    await datos.validar(pendiente.id);
    const aceptada = (await datos.sugerencias({ estado: ['aceptada'] })).find(
      (s) => s.id === pendiente.id,
    );
    expect(aceptada?.validadaPor).toBe('EDU-0001');
    expect(aceptada?.validadaEn).toContain(semilla.fechaDemo);

    const [otra] = await datos.sugerencias({ estado: ['pendiente'] });
    await datos.validar(otra.id, { nivel: 5 });
    const cambiada = (await datos.sugerencias({ estado: ['cambiada'] })).find(
      (s) => s.id === otra.id,
    );
    expect(cambiada?.nivel).toBe(5);
    expect(cambiada?.original?.nivel).toBe(otra.nivel);
  });

  it('descartar no deja la sugerencia como validada', async () => {
    const { datos } = servicios();
    const [pendiente] = await datos.sugerencias({ estado: ['pendiente'] });
    await datos.descartar(pendiente.id);
    const descartadas = await datos.sugerencias({ estado: ['descartada'] });
    expect(descartadas.map((s) => s.id)).toContain(pendiente.id);
  });

  it('avisa a los suscriptores y reinicia la demo', async () => {
    const { datos } = servicios();
    let avisos = 0;
    const baja = datos.suscribir(() => void (avisos += 1));

    const [pendiente] = await datos.sugerencias({ estado: ['pendiente'] });
    await datos.validar(pendiente.id);
    expect(avisos).toBe(1);

    await datos.reiniciarDemo();
    expect((await datos.sugerencias({ estado: ['pendiente'] })).length).toBe(
      semilla.sugerencias.filter((s) => s.estado === 'pendiente').length,
    );

    baja();
    await datos.descartar(pendiente.id);
    expect(avisos).toBe(2); // el reinicio avisó; después de la baja, no
  });

  it('dar de baja saca al niño/a de la sala sin borrar su historial', async () => {
    const { datos } = servicios();
    await datos.darDeBaja('NINO-00008');
    const ninos = await datos.ninos('SG-A');
    expect(ninos.map((n) => n.id)).not.toContain('NINO-00008');
    expect((await datos.sugerencias({ ninoId: 'NINO-00008' })).length).toBeGreaterThan(0);
  });

  it('recuerda la usuaria elegida y la olvida al reiniciar la demo', async () => {
    const { datos } = servicios();
    expect(await datos.usuariaElegida()).toBe(false);
    await datos.cambiarUsuaria('EDU-0002');
    expect(await datos.usuariaElegida()).toBe(true);
    await datos.reiniciarDemo();
    expect(await datos.usuariaElegida()).toBe(false);
  });

  it('el catálogo de salas del jardín trae las 2 salas, sin datos de niños', async () => {
    const { datos } = servicios();
    const salas = await datos.salasDelJardin();
    expect(salas.map((s) => s.nombre)).toEqual(['Sala A', 'Sala B']);
  });
});

describe('evidencias nuevas', () => {
  it('se guardan con el día de la demo y la hora real, y quedan al final (orden de llegada)', async () => {
    const { datos } = servicios();
    const nueva = await datos.guardarEvidencia({ salaId: 'SG-A', autorId: 'EDU-0001', formato: 'texto' });
    expect(nueva.creadaEn.slice(0, 10)).toBe(semilla.fechaDemo);
    const todas = await datos.evidencias({ salaId: 'SG-A' });
    expect(todas[todas.length - 1].id).toBe(nueva.id);
  });
});

describe('capturar', () => {
  it('devuelve de inmediato una evidencia en proceso y deja las sugerencias pendientes', async () => {
    const { datos, ia } = servicios();
    const antes = (await datos.sugerencias({ estado: ['pendiente'] })).length;

    const { evidencia, procesada } = await capturar('texto', undefined, 'Pascal cuenta objetos hasta 10.', undefined, { datos, ia });
    expect(evidencia.estado).toBe('procesando');
    expect(evidencia.autorId).toBe('EDU-0001');
    expect(evidencia.salaId).toBe('SG-A');

    const sugerencias = await procesada;
    expect(sugerencias).toHaveLength(1);
    expect(sugerencias[0].estado).toBe('pendiente');

    const despues = await datos.sugerencias({ estado: ['pendiente'] });
    expect(despues.length).toBe(antes + 1);
    const [guardada] = await datos.evidencias({ ids: [evidencia.id] });
    expect(guardada.estado).toBe('lista');
  });

  it('si la captura viene de una ficha, asocia a ese niño/a', async () => {
    const { datos, ia } = servicios();
    const { procesada } = await capturar(
      'texto',
      undefined,
      'Fernanda cuenta objetos hasta 10.',
      'NINO-00051',
      { datos, ia },
    );
    const sugerencias = await procesada;
    expect(sugerencias[0].ninoId).toBe('NINO-00051');
  });

  it('el nivel propuesto usa el nivel actual del núcleo del niño/a', async () => {
    const { datos, ia } = servicios();
    const { procesada } = await capturar(
      'texto',
      undefined,
      'Josefa combina dos palabras para pedir agua.',
      undefined,
      { datos, ia },
    );
    const [sug] = await procesada;
    expect(sug.ninoId).toBe('NINO-00008');
    expect(sug.nucleo).toBe('lenguaje_comunicacion');
    expect(sug.nivel).toBe(4); // nivel actual de Josefa en Lenguaje y comunicación
  });
});
