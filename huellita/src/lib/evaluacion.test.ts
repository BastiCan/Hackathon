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
import { niveles } from './rubrica';
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

describe('nivelEsperado', () => {
  it('respeta los bordes de cada rango de la rúbrica', () => {
    // Borde inferior inclusivo y borde superior exclusivo en los 8 rangos.
    for (const n of niveles()) {
      expect(nivelEsperado(n.edadDesdeMeses)).toBe(n.nivel);
      expect(nivelEsperado(n.edadHastaMeses - 1)).toBe(n.nivel);
    }
  });

  it('cubre los rangos esperados de la rúbrica de Integra', () => {
    const esperados: [number, Nivel][] = [
      [0, 1],
      [11, 1],
      [12, 2],
      [23, 2],
      [24, 3],
      [31, 3],
      [32, 4],
      [39, 4],
      [40, 5],
      [47, 5],
      [48, 6],
      [55, 6],
      [56, 7],
      [63, 7],
      [64, 8],
      [71, 8],
    ];
    for (const [edad, nivel] of esperados) expect(nivelEsperado(edad)).toBe(nivel);
  });

  it('sobre el último rango se queda en el nivel 8', () => {
    expect(nivelEsperado(72)).toBe(8);
    expect(nivelEsperado(96)).toBe(8);
  });

  it('usa la edad que tenía el niño/a en la fecha de la evidencia', () => {
    // Josefa, nacida el 26-11-2023: 34 meses hoy (nivel 4), 21 meses en agosto 2025 (nivel 2).
    expect(nivelEsperadoEnFecha('2023-11-26', '2026-10-15')).toBe(4);
    expect(nivelEsperadoEnFecha('2023-11-26', '2025-08-30T10:00:00')).toBe(2);
  });
});

describe('nivelActualPorNucleo y nivelGeneral', () => {
  it('toma el nivel de la evaluación validada más reciente de cada núcleo', () => {
    const niveles = nivelActualPorNucleo([
      ev('LV', 2, '2026-09-15T12:10:00'),
      ev('LV', 3, '2026-10-06T10:30:00'),
      ev('PM', 5, '2026-08-01T09:00:00'),
    ]);
    expect(niveles.LV).toBe(3);
    expect(niveles.PM).toBe(5);
  });

  it('deja en null los núcleos sin evidencia (nunca en 0)', () => {
    const niveles = nivelActualPorNucleo([ev('LV', 2, '2026-09-15T12:10:00')]);
    expect(niveles.CM).toBeNull();
    expect(niveles.IA).toBeNull();
    // Los núcleos sin evidencia quedan en null; los demás, entre 1 y 8.
    for (const valor of Object.values(niveles)) {
      if (valor !== null) expect(valor).toBeGreaterThanOrEqual(1);
    }
  });

  it('calcula la mediana redondeada hacia abajo', () => {
    // Impar: 2, 4, 4 → 4.
    expect(nivelGeneral(nivelActualPorNucleo([ev('LV', 2, '2026-01-01'), ev('PM', 4, '2026-01-01'), ev('CM', 4, '2026-01-01')]))).toBe(4);
    // Par: 3 y 4 → 3,5 → 3.
    expect(nivelGeneral(nivelActualPorNucleo([ev('LV', 3, '2026-01-01'), ev('PM', 4, '2026-01-01')]))).toBe(3);
    // Sin evidencia → null.
    expect(nivelGeneral(nivelActualPorNucleo([]))).toBeNull();
  });
});

describe('frescura', () => {
  it('es verde bajo los 14 días', () => {
    expect(frescura([ev('LV', 4, haceDias(13))], HOY)).toBe('verde');
  });

  it('es amarilla entre 14 y 30 días', () => {
    expect(frescura([ev('LV', 4, haceDias(14))], HOY)).toBe('amarillo');
    expect(frescura([ev('LV', 4, haceDias(30))], HOY)).toBe('amarillo');
  });

  it('es roja sobre los 30 días', () => {
    expect(frescura([ev('LV', 4, haceDias(31))], HOY)).toBe('rojo');
  });

  it('es roja si no hay ninguna evidencia validada', () => {
    expect(frescura([], HOY)).toBe('rojo');
  });

  it('usa la evidencia más reciente de cualquier núcleo', () => {
    expect(frescura([ev('LV', 4, haceDias(40)), ev('PM', 4, haceDias(2))], HOY)).toBe('verde');
  });
});

