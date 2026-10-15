import { describe, expect, it } from 'vitest';
import semillaJson from '@data/semilla.json';
import {
  diasEntre,
  edadAniosMeses,
  edadMeses,
  evaluacionesDe,
  evaluacionesValidadas,
  frescura,
  nivelActualPorNucleo,
  nivelEsperado,
  nivelEsperadoEnFecha,
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
    expect(diasEntre('2026-10-13T12:00:00-03:00', '2026-10-15')).toBe(2);
  });
});

describe('nivelEsperado', () => {
  it('respeta los bordes de cada rango de la rúbrica', () => {
    // Borde inferior inclusivo y borde superior exclusivo en los 9 rangos.
    for (const n of niveles()) {
      expect(nivelEsperado(n.edadDesdeMeses)).toBe(n.nivel);
      expect(nivelEsperado(n.edadHastaMeses - 1)).toBe(n.nivel);
    }
  });

  it('cubre los rangos de la ruta de niveles del dataset E-1', () => {
    const esperados: [number, Nivel][] = [
      [0, 1],
      [1, 1],
      [2, 2],
      [3, 2],
      [4, 3],
      [5, 3],
      [6, 4],
      [8, 4],
      [9, 5],
      [11, 5],
      [12, 6],
      [17, 6],
      [18, 7],
      [20, 7],
      [21, 8],
      [26, 8],
      [27, 9],
      [35, 9],
    ];
    for (const [edad, nivel] of esperados) expect(nivelEsperado(edad)).toBe(nivel);
  });

  it('sobre el último rango se queda en el nivel 9', () => {
    expect(nivelEsperado(36)).toBe(9);
    expect(nivelEsperado(40)).toBe(9);
  });

  it('usa la edad que tenía el niño/a en la fecha de la evidencia', () => {
    // Josefa, nacida el 01-06-2024: 28 meses hoy (nivel 9), 10 meses en abril de 2025 (nivel 5).
    expect(nivelEsperadoEnFecha('2024-06-01', '2026-10-15')).toBe(9);
    expect(nivelEsperadoEnFecha('2024-06-01', '2025-04-13T12:00:00-03:00')).toBe(5);
  });
});

describe('nivelActualPorNucleo y nivelGeneral', () => {
  it('toma el nivel de la evaluación validada más reciente de cada núcleo', () => {
    const niveles = nivelActualPorNucleo([
      ev('lenguaje_comunicacion', 2, '2026-09-15T12:10:00'),
      ev('lenguaje_comunicacion', 3, '2026-10-06T10:30:00'),
      ev('cognitivo', 5, '2026-08-01T09:00:00'),
    ]);
    expect(niveles.lenguaje_comunicacion).toBe(3);
    expect(niveles.cognitivo).toBe(5);
  });

  it('deja en null los núcleos sin evidencia (nunca en 0)', () => {
    const niveles = nivelActualPorNucleo([ev('lenguaje_comunicacion', 2, '2026-09-15T12:10:00')]);
    expect(niveles.motor_grueso).toBeNull();
    expect(niveles.motor_fino).toBeNull();
    expect(Object.keys(niveles)).toHaveLength(5);
    // Los núcleos sin evidencia quedan en null; los demás, entre 1 y 9.
    for (const valor of Object.values(niveles)) {
      if (valor !== null) expect(valor).toBeGreaterThanOrEqual(1);
    }
  });

  it('calcula la mediana redondeada hacia abajo', () => {
    // Impar: 2, 4, 4 → 4.
    expect(
      nivelGeneral(
        nivelActualPorNucleo([
          ev('lenguaje_comunicacion', 2, '2026-01-01'),
          ev('cognitivo', 4, '2026-01-01'),
          ev('motor_grueso', 4, '2026-01-01'),
        ]),
      ),
    ).toBe(4);
    // Par: 3 y 4 → 3,5 → 3.
    expect(
      nivelGeneral(
        nivelActualPorNucleo([
          ev('lenguaje_comunicacion', 3, '2026-01-01'),
          ev('cognitivo', 4, '2026-01-01'),
        ]),
      ),
    ).toBe(3);
    // Sin evidencia → null.
    expect(nivelGeneral(nivelActualPorNucleo([]))).toBeNull();
  });
});

describe('frescura', () => {
  it('es verde bajo los 14 días', () => {
    expect(frescura([ev('lenguaje_comunicacion', 4, haceDias(13))], HOY)).toBe('verde');
  });

  it('es amarilla entre 14 y 30 días', () => {
    expect(frescura([ev('lenguaje_comunicacion', 4, haceDias(14))], HOY)).toBe('amarillo');
    expect(frescura([ev('lenguaje_comunicacion', 4, haceDias(30))], HOY)).toBe('amarillo');
  });

  it('es roja sobre los 30 días', () => {
    expect(frescura([ev('lenguaje_comunicacion', 4, haceDias(31))], HOY)).toBe('rojo');
  });

  it('es roja si no hay ninguna evidencia validada', () => {
    expect(frescura([], HOY)).toBe('rojo');
  });

  it('usa la evidencia más reciente de cualquier núcleo', () => {
    expect(
      frescura([ev('lenguaje_comunicacion', 4, haceDias(40)), ev('cognitivo', 4, haceDias(2))], HOY),
    ).toBe('verde');
  });
});

