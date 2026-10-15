import { describe, expect, it } from 'vitest';
import semillaJson from '@data/semilla.json';
import { agendaDelDia, periodoDe, proximoIEA, semanaDe } from './agenda';
import type { Semilla } from './tipos';

const semilla = semillaJson as unknown as Semilla;
const HOY = semilla.fechaDemo; // jueves 2026-10-15
const salaA = (x: { salaId: string }) => x.salaId === 'SG-A';

describe('agenda', () => {
  it('asigna cada hora a su período de la jornada', () => {
    expect(periodoDe('08:00').nombre).toBe('Recepción y saludo');
    expect(periodoDe('09:45').nombre).toBe('Experiencia de aprendizaje');
    expect(periodoDe('10:30').nombre).toBe('Patio y juego libre');
    expect(periodoDe('16:30').nombre).toBe('Despedida');
  });

  it('arma la semana de lunes a viernes y marca hoy', () => {
    const semana = semanaDe(HOY, semilla.evidencias.filter(salaA), semilla.sugerencias);
    expect(semana.map((d) => d.nombreCorto)).toEqual(['lun', 'mar', 'mié', 'jue', 'vie']);
    expect(semana.map((d) => d.numero)).toEqual([12, 13, 14, 15, 16]);
    expect(semana.find((d) => d.esHoy)?.numero).toBe(15);
  });

  it('un sábado muestra la semana que termina', () => {
    const semana = semanaDe('2026-10-17', [], []);
    expect(semana[0].fecha).toBe('2026-10-12');
    expect(semana[4].fecha).toBe('2026-10-16');
  });

  it('ordena los registros del día por período y deja fuera lo descartado', () => {
    const periodos = agendaDelDia(
      HOY,
      semilla.evidencias.filter(salaA),
      semilla.sugerencias,
      (id) => semilla.ninos.find((n) => n.id === id)?.nombre,
    );
    const registros = periodos.flatMap((p) => p.registros);
    expect(registros.length).toBeGreaterThan(0);
    // La nota de "Naya" de hoy está pendiente y nombra a Nayara.
    const naya = registros.find((r) => r.texto.includes('Naya'));
    expect(naya?.entradas[0].nombre).toBe('Nayara');
    expect(naya?.entradas[0].pendiente).toBe(true);
    // Cada registro cae en el período de su hora.
    for (const p of periodos) {
      for (const r of p.registros) expect(periodoDe(r.hora).inicio).toBe(p.inicio);
    }
  });

  it('calcula el próximo registro del IEA', () => {
    expect(proximoIEA('2026-03-10')).toEqual({ numero: 1, mes: 'abril' });
    expect(proximoIEA('2026-06-01')).toEqual({ numero: 2, mes: 'agosto' });
    expect(proximoIEA(HOY)).toEqual({ numero: 3, mes: 'noviembre' });
    expect(proximoIEA('2026-12-05')).toEqual({ numero: 1, mes: 'abril' });
  });
});
