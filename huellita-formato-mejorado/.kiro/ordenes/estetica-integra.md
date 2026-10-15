# Orden: estética según el manual de imagen corporativa de Integra

Trabajas solo en esta carpeta (`huellita-formato-mejorado/`), solo frontend. **Solo cambia lo estético y visual.**

## Reglas duras (no negociables)

- **No cambies la distribución**: mismas pantallas, mismas secciones, mismo orden, mismos textos, mismas rutas, mismos botones y la misma lógica. Nada de mover, agregar ni quitar bloques.
- **No toques el logo** (`src/assets/marca/logo-mineduc-integra.png`, `LogoOficial`, la barra blanca del encabezado) ni la franja de 4 colores bajo él, salvo actualizar sus colores a los oficiales de abajo.
- Nada de letra manuscrita, nada de elementos girados/rotados, nada de degradados chillones ni "glassmorphism". Debe verse institucional, alegre y limpio.
- Accesibilidad: contraste de texto AA (≥ 4.5:1), áreas táctiles ≥ 44 px, nada que dependa solo del color. Las manchas decorativas llevan `aria-hidden="true"` y `pointer-events-none`.
- Privacidad intacta: sin fotos de niños/as; las pruebas de privacidad deben seguir pasando.

## 1. Paleta (actualiza `tailwind.config.js` y comentarios)

Colores oficiales del manual (versión RGB para pantallas):

| Token | Hex | Uso |
|---|---|---|
| azul (Pantone 300C) | `#0063BD` | marca, acciones principales, día seleccionado (reemplaza `integra` `#1F4E9A`; `integra.oscuro` ≈ `#004C91`, `integra.claro` ≈ `#E3EFFA`) |
| rojo (485C) | `#DD271D` | ámbito Desarrollo personal y social |
| amarillo (116C) | `#FFCD07` | ámbito Comunicación integral |
| verde (368C) | `#67BC27` | ámbito Interacción y comprensión del entorno |
| gris 80% | `#58585A` | texto secundario (el manual usa gris 80% para textos) |

Nuevos, tomados de las "manchas" de la gráfica institucional del manual:

| Token | Hex | Uso |
|---|---|---|
| rosado | `#E43C84` | acento cálido: notas/fotos de post-it, indicadores de "Hoy", detalles decorativos |
| rosado suave | `#FBE1EC` | fondos de acento |
| naranjo | `#F07818` | "por revisar" y "revisar avance" (reemplaza el `ambar` `#B86E00` donde sea relleno/borde; para **texto** sobre blanco usa un naranjo oscuro AA, p. ej. `#B4540A`) |
| naranjo suave | `#FDE7D3` | fondo de avisos de revisión |

- Actualiza `logo.*` a los 4 oficiales y los fondos suaves de `ambito.*` para que armonicen (ej. dps `#FDE3E1`/texto `#A01810`, com `#FFF3C2`/texto `#6B5200`, ent `#E6F5DA`/texto `#2B5A0C`). Revisa contraste AA de cada par.
- Recalcula `guardar` y `grabar` a partir del verde y rojo oficiales, oscurecidos lo justo para texto blanco AA.
- `tinta` principal puede quedar en un gris-azul muy oscuro (`#22262E` o similar); `tinta.2` = `#58585A`.
- Agrega tokens `rosado`, `rosado.suave`, `naranjo`, `naranjo.suave`, `naranjo.texto`.
- Revisa `src/components/colores.ts` y `src/components/ambitos.ts` (y cualquier hex suelto con `grep -rn "#[0-9A-Fa-f]\{6\}" src`) para que todo use los tokens nuevos.

## 2. Tipografía

El manual pide **Calibri** (y Trebuchet como reemplazo). En web usa **Carlito**, su equivalente libre y métricamente idéntico:

- `npm install @fontsource/carlito` (versión 5.x) y en `src/main.tsx` reemplaza los imports de Roboto/Roboto Condensed por Carlito 400 y 700 (latin).
- `fontFamily`: `texto`, `display` y `rotulo` → `['Carlito', 'Calibri', '"Trebuchet MS"', 'system-ui', 'sans-serif']`. **Una sola familia en toda la app.**
- Carlito se ve más pequeña que Roboto a igual tamaño: sube ~1 px los tamaños de texto pequeños (11→12, 12→13) donde haga falta para que se lea bien. Ajusta `font-medium` (500) a `font-bold` (700) donde se perdiera el énfasis, porque Carlito solo trae 400 y 700.
- Desinstala `@fontsource/roboto` y `@fontsource/roboto-condensed` si ya no se usan.

