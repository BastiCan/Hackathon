import { describe, expect, it } from 'vitest';
import semillaJson from '@data/semilla.json';
import { evaluacionesDe, evaluacionesValidadas, resumenSala } from './evaluacion';
import type { EvaluacionValidada, Nino, Semilla } from './tipos';
import {
  conteosFiltro,
  cuando,
  etiquetaFormato,
  etiquetaTarjeta,
  fechaCorta,
  fechaLarga,
  filtrarTarjetas,
  iniciales,
  inicialesUsuaria,
  nucleosDeFicha,
  ordenarNucleosFicha,
  partesResumenSala,
  resumenFicha,
  tarjetaSala,
  tarjetasDeSala,
  textoCerteza,
  textoResumenSala,
} from './vistas';

const semilla = semillaJson as unknown as Semilla;
const HOY = semilla.fechaDemo; // 2026-10-15
const SALA = 'SALA-MMA';

const ninosSala = semilla.ninos.filter((n) => n.salaId === SALA && n.activo);
const evaluaciones = evaluacionesValidadas(
  semilla.sugerencias.filter((s) => s.salaId === SALA),
  semilla.evidencias.filter((e) => e.salaId === SALA),
);

function nino(parcial: Partial<Nino> = {}): Nino {
  return {
    id: 'NINO-X',
    nombre: 'Prueba',
    apellidoInicial: 'X.',
    fechaNacimiento: '2023-10-15',
    salaId: SALA,
    activo: true,
    ...parcial,
  };
}

function evaluacion(parcial: Partial<EvaluacionValidada> = {}): EvaluacionValidada {
  return {
    sugerenciaId: 'SUG-X',
    evidenciaId: 'EVI-X',
    ninoId: 'NINO-X',
    salaId: SALA,
    nucleo: 'LV',
    nivel: 4,
    fecha: HOY,
    cita: 'Dijo una oración completa.',
    validadaPor: 'USR-ANA',
    ...parcial,
  };
}

describe('iniciales', () => {
  it('toma las dos primeras letras del nombre de pila', () => {
    expect(iniciales('Josefa')).toBe('JO');
    expect(iniciales('Emilio')).toBe('EM');
  });

  it('para las usuarias toma una letra por palabra', () => {
    expect(inicialesUsuaria('Tía Ana')).toBe('TA');
    expect(inicialesUsuaria('Directora Carmen')).toBe('DC');
  });
});

describe('fechas', () => {
  it('escribe la fecha corta y la larga', () => {
    expect(fechaCorta('2026-10-13')).toBe('13 oct');
    expect(fechaCorta('2026-09-06T11:05:00')).toBe('6 sep');
    expect(fechaLarga('2026-10-15')).toBe('Jueves 15 de octubre');
  });

  it('dice Hoy, Ayer o la fecha', () => {
    expect(cuando('2026-10-15T09:12:00', HOY)).toBe('Hoy, 09:12');
    expect(cuando('2026-10-14T15:20:00', HOY)).toBe('Ayer, 15:20');
    expect(cuando('2026-10-01T08:00:00', HOY)).toBe('1 oct, 08:00');
  });
});

describe('textos de la interfaz', () => {
  it('nombra el formato de la evidencia', () => {
    expect(etiquetaFormato('foto')).toBe('Foto de post-it');
    expect(etiquetaFormato('audio')).toBe('Audio');
    expect(etiquetaFormato('texto')).toBe('Nota escrita');
  });

  it('dice la certeza en palabras, nunca en porcentajes', () => {
    expect(textoCerteza('alta')).toBe('Alta');
    expect(textoCerteza('media')).toBe('Media');
    expect(textoCerteza('baja')).toBe('Baja');
  });
});

describe('tarjetas de la sala', () => {
  const tarjetas = tarjetasDeSala(ninosSala, evaluaciones, HOY);

  it('arma una tarjeta por niño/a activo de la sala', () => {
    expect(tarjetas).toHaveLength(18);
    expect(tarjetas.every((t) => t.iniciales.length === 2)).toBe(true);
  });

  it('marca a Josefa con bandera y nivel general 4 (reglas de la rúbrica)', () => {
    const josefa = tarjetas.find((t) => t.id === 'NINO-00001');
    expect(josefa?.nombre).toBe('Josefa');
    expect(josefa?.revisarAvance).toBe(true);
    expect(josefa?.nivelGeneral).toBe(4);
    expect(tarjetas.filter((t) => t.revisarAvance)).toHaveLength(1);
  });

  it('cuenta los filtros y filtra', () => {
    const conteos = conteosFiltro(tarjetas);
    expect(conteos.todos).toBe(18);
    expect(conteos.revisarAvance).toBe(1);
    expect(conteos.sinRegistro).toBe(
      tarjetas.filter((t) => t.frescura === 'rojo').length,
    );
    expect(filtrarTarjetas(tarjetas, 'revisar-avance')).toHaveLength(1);
    expect(filtrarTarjetas(tarjetas, 'todos')).toHaveLength(18);
    expect(filtrarTarjetas(tarjetas, 'sin-registro').every((t) => t.frescura === 'rojo')).toBe(
      true,
    );
  });

  it('describe la tarjeta para quien usa lector de pantalla', () => {
    const sinRegistro = tarjetasDeSala([nino()], [], HOY)[0];
    expect(etiquetaTarjeta(sinRegistro)).toBe('Prueba, sin nivel todavía, sin registros');

    const conRegistro = tarjetasDeSala([nino()], [evaluacion({ fecha: '2026-10-14' })], HOY)[0];
    expect(etiquetaTarjeta(conRegistro)).toBe('Prueba, nivel 4, 1 día desde el último registro');
  });
});

