---
inclusion: always
---

# Diseño visual (UX/UI): fuente de verdad

**La referencia visual obligatoria es `.kiro/diseno/prototipo.html`.** Ábrelo y léelo completo antes de construir cualquier pantalla. La app en React debe verse y comportarse igual: mismos colores, tipografías, tamaños, espaciados, textos, íconos y orden de los elementos. Si este archivo y `interfaz.md` difieren en algo visual, **gana el prototipo**.

## Idea del diseño
El mundo de la tía: **post-its pegados en un cuaderno cuadriculado**. La evidencia original se muestra como el post-it que la tía escribió (con letra manuscrita), y lo que Huellita entendió aparece como una etiqueta limpia pegada debajo. Así la tía reconoce su propia nota y ve qué hizo la app con ella. Todo lo demás es sobrio, claro y tranquilo.

## Tokens (copiar tal cual como variables CSS o en `tailwind.config.js`)
| Token | Valor | Uso |
|---|---|---|
| tinta | `#1E2A55` | Texto principal (azul tinta de lápiz pasta) |
| tinta-2 | `#56618A` | Texto secundario |
| tinta-3 | `#8A93B2` | Etiquetas y navegación inactiva |
| fondo | `#F3F6FB` | Fondo de la app |
| papel | `#FFFFFF` | Tarjetas |
| cuadricula | `#E2E8F4` | Cuadrícula del cuaderno y escalones vacíos |
| linea | `#DCE3EF` | Bordes |
| integra | `#1F4E9A` / claro `#E7EEFA` / oscuro `#163A75` | Acción principal, avatares |
| post-it | amarillo `#FFE873`, rosa `#FFB8D2`, lima `#D6F27C` | Solo para notas originales, la pila de pendientes y "Para observar" |
| frescura | verde `#2E9E5B`, amarillo `#E0A800`, rojo `#D64545` | **Solo** en el aro del avatar y la leyenda |
| ámbar | `#B86E00` | **Solo** en la bandera de "revisar avance" |
| niveles 1–8 | `#E8664F #F08A3E #F2C14E #9BC53D #5A9E3A #3A9E9A #3D7DD8 #1F3B6B` | **Solo** en chips, números y escaleras de nivel |

Radio de las tarjetas: 14 px. Bordes de 1 px `linea`. Sin sombras, salvo en los post-its (efecto de papel levantado).

## Tipografías (autoalojadas con `@fontsource` para que funcionen sin conexión)
- **Bricolage Grotesque** (600 y 800): títulos, iniciales de los avatares y números de nivel. Con moderación.
- **Atkinson Hyperlegible** (400 y 700): todo el texto de la interfaz. Está diseñada para máxima legibilidad. Base de 16 px; nunca menos de 12 px.
- **Kalam** (400): **solo** para texto escrito por la tía (citas de post-its, historial y la lista "Para observar"). Nunca en botones ni etiquetas.

## Piezas clave (ver el prototipo)
- **Pila de pendientes**: post-it amarillo con dos post-its (rosa y lima) asomando detrás, número grande en Kalam y "notas por revisar". Lleva a Revisar.
- **Tarjeta de niño/a**: avatar de 54 px con iniciales y **aro de color de frescura**, nombre, chip de nivel general "N3" y bandera ámbar arriba a la derecha si corresponde.
- **Dock de captura**: Foto y Texto como círculos de 54 px a los lados, y **Audio al centro como botón de 76 px** azul Integra con halo. Siempre al alcance del pulgar, sobre la barra inferior.
- **Revisar**: fondo de cuaderno cuadriculado (22 px). Cada nota = post-it rotado levemente (entre −1,2° y +1,1°, alternando) con una "cinta adhesiva" y la cita en Kalam, más la tarjeta "lectura" pegada debajo: niño/a, certeza (Segura / Revisar / Poco segura), número de nivel en cuadrado de color, nombre del nivel, núcleo, conducta, y los botones **Guardar** (verde), **Cambiar** y **X**.
- **Ficha**: tarjeta lima "Para observar esta semana"; sección "Cómo va" con cada núcleo como una **escalera de 8 escalones** (como la lámina de la rúbrica de Integra) pintada hasta el nivel actual con su color; historial como línea de tiempo con puntos del color del nivel.
- **Hojas inferiores** (captura, cambiar, leyenda y detalle de núcleo): suben desde abajo con esquinas de 24 px y un asa.
- **Aviso (toast)** oscuro sobre el dock, con "Deshacer" cuando aplica.

## Textos de la interfaz
Usar exactamente los del prototipo. Por ejemplo: "notas por revisar", "Huellita ya las ordenó", "Confirma lo que Huellita leyó de tus notas.", "Aceptar las seguras", "Guardar", "Cambiar", "Guardar en la sala", "Para observar esta semana", "Cómo va", "Registros", "Listo, lo verás en Revisar" y "¡Todo al día!". Tuteo cercano, sin jerga técnica y sin la palabra "IA".

## Calidad
- Diseñar a 375–390 px. En escritorio, centrar con un máximo de 480 px para las pantallas de la tía; la vista Directora puede usar hasta 1100 px.
- Respetar `prefers-reduced-motion`. Foco visible de 3 px azul Integra. Áreas táctiles de al menos 44 px.