## 3. Recuadros con estilo "manchas" (lo más importante)

El manual define como gráfica institucional las **manchas y formas de colores orgánicas** (ver `.kiro/diseno/manchas-integra.md` si existe; si no, son blobs redondeados irregulares, planos, sin borde, de colores de la paleta). Queremos que los recuadros dejen de verse "crudos" y se vean como tarjetas amables:

1. Crea `src/components/Mancha.tsx`: un SVG de blob orgánico (2–3 formas distintas, path suave tipo `M52 6c22 2 42 18 40 42s-20 44-46 44S4 72 8 46 30 4 52 6z`), props `color`, `forma`, `className`. Decorativo: `aria-hidden`, `pointer-events-none`, posición absoluta.
2. **Bordes más redondeados**: `rounded.tarjeta` 6px → 16px; `rounded.hoja` se queda o sube a 20px. Chips de nivel 10px.
3. **Agenda**
   - Tira de la semana: días como tarjetitas blancas redondeadas; el **día seleccionado** en azul sólido con 1–2 manchas pequeñas (amarillo y rosado, opacidad ~35%) en las esquinas, recortadas con `overflow-hidden`. "Hoy" en rosado.
   - Bloques de la jornada (períodos): tarjeta con un **círculo blanco con el ícono del período** y una mancha suave en la esquina inferior derecha. Los períodos con notas pueden llevar fondo de color sólido de la paleta (rotando azul, naranjo, verde, rosado, amarillo de forma fija por período, no aleatoria) con texto blanco o texto oscuro del mismo color si es amarillo/verde (AA). Los períodos vacíos siguen compactos y en blanco, con una mancha muy tenue.
   - El aviso de "por revisar" en naranjo suave con borde/acento naranjo.
4. **Mi sala (planilla)**: no cambies la tabla. Los chips de nivel con fondo suave del ámbito, esquinas 10px y una **manchita circular del color del ámbito** asomando en la esquina superior derecha (opacidad ~50%). "Revisar avance" con anillo naranjo. Fila al pasar el mouse en azul muy claro.
5. **Revisar**: la tarjeta de sugerencia en blanco con esquinas 16px, sombra suave y una mancha rosada tenue detrás de la foto del post-it. Botón Confirmar en verde, Corregir en borde azul, Descartar neutro.
6. **Ficha del niño/a**: tarjetas "Cómo va · por ámbito" con una mancha del color de su ámbito en la esquina. El aviso de resumen con acento naranjo o rosado suave.
7. **Directora**: tarjetas de sala con el mismo estilo de tarjeta + mancha (cada sala un color fijo de la paleta).
8. **Barra inferior y Dock**: mismo layout; ítem activo en azul oficial con un punto o mancha pequeña rosada. Botón Grabar en rojo oficial oscurecido.
9. **Fondo general**: `fondo` muy claro (`#F5F8FC`). Opcional: 2–3 manchas gigantes muy tenues (opacidad ≤ 6%) fijas en el fondo de las páginas, que no estorben la lectura.

Sombras: suaves y cortas (`0 1px 2px rgba(0,0,0,.06), 0 4px 12px rgba(0,40,90,.06)`), nunca pesadas.

## 4. Cómo terminar

- Revisa en el navegador a 360 px, 390 px y 1280 px con `npm run build` + `npm run preview` (ciérralo al final; no dejes servidores corriendo).
- `npm test` en verde (hoy 128 pruebas; no bajes el número; si una prueba depende de una clase o color viejo, ajústala sin perder lo que protege) y `npm run build` sin errores.
- Actualiza `.kiro/steering/diseno-visual.md` con la paleta, la tipografía Carlito y la regla de las manchas, y agrega en `PROGRESO.md` bajo "Formato mejorado" una sección "Estética manual Integra" con lo que cambiaste.
- No hagas commits ni push.
- Responde con un resumen corto de lo cambiado y el resultado de pruebas y build.
