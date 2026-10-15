import { describe, expect, it } from 'vitest';
import semillaJson from '@data/semilla.json';
import {
  diasEntre,
  edadAniosMeses,
  edadMeses,
  evaluacionesDe,
  evaluacionesValidadas,
  frescura,
  fueraDeRangoRubrica,
  nivelActualPorNucleo,
  nivelEsperado,
  nivelEsperadoEnFecha,
  nivelesEsperados,
  nivelGeneral,
  observarAhora,
  resumenSala,
  revisarAvance,
} from './evaluacion';
import { codigosNucleos, niveles } from './rubrica';
import type { EvaluacionValidada, Nivel, NucleoId, Semilla } from './tipos';

const semilla = semillaJson as unknown as Semilla;
const HOY = semilla.fechaDemo; // 2026-10-15

let contador = 0;
/** Arma una evaluación validada mínima para las pruebas. */
function ev(nucleo: NucleoId, nivel: Nivel, fecha: string, ninoId = 'NINO-TEST'): EvaluacionValidada {
  contador += 1;
  return {
    sugerenciaId: `SUG-T${contador}`,
    evidenciaId: `EVI-T${contador}`,
    ninoId,
    salaId: 'SALA-TEST',
    nucleo,
    nivel,
    fecha,
    cita: 'cita de prueba',
  };
}

/** Fecha ISO a N días antes de `HOY`. */
function haceDias(dias: number): string {
  const d = new Date(Date.UTC(2026, 9, 15) - dias * 86_400_000);
  return d.toISOString().slice(0, 10);
}

describe('edadMeses', () => {
  it('cuenta meses completos cumplidos', () => {
    expect(edadMeses('2023-11-26', '2026-10-15')).toBe(34);
    expect(edadMeses('2024-01-15', '2026-01-15')).toBe(24);
    expect(edadMeses('2024-01-15', '2026-01-14')).toBe(23);
    expect(edadMeses('2024-01-15', '2024-01-15')).toBe(0);
  });

  it('nunca devuelve meses negativos', () => {
    expect(edadMeses('2026-12-01', '2026-10-15')).toBe(0);
  });

  it('entrega años y meses para mostrar en la ficha', () => {
    expect(edadAniosMeses('2023-11-26', '2026-10-15')).toEqual({ anios: 2, meses: 10 });
  });
});

describe('diasEntre', () => {
  it('cuenta días calendario e ignora la hora', () => {
    expect(diasEntre('2026-10-01T23:59:00', '2026-10-15T00:01:00')).toBe(14);
    expect(diasEntre('2026-10-15', '2026-10-15')).toBe(0);
  });
});

describe('niveles esperados por edad (misma regla del backend)', () => {
  it('da los valores de referencia de integra-backend (dominio.md)', () => {
    const referencia: [number, Nivel[]][] = [
      [0, [1]],
      [2, [1, 2]],
      [5, [3]],
      [12, [5, 6]],
      [14, [6]],
      [24, [8]],
      [31, [9]],
      [40, [9]],
    ];
    for (const [edad, esperados] of referencia) expect(nivelesEsperados(edad)).toEqual(esperados);
  });

  it('marca la edad que pasa los 36 meses de la rúbrica', () => {
    expect(fueraDeRangoRubrica(36)).toBe(false);
    expect(fueraDeRangoRubrica(40)).toBe(true);
  });

  it('el nivel esperado es el menor de los esperados: en un borde no se pide de más', () => {
    expect(nivelEsperado(12)).toBe(5);
    expect(nivelEsperado(14)).toBe(6);
    expect(nivelEsperado(40)).toBe(9);
    // Dentro de cada rango (sin tocar los bordes) hay un solo nivel esperado.
    for (const n of niveles()) {
      if (n.edadMaxMeses - n.edadMinMeses < 2) continue;
      expect(nivelEsperado(n.edadMinMeses + 1)).toBe(n.nivel);
    }
  });

  it('usa la edad que tenía el niño/a en la fecha de la evidencia', () => {
    // Josefa, nacida el 26-11-2023: 34 meses hoy (nivel 9), 21 meses en agosto de 2025 (7 u 8).
    expect(nivelEsperadoEnFecha('2023-11-26', '2026-10-15')).toBe(9);
    expect(nivelEsperadoEnFecha('2023-11-26', '2025-08-30T10:00:00')).toBe(7);
  });
});

