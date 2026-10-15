---
inclusion: always
---

# Diseño visual (UX/UI) · formato mejorado: agenda institucional

El formato mejorado reemplaza al diseño anterior de post-its sobre cuaderno (`.kiro/diseno/prototipo.html` queda solo como referencia histórica: **no seguirlo**). La referencia actual es la app misma y la maqueta `maqueta-postits-reales.html` del equipo.

## Idea
Huellita se ve como **un sistema del Estado hecho para la tía**: sobrio, claro y con el sello de Integra, sin adornos de "app genérica". Se parece a lo que la tía ya usa: un **inicio** para registrar al tiro, una **planilla de la sala** (como el libro de registro) y una **bandeja de registros numerados**.

## Lo que NO se hace
- Nada de letra manuscrita imitada, notas giradas, cinta adhesiva ni fondo de cuaderno.
- Nada de esquinas muy redondeadas, sombras grandes, degradados ni emojis.
- Nada de frases "simpáticas" ("¡Todo al día!", "Huellita ya las ordenó"): tono institucional y cálido.
- Nunca inventar la imagen de un post-it: si hay foto, se muestra **la foto real**, derecha; si no, la nota se muestra como texto.

## Tokens (`tailwind.config.js`) · manual de imagen corporativa Integra 2019
Colores oficiales del manual (versión RGB para pantallas) más rosado y naranjo, tomados de las "manchas" de la gráfica institucional.

| Token | Valor | Uso |
|---|---|---|
| tinta | `#22262E` / 2 `#58585A` (gris 80% del manual) | Texto |
| fondo | `#F5F8FC` | Fondo de la app |
| integra | azul Pantone 300C `#0063BD` | Institución, navegación, acciones principales, día seleccionado |
| logo | rojo 485C `#DD271D`, amarillo 116C `#FFCD07`, azul 300C `#0063BD`, verde 368C `#67BC27` | Franja superior |
| niveles | 9 colores, del cálido (1) al azul oscuro (9), en `src/lib/rubrica.ts` (ver `interfaz.md`) | **Solo** números, etiquetas y puntos de nivel |
| núcleo | azul claro `integra-claro` con texto `integra-oscuro` | Etiquetas de núcleo (el color queda para el nivel) |
| rosado | `#E43C84` (suave `#FBE1EC`) | Acento cálido: "Hoy", notas/fotos, ítem activo |
| naranjo | `#F07818` (suave `#FDE7D3`, texto oscuro AA) | "Por revisar" y "revisar avance" |
| guardar | `#437A19` | Botón Confirmar |
| grabar | `#C41F15` | Botón Grabar |
| frescura | verde, amarillo, rojo | **Solo** el punto junto a la fecha del último registro |

Radio de tarjetas: 16 px; hojas inferiores: 20 px; sombra suave `shadow-tarjeta`.

**Manchas** (`src/components/Mancha.tsx`): formas orgánicas planas de la gráfica institucional. Solo adorno (`aria-hidden`, sin toques), en esquinas de tarjetas, del día de hoy y de los chips de nivel; nunca llevan información ni tapan texto.

## Tipografía
**Una sola familia: Carlito** (400 y 700), autoalojada con `@fontsource/carlito`. Es el equivalente libre y métricamente idéntico de **Calibri**, la tipografía institucional del manual (respaldo: Calibri, Trebuchet MS). No se usan Kids ni Claire Hand (manuscritas): la app no lleva letra a mano.

## Estructura
- **Encabezado institucional** en todas las pantallas: barra **blanca** (borde inferior `linea`, alto mínimo 56 px) con el **logo oficial** `src/assets/marca/logo-mineduc-integra.png` (Ministerio de Educación · Gobierno de Chile e Integra) a la izquierda —alto 36 px en celular y 44 px desde `sm`, ancho automático, nunca deformado ni recortado— y a la derecha la usuaria con su cargo (abre el menú). Debajo, la franja de 4 colores del logo. El logo **nunca va sobre el azul de Integra** (su fondo es blanco); si no cabe junto al nombre a 360 px, se esconde el cargo antes que achicar el logo.
- **Navegación inferior**: Inicio · Sala · Revisar (+ Directora para la directora).
- **Captura**: Subir foto · **Grabar audio** (rojo) · Escribir · Subir audio. En Inicio van como 4 tarjetas grandes (2 × 2 en celular, en fila en escritorio); en la ficha, en la barra de captura (celular) o en el bloque "Registrar" de la barra lateral (escritorio). Nunca dos veces en la misma pantalla.

