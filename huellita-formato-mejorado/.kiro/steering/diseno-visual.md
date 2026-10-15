---
inclusion: always
---

# Diseño visual (UX/UI) · formato mejorado: agenda institucional

El formato mejorado reemplaza al diseño anterior de post-its sobre cuaderno (`.kiro/diseno/prototipo.html` queda solo como referencia histórica: **no seguirlo**). La referencia actual es la app misma y la maqueta `maqueta-postits-reales.html` del equipo.

## Idea
Huellita se ve como **un sistema del Estado hecho para la agenda de la tía**: sobrio, claro y con el sello de Integra, sin adornos de "app genérica". Se parece a lo que la tía ya usa: una **agenda del día**, una **planilla de la sala** (como el libro de registro) y una **bandeja de registros numerados**.

## Lo que NO se hace
- Nada de letra manuscrita imitada, notas giradas, cinta adhesiva ni fondo de cuaderno.
- Nada de esquinas muy redondeadas, sombras grandes, degradados ni emojis.
- Nada de frases "simpáticas" ("¡Todo al día!", "Huellita ya las ordenó"): tono institucional y cálido.
- Nunca inventar la imagen de un post-it: si hay foto, se muestra **la foto real**, derecha; si no, la nota se muestra como texto.

## Tokens (`tailwind.config.js`)
| Token | Valor | Uso |
|---|---|---|
| tinta | `#1B2A44` / 2 `#4E5B70` / 3 `#8A93A6` | Texto |
| fondo | `#F4F7FC` | Fondo de la app |
| linea | `#DCE3EF` | Bordes y separadores |
| integra | `#1F4E9A` | Institución, navegación, acciones principales |
| logo | rojo `#E5432F`, amarillo `#F5B800`, azul `#1F4E9A`, verde `#4C9A2A` | Franja superior y ámbitos |
| ámbitos | DPS rojo · Comunicación amarillo · Entorno verde (fondo suave + texto oscuro) | Etiquetas de núcleo, números de nivel, puntos de la semana |
| aviso | fondo `#FFF8DC`, borde `#F5B800` | Avisos con borde izquierdo |
| guardar | `#2F7A1E` | Botón Confirmar |
| grabar | `#C8341F` | Botón Grabar |
| frescura | verde, amarillo, rojo | **Solo** el punto junto a la fecha del último registro |
| ámbar | `#B86E00` | **Solo** la bandera y el nivel en "revisar avance" |

Radio de tarjetas: 6 px; hojas inferiores: 14 px. Bordes de 1 px.

## Tipografía
**Una sola familia: Roboto** (400, 500 y 700), autoalojada con `@fontsource/roboto`. Rótulos de sección en **Roboto Condensed** 500, mayúscula pequeña (`.rotulo`). Si el equipo consigue la tipografía oficial **gobCL** (kitdigital.gob.cl), se cambia solo en `tailwind.config.js` y `main.tsx`.

## Estructura
- **Encabezado institucional** en todas las pantallas: franja azul con el sello "Gobierno de Chile · INTEGRA" y la usuaria con su cargo (abre el menú), más la franja de 4 colores del logo. En producción, el sello se reemplaza por los logos oficiales.
- **Navegación inferior**: Agenda · Sala · Revisar (+ Directora para la directora).
- **Barra de captura** (Agenda y ficha): Foto · **Grabar** (rojo, al centro) · Escribir.

## Pantallas
1. **Agenda** (`/`): rótulo "Agenda · sala", fecha larga y "Hoy"; semana de lunes a viernes con puntos de colores por ámbito; aviso "N por revisar"; próximo registro IEA y observados en 30 días; el día por **períodos de la jornada** (`lib/agenda.ts`), cada registro con miniatura (foto real o tipo de nota), nombre, hora, autora, texto (2 líneas), etiqueta del núcleo, nivel y "Por revisar".
2. **Sala** (`/sala`): planilla con una fila por niño/a ("Josefa P."), una columna por núcleo (IA, CC, CM, LV, LA, EN, ES, PM) con el número de nivel en el color de su ámbito (ámbar si está en revisar avance), y la columna "Último" con punto de frescura. Filtros, leyenda de ámbitos y resumen.
3. **Revisar** (`/revisar`): cada registro es una tarjeta con N.º de registro, origen, **la foto del post-it** (se amplía al tocarla), "Huellita leyó" y una ficha (Niño/a, Núcleo, Nivel, Conducta, Confianza: Alta/Media/Baja con explicación). Botones **Confirmar** (verde), **Corregir** y **Descartar**.
4. **Ficha** (`/nino/:id`): aviso con el resumen y "Para observar esta semana"; "Cómo va · por ámbito" con los 8 núcleos agrupados y su nivel; "Su agenda": tira con las fotos de sus registros; historial.
5. **Directora** (`/directora`): tarjetas por sala; la sala se abre como planilla en modo lectura.

## Calidad
Diseñar a 375–390 px; en escritorio, columna de 480 px (directora hasta 1100 px). Áreas táctiles de 44 px o más, foco visible de 3 px azul y `prefers-reduced-motion`.
