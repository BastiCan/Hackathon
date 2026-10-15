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
    expect((await datos.sesion()).id).toBe('USR-ANA');
    expect((await datos.salaActual()).id).toBe('SALA-MMA');
    expect(datos.hoy()).toBe(semilla.fechaDemo);
    expect(await datos.ninos('SALA-MMA')).toHaveLength(18);
  });

  it('una tía ve solo sus salas y la directora, todo el jardín', async () => {
    const { datos } = servicios();
    expect((await datos.salas()).map((s) => s.id)).toEqual(['SALA-MMA']);
    await datos.cambiarUsuaria('USR-CARMEN');
    expect((await datos.salas())).toHaveLength(3);
  });

  it('guarda en localStorage con la clave huellita:v1 y recupera el estado', async () => {
    const { almacen, datos } = servicios();
    await datos.cambiarUsuaria('USR-ROSA');
    expect(almacen.leer(CLAVE_ALMACEN)).not.toBeNull();

    const otro = new DataServiceLocal({ semilla, almacen });
    expect((await otro.sesion()).id).toBe('USR-ROSA');
  });

  it('validar deja la evaluación con autor y fecha; cambiar guarda el original', async () => {
    const { datos } = servicios();
    const [pendiente] = await datos.sugerencias({ estado: ['pendiente'] });

    await datos.validar(pendiente.id);
    const aceptada = (await datos.sugerencias({ estado: ['aceptada'] })).find(
      (s) => s.id === pendiente.id,
    );
    expect(aceptada?.validadaPor).toBe('USR-ANA');
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
    await datos.darDeBaja('NINO-00001');
    const ninos = await datos.ninos('SALA-MMA');
    expect(ninos.map((n) => n.id)).not.toContain('NINO-00001');
    expect((await datos.sugerencias({ ninoId: 'NINO-00001' })).length).toBeGreaterThan(0);
  });

  it('recuerda la usuaria elegida y la olvida al reiniciar la demo', async () => {
    const { datos } = servicios();
    expect(await datos.usuariaElegida()).toBe(false);
    await datos.cambiarUsuaria('USR-ROSA');
    expect(await datos.usuariaElegida()).toBe(true);
    await datos.reiniciarDemo();
    expect(await datos.usuariaElegida()).toBe(false);
  });

  it('el catálogo de salas del jardín trae las 3 salas, sin datos de niños', async () => {
    const { datos } = servicios();
    const salas = await datos.salasDelJardin();
    expect(salas.map((s) => s.nombre)).toEqual([
      'Medio Menor A',
      'Medio Menor B',
      'Sala Cuna Mayor',
    ]);
  });
});

describe('evidencias nuevas', () => {
  it('se guardan con el día de la demo y la hora real, y quedan al final (orden de llegada)', async () => {
    const { datos } = servicios();
    const nueva = await datos.guardarEvidencia({ salaId: 'SALA-MMA', autorId: 'USR-ANA', formato: 'texto' });
    expect(nueva.creadaEn.slice(0, 10)).toBe(semilla.fechaDemo);
    const todas = await datos.evidencias({ salaId: 'SALA-MMA' });
    expect(todas[todas.length - 1].id).toBe(nueva.id);
  });
});

describe('capturar', () => {
  it('devuelve de inmediato una evidencia en proceso y deja las sugerencias pendientes', async () => {
    const { datos, ia } = servicios();
    const antes = (await datos.sugerencias({ estado: ['pendiente'] })).length;

    const { evidencia, procesada } = await capturar('texto', undefined, 'Martina cuenta objetos hasta 10.', undefined, { datos, ia });
    expect(evidencia.estado).toBe('procesando');
    expect(evidencia.autorId).toBe('USR-ANA');
    expect(evidencia.salaId).toBe('SALA-MMA');

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
      'NINO-00003',
      { datos, ia },
    );
    const sugerencias = await procesada;
    expect(sugerencias[0].ninoId).toBe('NINO-00003');
  });

  it('el nivel propuesto usa el nivel actual del núcleo del niño/a', async () => {
    const { datos, ia } = servicios();
    const { procesada } = await capturar(
      'texto',
      undefined,
      'Josefa usa palabras nuevas para contar temas de su interés.',
      undefined,
      { datos, ia },
    );
    const [sug] = await procesada;
    expect(sug.ninoId).toBe('NINO-00001');
    expect(sug.nucleo).toBe('LV');
    expect(sug.nivel).toBe(2); // nivel actual de Josefa en Lenguaje Verbal
  });
});
