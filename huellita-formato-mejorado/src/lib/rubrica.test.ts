import { describe, expect, it } from 'vitest';
import {
  celda,
  codigosNucleos,
  colorNivel,
  conductas,
  niveles,
  nivelMaximo,
  nivelSiguiente,
  nombreNivel,
  nombreNucleo,
  nucleos,
  siglaNucleo,
} from './rubrica';

describe('rubrica', () => {
  it('carga los 9 niveles del dataset E-1 con sus nombres y rangos de edad', () => {
    expect(niveles()).toHaveLength(9);
    expect(nombreNivel(1)).toBe('Atención y regulación inicial');
    expect(nombreNivel(9)).toBe('Secuencias y autonomía creciente');
    expect(niveles()[0]).toMatchObject({ edadMinMeses: 0, edadMaxMeses: 2 });
    expect(niveles()[8]).toMatchObject({
      edadMinMeses: 27,
      edadMaxMeses: 36,
      edadOrientativa: '27–36 meses',
    });
    expect(nivelMaximo()).toBe(9);
  });

  it('carga los 5 dominios como núcleos, en el orden de los datos', () => {
    expect(codigosNucleos()).toEqual([
      'motor_grueso',
      'motor_fino',
      'lenguaje_comunicacion',
      'socioemocional',
      'cognitivo',
    ]);
    expect(nucleos()).toHaveLength(5);
    expect(nombreNucleo('lenguaje_comunicacion')).toBe('Lenguaje y comunicación');
    // La sigla sale del código del núcleo (MG, MF, LC, SE, CO).
    expect(nucleos().map((n) => n.sigla)).toEqual(['MG', 'MF', 'LC', 'SE', 'CO']);
    expect(siglaNucleo('cognitivo')).toBe('CO');
  });

  it('entrega descripción y 2 conductas observables por celda', () => {
    for (const nucleo of codigosNucleos()) {
      for (const { nivel } of niveles()) {
        const c = celda(nucleo, nivel);
        expect(c.descripcionNivel.length).toBeGreaterThan(0);
        expect(conductas(nucleo, nivel)).toHaveLength(2);
        expect(c.nivel).toBe(nivel);
      }
    }
  });

  it('las conductas son las manifestaciones del dataset', () => {
    expect(conductas('cognitivo', 9)).toContain(
      'Clasifica objetos por una característica visible, como forma, color o tamaño, después de una consigna simple.',
    );
  });

  it('el nivel siguiente se detiene en el 9', () => {
    expect(nivelSiguiente(8)).toBe(9);
    expect(nivelSiguiente(9)).toBe(9);
  });

  it('usa un color distinto por nivel, del cálido al azul oscuro', () => {
    expect(colorNivel(1)).toBe('#EF7A6A');
    expect(colorNivel(4)).toBe('#B7D351');
    expect(colorNivel(8)).toBe('#2F6BC4');
    expect(colorNivel(9)).toBe('#233F86');
    expect(new Set(niveles().map((n) => colorNivel(n.nivel))).size).toBe(9);
  });
});
