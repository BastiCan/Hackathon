import { describe, expect, it } from 'vitest';
import semillaJson from '@data/semilla.json';
import { IAServiceSimulado, type ContextoIA } from './ia';
import type { Evidencia, Formato, Semilla } from '../lib/tipos';

const semilla = semillaJson as unknown as Semilla;

/** Sala Medio Menor A, la de la demo. */
const ninosSala = semilla.ninos.filter((n) => n.salaId === 'SALA-MMA' && n.activo);

const contexto: ContextoIA = {
  ninos: ninosSala.map((n) => ({ id: n.id, nombre: n.nombre, nivelEsperado: 4 })),
};

function evidencia(formato: Formato, textoExtraido?: string): Evidencia {
  return {
    id: 'EVI-TEST',
    salaId: 'SALA-MMA',
    autorId: 'USR-ANA',
    creadaEn: '2026-10-15T10:00:00',
    formato,
    textoExtraido,
    estado: 'procesando',
  };
}

function ia() {
  return new IAServiceSimulado({ guiones: semilla.demoCapturas, latenciaMs: 0 });
}

describe('IAServiceSimulado', () => {
  it('con un nombre exacto de la sala y una conducta reconocible, la certeza es alta', async () => {
    const texto = 'Martina clasifica los bloques por color y forma, y los ordena por tamaño.';
    const [sug, ...resto] = await ia().procesar(evidencia('texto', texto), undefined, contexto);

    expect(resto).toHaveLength(0);
    expect(sug.tipo).toBe('evaluacion');
    expect(sug.ninoId).toBe('NINO-00004');
    expect(sug.nombreDetectado).toBe('Martina');
    expect(sug.nucleo).toBe('PM');
    expect(sug.certeza).toBe('alta');
    expect(sug.estado).toBe('pendiente');
    expect(sug.cita).toContain('Martina');
  });

  it('usa solo conductas y niveles que existen en la rúbrica', async () => {
    const texto = 'Sofía cuenta objetos hasta 10 mientras ordena las tapitas.';
    const [sug] = await ia().procesar(evidencia('texto', texto), undefined, contexto);

    expect(sug.nivel).toBeGreaterThanOrEqual(1);
    expect(sug.nivel).toBeLessThanOrEqual(8);
    const { conductas } = await import('../lib/rubrica');
    expect(conductas(sug.nucleo!, sug.nivel!)).toContain(sug.conducta);
  });

  it('reconoce nombres con tilde', async () => {
    const texto = 'Tomás describe la posición de los objetos: cerca, lejos, encima y debajo.';
    const [sug] = await ia().procesar(evidencia('texto', texto), undefined, contexto);
    expect(sug.ninoId).toBe('NINO-00005');
  });

  it('si la nota menciona a 2 niños, genera 2 sugerencias', async () => {
    const texto =
      'Emilio reproduce patrones simples de dos elementos. Isidora usa mucho y poco al comparar.';
    const sugerencias = await ia().procesar(evidencia('texto', texto), undefined, contexto);

    expect(sugerencias).toHaveLength(2);
    expect(sugerencias.map((s) => s.ninoId).sort()).toEqual(['NINO-00002', 'NINO-00009']);
    expect(new Set(sugerencias.map((s) => s.id)).size).toBe(2);
    // Cada tarjeta cita la parte que le corresponde.
    expect(sugerencias.find((s) => s.ninoId === 'NINO-00009')?.cita).toContain('Isidora');
  });

  it('ordena las sugerencias según quién aparece primero en la nota', async () => {
    const texto = 'Tomás armó un puzzle de 6 piezas y le explicó a Gaspar cómo hacerlo.';
    const sugerencias = await ia().procesar(evidencia('texto', texto), undefined, contexto);
    const nombres = sugerencias.map((s) => s.nombreDetectado);
    expect(nombres).toEqual(['Tomás', 'Gaspar']);
  });

  it('un texto grupal o no evaluativo queda como nota de sala', async () => {
    const texto = 'Hoy bajó la asistencia y los niños estuvieron con tos toda la jornada.';
    const sugerencias = await ia().procesar(evidencia('texto', texto), undefined, contexto);

    expect(sugerencias).toHaveLength(1);
    expect(sugerencias[0].tipo).toBe('nota_sala');
    expect(sugerencias[0].ninoId).toBeUndefined();
    expect(sugerencias[0].nucleo).toBeUndefined();
  });

  it('un nombre que no es de la sala queda por confirmar, con certeza baja y sin ninoId', async () => {
    const texto = 'Fernanda cuenta objetos hasta 10 en el patio.';
    const sugerencias = await ia().procesar(evidencia('texto', texto), undefined, contexto);

    expect(sugerencias).toHaveLength(1);
    expect(sugerencias[0].nombreDetectado).toBe('Fernanda');
    expect(sugerencias[0].ninoId).toBeUndefined();
    expect(sugerencias[0].certeza).toBe('baja');
  });

  it('si el texto calza con un guion de la demo, devuelve sus sugerencias predefinidas', async () => {
    const guion = semilla.demoCapturas[3]; // Sofía y Martina
    const sugerencias = await ia().procesar(
      evidencia('texto', guion.texto),
      undefined,
      contexto,
    );

    expect(sugerencias).toHaveLength(guion.sugerencias.length);
    expect(sugerencias.map((s) => s.ninoId)).toEqual(guion.sugerencias.map((s) => s.ninoId));
    expect(sugerencias[0].conducta).toBe(guion.sugerencias[0].conducta);
    expect(sugerencias.every((s) => s.estado === 'pendiente')).toBe(true);
  });

  it('una foto sin texto toma el siguiente guion de foto de la demo', async () => {
    const servicio = ia();
    const primera = await servicio.procesar(evidencia('foto'), undefined, contexto);
    expect(primera[0].ninoId).toBe('NINO-00001'); // Josefa, post-it de los individuales
    expect(primera[0].nucleo).toBe('CC');

    // El guion no se repite: la siguiente foto toma el siguiente guion de foto
    // (Emilio y las hojas de otoño), con su foto de ejemplo.
    const segunda = await servicio.procesar(evidencia('foto'), undefined, contexto);
    expect(segunda[0].ninoId).toBe('NINO-00002');
    expect(segunda[0].nucleo).toBe('PM');
  });

  it('recuerda lo leído y la foto de ejemplo del guion', async () => {
    const servicio = ia();
    const ev = evidencia('foto');
    await servicio.procesar(ev, undefined, contexto);
    const lectura = servicio.lecturaDe(ev.id);
    expect(lectura?.texto).toContain('individuales');
    expect(lectura?.foto).toBe('postit-individuales');
  });

  it('un audio sin texto toma el guion de audio de la demo', async () => {
    const [sug] = await ia().procesar(evidencia('audio'), undefined, contexto);
    expect(sug.tipo).toBe('nota_sala'); // "Hoy bajó la asistencia…"
  });

  it('simula latencia antes de responder', async () => {
    const lenta = new IAServiceSimulado({ guiones: semilla.demoCapturas, latenciaMs: 30 });
    const inicio = Date.now();
    await lenta.procesar(evidencia('texto', 'Martina cuenta objetos hasta 10.'), undefined, contexto);
    expect(Date.now() - inicio).toBeGreaterThanOrEqual(25);
  });
});
