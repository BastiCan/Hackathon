import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath, URL } from 'node:url';
import { describe, expect, it } from 'vitest';
import rubricaJson from '@data/rubrica_e1.json';
import { colorTextoNivel } from '../components/colores';
import {
  celda,
  codigosNucleos,
  colorNivel,
  conductas,
  descripcionNivel,
  nivelMaximo,
  niveles,
  nivelSiguiente,
  nombreNivel,
  nombreNucleo,
  nucleos,
  siglaNucleo,
  todasLasCeldas,
} from './rubrica';

/** Contraste WCAG entre dos colores `#RRGGBB`. */
function contraste(a: string, b: string): number {
  const luminancia = (hex: string) => {
    const n = Number.parseInt(hex.slice(1), 16);
    const lineal = (c: number) => {
      const v = c / 255;
      return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
    };
    return (
      0.2126 * lineal((n >> 16) & 255) + 0.7152 * lineal((n >> 8) & 255) + 0.0722 * lineal(n & 255)
    );
  };
  const [x, y] = [luminancia(a), luminancia(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
}

const RUBRICA_BACKEND = fileURLToPath(
  new URL('../../../integra-backend/data/processed/rubrica.json', import.meta.url),
);

describe('rúbrica E-1 (la misma del backend)', () => {
  it('carga los 9 niveles con su nombre, descripción y rango de edad', () => {
    expect(niveles()).toHaveLength(9);
    expect(nombreNivel(1)).toBe('Atención y regulación inicial');
    expect(nombreNivel(6)).toBe('Autonomía funcional inicial');
    expect(nombreNivel(9)).toBe('Secuencias y autonomía creciente');
    expect(descripcionNivel(9).length).toBeGreaterThan(0);
    expect(niveles()[8]).toMatchObject({
      edadMinMeses: 27,
      edadMaxMeses: 36,
      edadOrientativa: '27–36 meses',
    });
    expect(nivelMaximo()).toBe(9);
    expect(nivelSiguiente(8)).toBe(9);
    expect(nivelSiguiente(9)).toBe(9);
  });

  it('carga los 5 núcleos como configuración, en el orden del backend', () => {
    expect(codigosNucleos()).toEqual([
      'motor_grueso',
      'motor_fino',
      'lenguaje_comunicacion',
      'socioemocional',
      'cognitivo',
    ]);
    expect(nucleos().map((n) => n.sigla)).toEqual(['MG', 'MF', 'LC', 'SE', 'CO']);
    expect(nombreNucleo('lenguaje_comunicacion')).toBe('Lenguaje y comunicación');
    expect(siglaNucleo('cognitivo')).toBe('CO');
  });

  it('cada celda trae sus 2 conductas observables con el código del backend', () => {
    expect(todasLasCeldas()).toHaveLength(45);
    let total = 0;
    for (const nucleo of codigosNucleos()) {
      for (const { nivel } of niveles()) {
        const c = celda(nucleo, nivel);
        expect(c.nivel).toBe(nivel);
        expect(conductas(nucleo, nivel)).toHaveLength(2);
        // La sigla del núcleo es la de sus códigos: MAN-L09-MG-01 → MG.
        for (const m of c.manifestaciones) {
          expect(m.id).toMatch(new RegExp(`^MAN-L0${nivel}-${siglaNucleo(nucleo)}-0\\d$`));
        }
        total += c.manifestaciones.length;
      }
    }
    expect(total).toBe(90);
  });

  it('usa un color distinto por nivel y cada uno cumple AA con su texto', () => {
    const colores = niveles().map((n) => colorNivel(n.nivel));
    expect(new Set(colores).size).toBe(9);
    for (const { nivel } of niveles()) {
      expect(contraste(colorNivel(nivel), colorTextoNivel(nivel))).toBeGreaterThanOrEqual(4.5);
    }
  });

  it.skipIf(!existsSync(RUBRICA_BACKEND))('es copia exacta de la rúbrica del backend', () => {
    // Si el backend cambia la rúbrica, esta prueba avisa que hay que volver a copiarla.
    expect(JSON.parse(readFileSync(RUBRICA_BACKEND, 'utf8'))).toEqual(rubricaJson);
  });
});