describe('revisarAvance', () => {
  const nacimiento = '2023-11-26'; // 34 meses al 2026-10-15 → nivel esperado 9.

  it('no marca con una sola evaluación', () => {
    expect(revisarAvance([ev('lenguaje_comunicacion', 2, '2026-10-06T10:30:00')], nacimiento)).toEqual(
      [],
    );
  });

  it('marca con 2 evaluaciones bajas de fechas distintas', () => {
    const marcados = revisarAvance(
      [
        ev('lenguaje_comunicacion', 7, '2026-10-06T10:30:00'),
        ev('lenguaje_comunicacion', 7, '2026-09-15T12:10:00'),
      ],
      nacimiento,
    );
    expect(marcados).toEqual(['lenguaje_comunicacion']);
  });

  it('no marca si las 2 evaluaciones son del mismo día', () => {
    const marcados = revisarAvance(
      [
        ev('lenguaje_comunicacion', 2, '2026-10-06T10:30:00'),
        ev('lenguaje_comunicacion', 2, '2026-10-06T16:00:00'),
      ],
      nacimiento,
    );
    expect(marcados).toEqual([]);
  });

  it('no marca si el nivel es bajo solo para la edad actual, pero normal para la edad de la fecha', () => {
    // Nacido el 15-10-2022: hoy tiene 48 meses (esperado 9), pero en noviembre y
    // diciembre de 2023 tenía 13 y 14 meses (esperado 6), así que un nivel 6 era lo normal.
    const marcados = revisarAvance(
      [
        ev('lenguaje_comunicacion', 6, '2023-12-20T10:00:00'),
        ev('lenguaje_comunicacion', 6, '2023-11-20T10:00:00'),
      ],
      '2022-10-15',
    );
    expect(marcados).toEqual([]);
  });

  it('solo mira las 2 últimas: si la última está al día, no marca', () => {
    const marcados = revisarAvance(
      [
        ev('lenguaje_comunicacion', 9, '2026-10-10T10:00:00'),
        ev('lenguaje_comunicacion', 2, '2026-10-06T10:30:00'),
        ev('lenguaje_comunicacion', 2, '2026-09-15T12:10:00'),
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
  it('propone conductas del nivel esperado en el primer núcleo sin evidencia', () => {
    const evaluaciones = [ev('lenguaje_comunicacion', 3, '2026-10-10'), ev('cognitivo', 4, '2026-01-05')];
    const sugerencia = observarAhora(evaluaciones, nivelActualPorNucleo(evaluaciones), 4);
    expect(sugerencia).not.toBeNull();
    expect(sugerencia?.nucleo).toBe('motor_grueso');
    expect(sugerencia?.nivel).toBe(4); // sin evidencia → nivel esperado por edad
    expect(sugerencia?.conductas).toHaveLength(2);
  });

  it('cuando todos los núcleos tienen evidencia, elige la más antigua y sube un nivel', () => {
    const evaluaciones = codigosNucleos().map((n, i) =>
      ev(n, 4, n === 'socioemocional' ? '2026-02-01' : `2026-09-${String(i + 1).padStart(2, '0')}`),
    );
    const sugerencia = observarAhora(evaluaciones, nivelActualPorNucleo(evaluaciones), 4);
    expect(sugerencia?.nucleo).toBe('socioemocional');
    expect(sugerencia?.nivel).toBe(5);
  });
});

describe('con los datos de la demo (data/semilla.json)', () => {
  const evaluaciones = evaluacionesValidadas(semilla.sugerencias, semilla.evidencias);

  it('la semilla trae evaluaciones validadas y sugerencias pendientes', () => {
    expect(evaluaciones.length).toBeGreaterThan(0);
    expect(semilla.sugerencias.filter((s) => s.estado === 'pendiente')).toHaveLength(3);
  });

  it('el historial del dataset no deja a nadie en revisar avance', () => {
    const marcados: string[] = [];
    for (const nino of semilla.ninos) {
      const suyas = evaluacionesDe(evaluaciones, nino.id);
      for (const nucleo of revisarAvance(suyas, nino.fechaNacimiento)) {
        marcados.push(`${nino.nombre} ${nino.id} ${nucleo}`);
      }
    }
    expect(marcados).toEqual([]);
  });

  it('el nivel general de Josefa es la mediana de sus núcleos con evidencia', () => {
    const josefa = semilla.ninos.find((n) => n.id === 'NINO-00008')!;
    const suyas = evaluacionesDe(evaluaciones, josefa.id);
    const porNucleo = nivelActualPorNucleo(suyas);
    expect(porNucleo).toEqual({
      motor_grueso: 5,
      motor_fino: 5,
      lenguaje_comunicacion: 4,
      socioemocional: 5,
      cognitivo: 6,
    });
    // Niveles con evidencia: 4, 5, 5, 5 y 6 → mediana 5.
    expect(nivelGeneral(porNucleo)).toBe(5);
    // Su último registro validado es de agosto de 2025.
    expect(frescura(suyas, HOY)).toBe('rojo');
  });

  it('el resumen de la Sala A cuadra con la semilla', () => {
    const ninos = semilla.ninos.filter((n) => n.salaId === 'SG-A');
    const resumen = resumenSala(ninos, evaluaciones, HOY);
    expect(resumen.total).toBe(13);
    // Esperanza (13 de octubre) y Tomás (la foto de las tortugas de hoy).
    expect(resumen.observadosMes).toBe(2);
    expect(resumen.nucleoMenosCubierto).toBe('motor_grueso');
  });
});
