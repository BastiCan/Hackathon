/** @type {import('tailwindcss').Config} */
/*
 * Tokens del diseño "agenda institucional" (`.kiro/steering/diseno-visual.md`):
 * una sola familia tipográfica (Roboto), el azul de Integra para la institución
 * y las acciones, y los otros tres colores del logo de Integra para los ámbitos
 * de las Bases Curriculares.
 */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        tinta: {
          DEFAULT: '#1B2A44',
          2: '#4E5B70',
          3: '#8A93A6',
        },
        fondo: '#F4F7FC',
        papel: '#FFFFFF',
        cuadricula: '#E6EBF2',
        linea: '#DCE3EF',
        integra: {
          DEFAULT: '#1F4E9A',
          claro: '#E8EEF8',
          oscuro: '#163A75',
        },
        // Los 4 colores del logo de Integra (franja superior y ámbitos).
        logo: {
          rojo: '#E5432F',
          amarillo: '#F5B800',
          azul: '#1F4E9A',
          verde: '#4C9A2A',
        },
        // Ámbitos de las BCEP: fondo suave + texto oscuro del mismo color (AA).
        ambito: {
          dps: '#FDE7E3',
          'dps-texto': '#9A2414',
          com: '#FFF3C4',
          'com-texto': '#6B4A00',
          ent: '#E3F2DA',
          'ent-texto': '#2E5A12',
        },
        // Avisos: amarillo del logo, suavizado.
        aviso: {
          fondo: '#FFF8DC',
          borde: '#F5B800',
          globo: '#C83B3B',
        },
        // Solo en el punto de frescura y la leyenda.
        frescura: {
          verde: '#2E9E5B',
          amarillo: '#E0A800',
          rojo: '#D64545',
        },
        // Bandera de "revisar avance".
        ambar: '#B86E00',
        // Botón Confirmar: verde del logo oscurecido para texto blanco AA.
        guardar: '#2F7A1E',
        // Botón de grabar: rojo del logo oscurecido para texto blanco AA.
        grabar: '#C8341F',
      },
      fontFamily: {
        // Una sola familia en toda la app (como los sistemas del Estado).
        texto: ['Roboto', 'system-ui', 'sans-serif'],
        display: ['Roboto', 'system-ui', 'sans-serif'],
        // Rótulos pequeños en mayúscula (encabezados de sección).
        rotulo: ['"Roboto Condensed"', 'Roboto', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        tarjeta: '6px',
        hoja: '14px',
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
          '50%': { boxShadow: '0 0 0 14px rgba(200, 52, 31, 0.15)' },
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