describe('resumen de la sala', () => {
  it('usa los textos del prototipo', () => {
    const texto = textoResumenSala(resumenSala(ninosSala, evaluaciones, HOY));
    expect(texto).toContain('Observados en 30 días: 16 de 18');
    expect(texto).toContain('Menos registrado:');
  });

  it('separa las dos partes que van en negrita', () => {
    const partes = partesResumenSala(resumenSala(ninosSala, evaluaciones, HOY));
    expect(partes.observados).toBe('16 de 18');
    expect(partes.menos.length).toBeGreaterThan(0);
  });
});

describe('tarjeta de sala (vista directora)', () => {
  const sala = { id: SALA, nombre: 'Medio Menor A' };

  it('cuenta los observados de los últimos 30 días y los de revisar avance', () => {
    const t = tarjetaSala(sala, ninosSala, evaluaciones, HOY, 'EN');
    expect(t.total).toBe(18);
    // 2 de los 18 llevan más de 30 días sin registro (aro rojo).
    expect(t.observados30).toBe(16);
    expect(t.porcentaje).toBe(89);
    expect(t.revisarAvance).toBe(1);
    expect(t.nombreNucleoMenosCubierto).toBe('Exploración del Entorno Natural');
  });

  it('no divide por cero en una sala vacía', () => {
    const t = tarjetaSala(sala, [], [], HOY, null);
    expect(t.total).toBe(0);
    expect(t.porcentaje).toBe(0);
    expect(t.nombreNucleoMenosCubierto).toBeNull();
  });
});

describe('ficha', () => {
  const josefa = semilla.ninos.find((n) => n.id === 'NINO-00001')!;
  const suyas = evaluacionesDe(evaluaciones, josefa.id);
  const nucleos = nucleosDeFicha(suyas, josefa.fechaNacimiento);

  it('muestra los 8 núcleos con su nivel o sin registros', () => {
    expect(nucleos).toHaveLength(8);
    const lv = nucleos.find((n) => n.nucleo === 'LV');
    expect(lv?.nivel).toBe(2);
    expect(lv?.nombreNivel).toBe('Explorando');
    expect(lv?.revisarAvance).toBe(true);
    expect(nucleos.filter((n) => n.revisarAvance)).toHaveLength(1);
  });

  it('escribe el resumen por plantilla, sin lenguaje clínico', () => {
    const texto = resumenFicha(josefa.nombre, nucleos, { nucleo: 'CC', nivel: 5, conductas: [] });
    expect(texto).toContain('Avanza bien en');
    expect(texto.toLowerCase()).not.toContain('rezago');
  });

  it('si hay un núcleo en revisar avance, el resumen lo nombra primero', () => {
    const texto = resumenFicha(josefa.nombre, nucleos, { nucleo: 'CC', nivel: 5, conductas: [] });
    expect(texto).toContain('Conviene acompañar de cerca Lenguaje Verbal');
    expect(texto).not.toContain('Avanza bien en Lenguaje Verbal');
  });

  it('sin núcleos marcados, sugiere el núcleo por observar', () => {
    const sinMarca = nucleos.map((n) => ({ ...n, revisarAvance: false }));
    const texto = resumenFicha(josefa.nombre, sinMarca, { nucleo: 'PM', nivel: 4, conductas: [] });
    expect(texto).toContain('Conviene observar más Pensamiento Matemático');
  });

  it('ordena Cómo va: marcados, con registros y luego sin registros', () => {
    const orden = ordenarNucleosFicha(nucleos);
    expect(orden[0].nucleo).toBe('LV');
    const primeraSinRegistro = orden.findIndex((n) => n.nivel === null);
    if (primeraSinRegistro >= 0) {
      expect(orden.slice(primeraSinRegistro).every((n) => n.nivel === null)).toBe(true);
    }
    expect(orden).toHaveLength(8);
  });

  it('invita a registrar cuando no hay evidencia', () => {
    const vacios = nucleosDeFicha([], '2023-10-15');
    expect(resumenFicha('Prueba', vacios, null)).toContain('Todavía no hay registros');
  });
});
