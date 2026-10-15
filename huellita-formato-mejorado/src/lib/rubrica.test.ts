import { describe, expect, it } from 'vitest';
import {
  celda,
  codigosNucleos,
  colorNivel,
  conductas,
  descriptor,
  niveles,
  nivelSiguiente,
  nombreNivel,
  nombreNucleo,
  nucleos,
} from './rubrica';

describe('rubrica', () => {
  it('carga los 9 niveles del dataset E-1 con sus nombres y rangos de edad', () => {
    expect(niveles()).toHaveLength(9);
    expect(nombreNivel(1)).toBe('Atención y regulación inicial');
    expect(nombreNivel(9)).toBe('Secuencias y autonomía creciente');
    expect(niveles()[0]).toMatchObject({ edadDesdeMeses: 0, edadHastaMeses: 2 });
    expect(niveles()[8]).toMatchObject({ edadDesdeMeses: 27, edadHastaMeses: 36 });
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
    expect(nucleos().find((n) => n.codigo === 'cognitivo')?.ambito).toBe(
      'Interacción y comprensión del entorno',
    );
  });

  it('entrega descriptor y 2 conductas observables por celda', () => {
    for (const nucleo of codigosNucleos()) {
      for (const { nivel } of niveles()) {
        expect(descriptor(nucleo, nivel).length).toBeGreaterThan(0);
        expect(conductas(nucleo, nivel)).toHaveLength(2);
        expect(celda(nucleo, nivel).nivel).toBe(nivel);
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

  it('usa los colores de nivel de la interfaz y uno oscuro para el 9', () => {
    expect(colorNivel(1)).toBe('#E8664F');
    expect(colorNivel(4)).toBe('#9BC53D');
    expect(colorNivel(8)).toBe('#1F3B6B');
    expect(colorNivel(9)).toBe('#5B3A8E');
    expect(new Set(niveles().map((n) => colorNivel(n.nivel))).size).toBe(9);
  });
});
