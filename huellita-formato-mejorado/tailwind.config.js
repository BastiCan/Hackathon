/** @type {import('tailwindcss').Config} */
/*
 * Tokens del diseño "agenda institucional" con la estética del manual de
 * imagen corporativa de Integra (`.kiro/steering/diseno-visual.md`):
 *
 * - paleta oficial (versión RGB para pantallas): azul Pantone 300C `#0063BD`,
 *   rojo 485C `#DD271D`, amarillo 116C `#FFCD07`, verde 368C `#67BC27` y el
 *   gris 80% `#58585A` de los textos secundarios;
 * - los colores de las "manchas" de la gráfica institucional (rosado y
 *   naranjo), que dan el acento cálido de las tarjetas;
 * - una sola familia tipográfica: Carlito, equivalente libre de Calibri
 *   (la familia que pide el manual), con Trebuchet MS como reemplazo;
 * - esquinas amables (tarjeta 16 px, hoja 20 px, chip 10 px) y sombras cortas.
 *
 * Todos los pares fondo/texto de esta tabla cumplen contraste AA (≥ 4,5:1).
 */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        tinta: {
          DEFAULT: '#22262E',
          // Gris 80% del manual: el color de los textos secundarios.
          2: '#58585A',
          3: '#686F7B',
        },
        fondo: '#F5F8FC',
        papel: '#FFFFFF',
        cuadricula: '#E6EBF2',
        linea: '#DCE3EF',
        // Azul institucional (Pantone 300C).
        integra: {
          DEFAULT: '#0063BD',
          claro: '#E3EFFA',
          oscuro: '#004C91',
        },
        // Los 4 colores oficiales del logo (franja superior y ámbitos).
        logo: {
          rojo: '#DD271D',
          amarillo: '#FFCD07',
          azul: '#0063BD',
          verde: '#67BC27',
        },
        // Ámbitos de las BCEP: fondo suave + texto oscuro del mismo color (AA).
        ambito: {
          dps: '#FDE3E1',
          'dps-texto': '#A01810',
          com: '#FFF3C2',
          'com-texto': '#6B5200',
          ent: '#E6F5DA',
          'ent-texto': '#2B5A0C',
        },
        // Mancha rosada: acento cálido (notas, "Hoy", detalles decorativos).
        rosado: {
          DEFAULT: '#E43C84',
          suave: '#FBE1EC',
          // Para texto y fondos con texto blanco (el rosado pleno no da AA).
          oscuro: '#C01E63',
        },
        // Mancha naranja: "por revisar" y "revisar avance".
        naranjo: {
          DEFAULT: '#F07818',
          suave: '#FDE7D3',
          // Naranjo oscuro para texto e íconos sobre blanco o naranjo suave.
          texto: '#9A4708',
        },
        // Avisos con borde izquierdo: la mancha naranja, suavizada.
        aviso: {
          fondo: '#FDE7D3',
          borde: '#F07818',
          globo: '#C41F15',
        },
        // Solo en el punto de frescura y la leyenda.
        frescura: {
          verde: '#2E9E5B',
          amarillo: '#E0A800',
          rojo: '#D64545',
        },
        // Botón Confirmar: verde oficial oscurecido para texto blanco AA.
        guardar: '#437A19',
        // Botón de grabar: rojo oficial oscurecido para texto blanco AA.
        grabar: '#C41F15',
      },
      fontFamily: {
        // Una sola familia en toda la app. El manual pide Calibri; en web se
        // usa Carlito, su equivalente libre y métricamente idéntico.
        texto: ['Carlito', 'Calibri', '"Trebuchet MS"', 'system-ui', 'sans-serif'],
        display: ['Carlito', 'Calibri', '"Trebuchet MS"', 'system-ui', 'sans-serif'],
        rotulo: ['Carlito', 'Calibri', '"Trebuchet MS"', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        tarjeta: '16px',
        hoja: '20px',
        chip: '10px',
        boton: '12px',
        campo: '10px',
      },
      boxShadow: {
        // Sombras suaves y cortas, nunca pesadas.
        tarjeta: '0 1px 2px rgba(0, 0, 0, 0.06), 0 4px 12px rgba(0, 40, 90, 0.06)',
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
          '50%': { boxShadow: '0 0 0 14px rgba(196, 31, 21, 0.15)' },
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
