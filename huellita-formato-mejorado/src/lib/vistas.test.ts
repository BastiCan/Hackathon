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
const SALA = 'SG-A';

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
    nucleo: 'lenguaje_comunicacion',
    nivel: 4,
    fecha: HOY,
    cita: 'Dijo una oración completa.',
    validadaPor: 'EDU-0001',
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
    expect(cuando('2026-10-14T15:20:00-03:00', HOY)).toBe('Ayer, 15:20');
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
    expect(tarjetas).toHaveLength(13);
    expect(tarjetas.every((t) => t.iniciales.length === 2)).toBe(true);
  });

  it('calcula el nivel general de Josefa con las reglas de la rúbrica', () => {
    const josefa = tarjetas.find((t) => t.id === 'NINO-00008');
    expect(josefa?.nombre).toBe('Josefa');
    expect(josefa?.nivelGeneral).toBe(5);
    expect(josefa?.revisarAvance).toBe(false);
    expect(tarjetas.filter((t) => t.revisarAvance)).toHaveLength(0);
  });

  it('distingue a los homónimos con la inicial del apellido', () => {
    const martinas = tarjetas.filter((t) => t.nombre === 'Martina').map((t) => t.nombreCorto);
    expect(martinas).toEqual(['Martina M.', 'Martina R.']);
  });

  it('cuenta los filtros y filtra', () => {
    const conteos = conteosFiltro(tarjetas);
    expect(conteos.todos).toBe(13);
    expect(conteos.revisarAvance).toBe(0);
    expect(conteos.sinRegistro).toBe(11);
    expect(filtrarTarjetas(tarjetas, 'revisar-avance')).toHaveLength(0);
    expect(filtrarTarjetas(tarjetas, 'todos')).toHaveLength(13);
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
    expect(texto).toContain('Observados en 30 días: 2 de 13');
    expect(texto).toContain('Menos registrado: Motor grueso');
  });

  it('separa las dos partes que van en negrita', () => {
    const partes = partesResumenSala(resumenSala(ninosSala, evaluaciones, HOY));
    expect(partes.observados).toBe('2 de 13');
    expect(partes.menos).toBe('Motor grueso');
  });
});

describe('tarjeta de sala (vista directora)', () => {
  const sala = { id: SALA, nombre: 'Sala A' };

  it('cuenta los observados de los últimos 30 días y los de revisar avance', () => {
    const t = tarjetaSala(sala, ninosSala, evaluaciones, HOY, 'motor_grueso');
    expect(t.total).toBe(13);
    // Solo 2 de los 13 tienen un registro de hace 30 días o menos.
    expect(t.observados30).toBe(2);
    expect(t.porcentaje).toBe(15);
    expect(t.revisarAvance).toBe(0);
    expect(t.nombreNucleoMenosCubierto).toBe('Motor grueso');
  });

  it('no divide por cero en una sala vacía', () => {
    const t = tarjetaSala(sala, [], [], HOY, null);
    expect(t.total).toBe(0);
    expect(t.porcentaje).toBe(0);
    expect(t.nombreNucleoMenosCubierto).toBeNull();
  });
});

describe('ficha', () => {
  const josefa = semilla.ninos.find((n) => n.id === 'NINO-00008')!;
  const suyas = evaluacionesDe(evaluaciones, josefa.id);
  const nucleos = nucleosDeFicha(suyas, josefa.fechaNacimiento);
  /** La misma ficha con Lenguaje y comunicación en "revisar avance". */
  const conMarca = nucleos.map((n) =>
    n.nucleo === 'lenguaje_comunicacion' ? { ...n, revisarAvance: true } : n,
  );

  it('muestra los 5 núcleos con su nivel o sin registros', () => {
    expect(nucleos).toHaveLength(5);
    const lenguaje = nucleos.find((n) => n.nucleo === 'lenguaje_comunicacion');
    expect(lenguaje?.nivel).toBe(4);
    expect(lenguaje?.nombreNivel).toBe('Sedestación y comunicación intencional');
    expect(nucleos.filter((n) => n.revisarAvance)).toHaveLength(0);
  });

  it('escribe el resumen por plantilla, sin lenguaje clínico', () => {
    const texto = resumenFicha(josefa.nombre, nucleos, {
      nucleo: 'socioemocional',
      nivel: 6,
      conductas: [],
    });
    expect(texto).toContain('Avanza bien en Cognitivo');
    expect(texto.toLowerCase()).not.toContain('rezago');
  });

  it('si hay un núcleo en revisar avance, el resumen lo nombra primero', () => {
    const texto = resumenFicha(josefa.nombre, conMarca, {
      nucleo: 'socioemocional',
      nivel: 6,
      conductas: [],
    });
    expect(texto).toContain('Conviene acompañar de cerca Lenguaje y comunicación');
    expect(texto).not.toContain('Avanza bien en Lenguaje y comunicación');
  });

  it('sin núcleos marcados, sugiere el núcleo por observar', () => {
    const texto = resumenFicha(josefa.nombre, nucleos, { nucleo: 'motor_fino', nivel: 6, conductas: [] });
    expect(texto).toContain('Conviene observar más Motor fino');
  });

  it('ordena Cómo va: marcados, con registros y luego sin registros', () => {
    const orden = ordenarNucleosFicha(conMarca);
    expect(orden[0].nucleo).toBe('lenguaje_comunicacion');
    const primeraSinRegistro = orden.findIndex((n) => n.nivel === null);
    if (primeraSinRegistro >= 0) {
      expect(orden.slice(primeraSinRegistro).every((n) => n.nivel === null)).toBe(true);
    }
    expect(orden).toHaveLength(5);
  });

  it('invita a registrar cuando no hay evidencia', () => {
    const vacios = nucleosDeFicha([], '2023-10-15');
    expect(resumenFicha('Prueba', vacios, null)).toContain('Todavía no hay registros');
  });
});
