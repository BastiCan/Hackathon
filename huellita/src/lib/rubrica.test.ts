import { describe, expect, it } from 'vitest';
import {
  celda,
  codigosNucleos,
  colorNivel,
  conductas,
  descriptor,
  niveles,
  nombreNivel,
  nombreNucleo,
  nucleos,
} from './rubrica';

describe('rubrica', () => {
  it('carga los 8 niveles con sus nombres y rangos de edad', () => {
    expect(niveles()).toHaveLength(8);
    expect(nombreNivel(1)).toBe('Comenzando');
    expect(nombreNivel(4)).toBe('Afianzando');
    expect(nombreNivel(8)).toBe('Profundizando');
    expect(niveles()[3]).toMatchObject({ edadDesdeMeses: 32, edadHastaMeses: 40 });
  });

  it('carga los núcleos como configuración, en el orden de los datos', () => {
    expect(codigosNucleos()).toEqual(['IA', 'CC', 'CM', 'LV', 'LA', 'EN', 'ES', 'PM']);
    expect(nucleos()).toHaveLength(8);
    expect(nombreNucleo('LV')).toBe('Lenguaje Verbal');
  });

  it('entrega descriptor y conductas observables de cada celda', () => {
    for (const nucleo of codigosNucleos()) {
      for (const { nivel } of niveles()) {
        expect(descriptor(nucleo, nivel).length).toBeGreaterThan(0);
        expect(conductas(nucleo, nivel).length).toBeGreaterThan(0);
        expect(celda(nucleo, nivel).nivel).toBe(nivel);
      }
    }
  });

  it('usa los colores de nivel de la interfaz', () => {
    expect(colorNivel(1)).toBe('#E8664F');
    expect(colorNivel(4)).toBe('#9BC53D');
    expect(colorNivel(8)).toBe('#1F3B6B');
  });
});
