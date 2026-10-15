import { describe, expect, it } from 'vitest';
import semillaJson from '@data/semilla.json';
import { estadoRegistro, etiquetaDia, proximoIEA, semanaDe } from './inicio';
import type { Evidencia, Semilla, Sugerencia } from './tipos';

const semilla = semillaJson as unknown as Semilla;
const HOY = semilla.fechaDemo; // jueves 2026-10-15
const salaA = (x: { salaId: string }) => x.salaId === 'SALA-MMA';

function evidencia(parcial: Partial<Evidencia> = {}): Evidencia {
  return {
    id: 'EVI-X',
    salaId: 'SALA-MMA',
    autorId: 'USR-ANA',
    creadaEn: '2026-10-14T10:00:00',
    formato: 'texto',
    estado: 'lista',
    ...parcial,
  };
}

function sugerencia(parcial: Partial<Sugerencia> = {}): Sugerencia {
  return {
    id: 'SUG-X',
    evidenciaId: 'EVI-X',
    salaId: 'SALA-MMA',
    tipo: 'evaluacion',
    cita: 'cita',
    certeza: 'alta',
    estado: 'aceptada',
    ...parcial,
  };
}

describe('semana de inicio', () => {
  it('arma la semana de lunes a viernes y marca hoy', () => {
    const semana = semanaDe(HOY, semilla.evidencias.filter(salaA), semilla.sugerencias);
    expect(semana.map((d) => d.nombreCorto)).toEqual(['lun', 'mar', 'mié', 'jue', 'vie']);
    expect(semana.map((d) => d.numero)).toEqual([12, 13, 14, 15, 16]);
    expect(semana.find((d) => d.esHoy)?.numero).toBe(15);
    expect(semana.filter((d) => d.esFuturo).map((d) => d.numero)).toEqual([16]);
  });

  it('cuenta los registros de cada día y los que faltan por revisar', () => {
    const semana = semanaDe(HOY, semilla.evidencias.filter(salaA), semilla.sugerencias);
    const hoy = semana.find((d) => d.esHoy)!;
    // Hoy: Emilio, Sofía y "Agus" esperan la revisión de la tía.
    expect(hoy.porRevisar).toBe(3);
    expect(hoy.registros).toBeGreaterThan(hoy.porRevisar);
    expect(hoy.puntos.filter((p) => p === 'pendiente')).toHaveLength(3);
    expect(semana.find((d) => d.esFuturo)?.registros).toBe(0);
  });

  it('un sábado muestra la semana que termina', () => {
    const semana = semanaDe('2026-10-17', [], []);
    expect(semana[0].fecha).toBe('2026-10-12');
    expect(semana[4].fecha).toBe('2026-10-16');
  });

  it('no dibuja más de 6 puntos por día', () => {
    const muchas = Array.from({ length: 9 }, (_, i) =>
      evidencia({ id: `EVI-${i}`, creadaEn: '2026-10-13T09:00:00' }),
    );
    const sugerencias = muchas.map((e) => sugerencia({ id: `S-${e.id}`, evidenciaId: e.id }));
    const martes = semanaDe(HOY, muchas, sugerencias)[1];
    expect(martes.registros).toBe(9);
    expect(martes.puntos).toHaveLength(6);
  });
});

describe('estado de un registro', () => {
  it('queda pendiente mientras se lee, si falló o si tiene algo por confirmar', () => {
    expect(estadoRegistro(evidencia({ estado: 'procesando' }), [])).toBe('pendiente');
    expect(estadoRegistro(evidencia({ estado: 'error' }), [])).toBe('pendiente');
    expect(estadoRegistro(evidencia(), [sugerencia({ estado: 'pendiente' })])).toBe('pendiente');
  });

  it('queda revisado cuando todo se confirmó, y no cuenta si se descartó entero', () => {
    expect(estadoRegistro(evidencia(), [sugerencia()])).toBe('revisado');
    expect(estadoRegistro(evidencia(), [sugerencia({ estado: 'descartada' })])).toBeNull();
    expect(estadoRegistro(evidencia(), [])).toBeNull();
  });
});

describe('textos de la semana', () => {
  it('describe cada día para quien usa lector de pantalla', () => {
    const [lunes, , , jueves, viernes] = semanaDe(
      HOY,
      semilla.evidencias.filter(salaA),
      semilla.sugerencias,
    );
    expect(etiquetaDia(lunes)).toMatch(/^lunes 12: \d+ registros?$/);
    expect(etiquetaDia(jueves)).toMatch(/^jueves 15, hoy: \d+ registros, 3 por revisar$/);
    expect(etiquetaDia(viernes)).toBe('viernes 16: todavía no llega');
  });

  it('calcula el próximo registro del IEA', () => {
    expect(proximoIEA('2026-03-10')).toEqual({ numero: 1, mes: 'abril' });
    expect(proximoIEA('2026-06-01')).toEqual({ numero: 2, mes: 'agosto' });
    expect(proximoIEA(HOY)).toEqual({ numero: 3, mes: 'noviembre' });
    expect(proximoIEA('2026-12-05')).toEqual({ numero: 1, mes: 'abril' });
  });
});