## Pantallas
1. **Inicio** (`/`): rótulo "Inicio · sala", fecha larga y "Hoy"; semana de lunes a viernes con un punto por registro (azul revisado, naranjo por revisar); aviso "N por revisar"; próximo registro IEA y observados en 30 días; "Registrar en [sala]" con el selector de sala y los 4 botones de captura (`lib/inicio.ts`).
2. **Sala** (`/sala`): planilla con una fila por niño/a ("Josefa P."), una columna por núcleo (MG, MF, LC, SE, CO) con el número de nivel **en el color de su nivel** (aro naranjo si está en revisar avance), y la columna "Último" con punto de frescura. Filtros, leyenda de los 9 niveles y resumen.
3. **Revisar** (`/revisar`): cada registro es una tarjeta con N.º de registro, origen, **la foto del post-it** (se amplía al tocarla), "Huellita leyó" y una ficha (Niño/a, Núcleo, Nivel, Conducta, Confianza: Alta/Media/Baja con explicación). Botones **Confirmar** (verde), **Corregir** y **Descartar**.
4. **Ficha** (`/nino/:id`): aviso con el resumen y "Para observar esta semana"; "Cómo va · por núcleo" con los 5 núcleos y su nivel en su color; "Últimos registros": tira con las fotos de sus registros; historial (el punto de cada registro en el color de su nivel).
5. **Directora** (`/directora`): tarjetas por sala; la sala se abre como planilla en modo lectura.

## Adaptable: celular y escritorio

Misma app, mismos componentes y datos: solo cambian clases responsivas.

- **Celular (< 1024 px):** manda lo descrito arriba. Columna de 480 px, barra
  inferior fija, barra de captura sobre ella y hojas que suben desde abajo.
- **Tablet (768–1023 px):** el mismo diseño de celular, hasta 640 px de ancho y
  sin barra lateral.
- **Computador (desde 1024 px, prefijo `lg:`):**
  - encabezado a todo el ancho de la ventana con su contenido centrado hasta
    1280 px; debajo, **barra lateral** de 232 px y contenido hasta 1000 px con
    24–32 px de aire;
  - la barra lateral (`src/app/NavegacionLateral.tsx`) lleva, en la ficha, el
    bloque **Registrar** (los 4 botones de captura) y después los destinos; el
    actual va en azul oficial sobre azul claro con la manchita rosada;
  - **no hay barras fijas abajo**: `BarraInferior` y `Dock` llevan `lg:hidden` y
    el hueco que reservaban desaparece;
  - Inicio en dos columnas (semana y botones para registrar / pendientes y
    resumen); planilla de la sala a todo el ancho y sin truncar nombres; Revisar
    en 2 columnas con la foto del post-it más grande; ficha en dos columnas
    (resumen y núcleos / últimos registros e historial); directora en 3
    columnas; Entrada como tarjeta centrada de 560 px;
  - las **hojas inferiores** se muestran como diálogo centrado de 520 px con las
    4 esquinas redondeadas, y los **avisos** abajo a la derecha (380 px).
- Los destinos de navegación salen de una sola lista (`src/app/destinos.ts`):
  nunca se duplican entre la barra inferior y la lateral.
- Nada de pantallas ni lógica duplicadas, y **nada de scroll horizontal** entre
  320 y 1440 px: `min-w-0` en el contenido, `overflow-x-auto` solo dentro de la
  planilla, imágenes con `max-w-full`.
- Zonas seguras del iPhone (`env(safe-area-inset-bottom)`) y alto de ventana con
  respaldo (`100vh` y luego `100dvh`) en `src/estilos.css`.
- La app puede servirse desde una subcarpeta: se compila con
  `BASE_URL=/Hackathon/ npm run build` (el router toma `import.meta.env.BASE_URL`).

## Calidad
Diseñar a 375–390 px; en escritorio, barra lateral de 232 px y contenido hasta
1000 px (la vista directora dentro del mismo marco). Áreas táctiles de 44 px o
más, foco visible de 3 px azul y `prefers-reduced-motion`.