describe('nivelActualPorNucleo y nivelGeneral', () => {
  it('toma el nivel de la evaluación validada más reciente de cada núcleo', () => {
    const porNucleo = nivelActualPorNucleo([
      ev('lenguaje_comunicacion', 7, '2026-09-15T12:10:00'),
      ev('lenguaje_comunicacion', 8, '2026-10-06T10:30:00'),
      ev('cognitivo', 9, '2026-08-01T09:00:00'),
    ]);
    expect(porNucleo.lenguaje_comunicacion).toBe(8);
    expect(porNucleo.cognitivo).toBe(9);
  });

  it('deja en null los núcleos sin evidencia (nunca en 0)', () => {
    const porNucleo = nivelActualPorNucleo([ev('lenguaje_comunicacion', 7, '2026-09-15T12:10:00')]);
    expect(Object.keys(porNucleo)).toEqual(codigosNucleos());
    expect(porNucleo.motor_grueso).toBeNull();
    expect(porNucleo.socioemocional).toBeNull();
  });

  it('calcula la mediana redondeada hacia abajo', () => {
    // Impar: 7, 9, 9 → 9.
    expect(
      nivelGeneral(
        nivelActualPorNucleo([
          ev('lenguaje_comunicacion', 7, '2026-01-01'),
          ev('cognitivo', 9, '2026-01-01'),
          ev('motor_fino', 9, '2026-01-01'),
        ]),
      ),
    ).toBe(9);
    // Par: 7 y 8 → 7,5 → 7.
    expect(
      nivelGeneral(
        nivelActualPorNucleo([
          ev('lenguaje_comunicacion', 7, '2026-01-01'),
          ev('cognitivo', 8, '2026-01-01'),
        ]),
      ),
    ).toBe(7);
    // Sin evidencia → null.
    expect(nivelGeneral(nivelActualPorNucleo([]))).toBeNull();
  });
});

describe('frescura', () => {
  it('es verde bajo los 14 días', () => {
    expect(frescura([ev('motor_fino', 8, haceDias(13))], HOY)).toBe('verde');
  });

  it('es amarilla entre 14 y 30 días', () => {
    expect(frescura([ev('motor_fino', 8, haceDias(14))], HOY)).toBe('amarillo');
    expect(frescura([ev('motor_fino', 8, haceDias(30))], HOY)).toBe('amarillo');
  });

  it('es roja sobre los 30 días', () => {
    expect(frescura([ev('motor_fino', 8, haceDias(31))], HOY)).toBe('rojo');
  });

  it('es roja si no hay ninguna evidencia validada', () => {
    expect(frescura([], HOY)).toBe('rojo');
  });

  it('usa la evidencia más reciente de cualquier núcleo', () => {
    expect(
      frescura([ev('motor_fino', 8, haceDias(40)), ev('cognitivo', 8, haceDias(2))], HOY),
    ).toBe('verde');
  });
});

describe('revisarAvance', () => {
  const nacimiento = '2023-11-26'; // 33 a 34 meses en sep-oct de 2026 → nivel esperado 9.
  const LC: NucleoId = 'lenguaje_comunicacion';

  it('no marca con una sola evaluación', () => {
    expect(revisarAvance([ev(LC, 7, '2026-10-06T10:30:00')], nacimiento)).toEqual([]);
  });

  it('marca con 2 evaluaciones bajas de fechas distintas', () => {
    const marcados = revisarAvance(
      [ev(LC, 7, '2026-10-06T10:30:00'), ev(LC, 7, '2026-09-15T12:10:00')],
      nacimiento,
    );
    expect(marcados).toEqual([LC]);
  });

  it('no marca si las 2 evaluaciones son del mismo día', () => {
    const marcados = revisarAvance(
      [ev(LC, 7, '2026-10-06T10:30:00'), ev(LC, 7, '2026-10-06T16:00:00')],
      nacimiento,
    );
    expect(marcados).toEqual([]);
  });

  it('no marca si el nivel es bajo solo para la edad actual, pero normal para la edad de la fecha', () => {
    // Nacido el 15-10-2024: hoy tiene 24 meses (esperado 8), pero en abril y mayo
    // de 2025 tenía 6 y 7 meses (esperado 3 y 4), así que un nivel 4 era lo normal.
    const marcados = revisarAvance(
      [ev(LC, 4, '2025-05-20T10:00:00'), ev(LC, 4, '2025-04-20T10:00:00')],
      '2024-10-15',
    );
    expect(marcados).toEqual([]);
  });

  it('solo mira las 2 últimas: si la última está al día, no marca', () => {
    const marcados = revisarAvance(
      [
        ev(LC, 9, '2026-10-10T10:00:00'),
        ev(LC, 7, '2026-10-06T10:30:00'),
        ev(LC, 7, '2026-09-15T12:10:00'),
      ],
      nacimiento,
    );
    expect(marcados).toEqual([]);
  });

  it('no marca cuando la diferencia con el nivel esperado es de solo 1', () => {
    const marcados = revisarAvance(
      [ev('cognitivo', 8, '2026-10-06T10:30:00'), ev('cognitivo', 8, '2026-09-15T12:10:00')],
      nacimiento,
    );
    expect(marcados).toEqual([]);
  });
});