describe('revisarAvance', () => {
  const nacimiento = '2023-11-26'; // 34 meses al 2026-10-15 → nivel esperado 4.

  it('no marca con una sola evaluación', () => {
    expect(revisarAvance([ev('LV', 2, '2026-10-06T10:30:00')], nacimiento)).toEqual([]);
  });

  it('marca con 2 evaluaciones bajas de fechas distintas', () => {
    const marcados = revisarAvance(
      [ev('LV', 2, '2026-10-06T10:30:00'), ev('LV', 2, '2026-09-15T12:10:00')],
      nacimiento,
    );
    expect(marcados).toEqual(['LV']);
  });

  it('no marca si las 2 evaluaciones son del mismo día', () => {
    const marcados = revisarAvance(
      [ev('LV', 2, '2026-10-06T10:30:00'), ev('LV', 2, '2026-10-06T16:00:00')],
      nacimiento,
    );
    expect(marcados).toEqual([]);
  });

  it('no marca si el nivel es bajo solo para la edad actual, pero normal para la edad de la fecha', () => {
    // Nacido el 15-10-2022: hoy tiene 48 meses (esperado 6), pero en diciembre de
    // 2023 tenía 13 y 14 meses (esperado 2), así que un nivel 2 era lo normal.
    const marcados = revisarAvance(
      [ev('LV', 2, '2023-12-20T10:00:00'), ev('LV', 2, '2023-11-20T10:00:00')],
      '2022-10-15',
    );
    expect(marcados).toEqual([]);
  });

  it('solo mira las 2 últimas: si la última está al día, no marca', () => {
    const marcados = revisarAvance(
      [
        ev('LV', 4, '2026-10-10T10:00:00'),
        ev('LV', 2, '2026-10-06T10:30:00'),
        ev('LV', 2, '2026-09-15T12:10:00'),
      ],
      nacimiento,
    );
    expect(marcados).toEqual([]);
  });

  it('no marca cuando la diferencia con el nivel esperado es de solo 1', () => {
    const marcados = revisarAvance(
      [ev('PM', 3, '2026-10-06T10:30:00'), ev('PM', 3, '2026-09-15T12:10:00')],
      nacimiento,
    );
    expect(marcados).toEqual([]);
  });
});

describe('observarAhora', () => {
  it('propone conductas del nivel siguiente en el núcleo con evidencia más antigua', () => {
    const evaluaciones = [ev('LV', 3, '2026-10-10'), ev('PM', 4, '2026-01-05')];
    // Todos los demás núcleos no tienen evidencia, así que uno de ellos gana.
    const sinEvidencia = observarAhora(evaluaciones, nivelActualPorNucleo(evaluaciones), 4);
    expect(sinEvidencia).not.toBeNull();
    expect(sinEvidencia?.nucleo).toBe('IA');
    expect(sinEvidencia?.nivel).toBe(4); // sin evidencia → nivel esperado por edad
    expect(sinEvidencia?.conductas.length).toBeGreaterThan(0);
    expect(sinEvidencia?.conductas.length).toBeLessThanOrEqual(2);
  });

  it('cuando todos los núcleos tienen evidencia, elige la más antigua y sube un nivel', () => {
    const todos: NucleoId[] = ['IA', 'CC', 'CM', 'LV', 'LA', 'EN', 'ES', 'PM'];
    const evaluaciones = todos.map((n, i) =>
      ev(n, 4, n === 'EN' ? '2026-02-01' : `2026-09-${String(i + 1).padStart(2, '0')}`),
    );
    const sug = observarAhora(evaluaciones, nivelActualPorNucleo(evaluaciones), 4);
    expect(sug?.nucleo).toBe('EN');
    expect(sug?.nivel).toBe(5);
  });
});

describe('con los datos de la demo (data/semilla.json)', () => {
  const evaluaciones = evaluacionesValidadas(semilla.sugerencias, semilla.evidencias);

  it('la semilla trae evaluaciones validadas y sugerencias pendientes', () => {
    expect(evaluaciones.length).toBeGreaterThan(0);
    expect(semilla.sugerencias.filter((s) => s.estado === 'pendiente').length).toBeGreaterThan(0);
  });

  it('solo Josefa queda con revisar avance, en el núcleo Lenguaje Verbal', () => {
    const marcados: string[] = [];
    for (const nino of semilla.ninos) {
      const suyas = evaluacionesDe(evaluaciones, nino.id);
      for (const nucleo of revisarAvance(suyas, nino.fechaNacimiento)) {
        marcados.push(`${nino.nombre} ${nino.id} ${nucleo}`);
      }
    }
    expect(marcados).toEqual(['Josefa NINO-00001 LV']);
  });

  it('el nivel general de Josefa es la mediana de sus núcleos con evidencia', () => {
    const josefa = semilla.ninos.find((n) => n.id === 'NINO-00001')!;
    const suyas = evaluacionesDe(evaluaciones, josefa.id);
    const porNucleo = nivelActualPorNucleo(suyas);
    expect(porNucleo.LV).toBe(2);
    expect(porNucleo.CM).toBe(4);
    // Niveles con evidencia: 4, 4, 4, 4 y 2 → mediana 4.
    expect(nivelGeneral(porNucleo)).toBe(4);
    expect(frescura(suyas, HOY)).toBe('verde');
    expect(revisarAvance(suyas, josefa.fechaNacimiento)).toEqual(['LV']);
  });

  it('el resumen de la sala Medio Menor A cuadra con la semilla', () => {
    const ninos = semilla.ninos.filter((n) => n.salaId === 'SALA-MMA');
    const resumen = resumenSala(ninos, evaluaciones, HOY);
    expect(resumen.total).toBe(18);
    expect(resumen.observadosMes).toBe(16);
    expect(resumen.nucleoMenosCubierto).toBe('CC');
  });
});
