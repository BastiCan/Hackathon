/** @type {import('tailwindcss').Config} */
/*
 * Tokens de `.kiro/steering/diseno-visual.md`, que son los mismos del
 * prototipo `.kiro/diseno/prototipo.html` (fuente de verdad visual).
 */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Texto: azul tinta de lápiz pasta.
        tinta: {
          DEFAULT: '#1E2A55',
          2: '#56618A',
          3: '#8A93B2',
        },
        fondo: '#F3F6FB',
        papel: '#FFFFFF',
        cuadricula: '#E2E8F4',
        linea: '#DCE3EF',
        integra: {
          DEFAULT: '#1F4E9A',
          claro: '#E7EEFA',
          oscuro: '#163A75',
        },
        // Solo para notas originales, la pila de pendientes y "Para observar".
        postit: {
          amarillo: '#FFE873',
          rosa: '#FFB8D2',
          lima: '#D6F27C',
        },
        // Solo en el aro del avatar y la leyenda.
        frescura: {
          verde: '#2E9E5B',
          amarillo: '#E0A800',
          rojo: '#D64545',
        },
        // Solo en la bandera de "revisar avance".
        ambar: '#B86E00',
        /*
         * Dos tonos un punto más oscuros que los del prototipo, necesarios para
         * que el texto blanco encima llegue al contraste AA (tarea 10):
         * `guardar` es el verde del botón Guardar (frescura verde da 3,4:1) y
         * `aviso` el rojo del globo con el número de pendientes.
         * Los colores de frescura siguen intactos en el aro y la leyenda.
         */
        guardar: '#237A47',
        aviso: '#C83B3B',
        // Solo en chips, números y escaleras de nivel.
        nivel: {
          1: '#E8664F',
          2: '#F08A3E',
          3: '#F2C14E',
          4: '#9BC53D',
          5: '#5A9E3A',
          6: '#3A9E9A',
          7: '#3D7DD8',
          8: '#1F3B6B',
        },
      },
      fontFamily: {
        // Títulos, iniciales de avatares y números de nivel.
        display: ['"Bricolage Grotesque Variable"', '"Bricolage Grotesque"', 'system-ui', 'sans-serif'],
        // Todo el texto de la interfaz.
        texto: ['"Atkinson Hyperlegible"', 'system-ui', 'sans-serif'],
        // Solo texto escrito por la tía (citas, historial, "Para observar").
        mano: ['Kalam', '"Comic Sans MS"', 'cursive'],
      },
      borderRadius: {
        tarjeta: '14px',
        hoja: '24px',
      },
      maxWidth: {
        // Pantallas de la tía; la vista directora puede llegar a 1100 px.
        tia: '480px',
        contenido: '1100px',
      },
      minHeight: {
        tactil: '44px',
      },
      minWidth: {
        tactil: '44px',
      },
      keyframes: {
        sube: {
          from: { transform: 'translateY(30px)', opacity: '0.4' },
          to: { transform: 'none', opacity: '1' },
        },
        late: {
          '50%': { boxShadow: '0 0 0 14px rgba(214, 69, 69, 0.15)' },
        },
      },
      animation: {
        sube: 'sube 0.22s ease-out',
        late: 'late 1.2s ease-in-out infinite',
      },
    },
  },
  plugins: [],
};