describe('observarAhora', () => {
  it('sin evidencia en un núcleo, propone conductas del nivel esperado por edad', () => {
    const evaluaciones = [ev('lenguaje_comunicacion', 8, '2026-10-10'), ev('cognitivo', 9, '2026-01-05')];
    const sug = observarAhora(evaluaciones, nivelActualPorNucleo(evaluaciones), 9);
    expect(sug?.nucleo).toBe('motor_grueso'); // el primero sin evidencia, en el orden de la rúbrica
    expect(sug?.nivel).toBe(9);
    expect(sug?.conductas.length).toBeGreaterThan(0);
    expect(sug?.conductas.length).toBeLessThanOrEqual(2);
  });

  it('cuando todos los núcleos tienen evidencia, elige la más antigua y sube un nivel', () => {
    const evaluaciones = codigosNucleos().map((n, i) =>
      ev(n, 7, n === 'cognitivo' ? '2026-02-01' : `2026-09-${String(i + 1).padStart(2, '0')}`),
    );
    const sug = observarAhora(evaluaciones, nivelActualPorNucleo(evaluaciones), 9);
    expect(sug?.nucleo).toBe('cognitivo');
    expect(sug?.nivel).toBe(8);
  });
});

describe('con los datos de la demo (data/semilla.json)', () => {
  const evaluaciones = evaluacionesValidadas(semilla.sugerencias, semilla.evidencias);

  it('la semilla usa solo núcleos y niveles de la rúbrica E-1', () => {
    const validos = new Set(codigosNucleos());
    for (const s of semilla.sugerencias) {
      if (s.tipo !== 'evaluacion') continue;
      expect(validos.has(s.nucleo!)).toBe(true);
      expect(s.nivel).toBeGreaterThanOrEqual(1);
      expect(s.nivel).toBeLessThanOrEqual(9);
    }
    expect(semilla.sugerencias.filter((s) => s.estado === 'pendiente').length).toBeGreaterThan(0);
  });

  it('solo Josefa queda con revisar avance, en Lenguaje y comunicación', () => {
    const marcados: string[] = [];
    for (const nino of semilla.ninos) {
      const suyas = evaluacionesDe(evaluaciones, nino.id);
      for (const nucleo of revisarAvance(suyas, nino.fechaNacimiento)) {
        marcados.push(`${nino.nombre} ${nino.id} ${nucleo}`);
      }
    }
    expect(marcados).toEqual(['Josefa NINO-00001 lenguaje_comunicacion']);
  });

  it('el nivel general de Josefa es la mediana de sus núcleos con evidencia', () => {
    const josefa = semilla.ninos.find((n) => n.id === 'NINO-00001')!;
    const suyas = evaluacionesDe(evaluaciones, josefa.id);
    const porNucleo = nivelActualPorNucleo(suyas);
    expect(porNucleo.lenguaje_comunicacion).toBe(7);
    expect(porNucleo.motor_grueso).toBeNull();
    // Niveles con evidencia: 7, 9, 9 y 9 → mediana 9.
    expect(nivelGeneral(porNucleo)).toBe(9);
    expect(frescura(suyas, HOY)).toBe('verde');
  });

  it('el resumen de cada sala cuadra con la semilla', () => {
    const resumen = (salaId: string) =>
      resumenSala(
        semilla.ninos.filter((n) => n.salaId === salaId),
        evaluaciones,
        HOY,
      );
    expect(resumen('SALA-MMA')).toEqual({
      total: 18,
      observadosMes: 16,
      nucleoMenosCubierto: 'motor_grueso',
    });
    expect(resumen('SALA-MMB').nucleoMenosCubierto).toBe('socioemocional');
    expect(resumen('SALA-SCM').nucleoMenosCubierto).toBe('lenguaje_comunicacion');
  });
});
