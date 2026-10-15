# Orden: diseño adaptable — celular y computador

Trabajas solo en `huellita-formato-mejorado/`, solo frontend. Esta orden va **después** de `estetica-integra.md` (respeta su paleta, la fuente Carlito, las manchas y el logo; no los cambies).

## Problema

Hoy todo se dibuja como una columna de 480 px (`max-w-tia`) centrada. En el computador se ve como "un celular en medio de la pantalla", con la barra inferior y el Dock flotando. Queremos que la app sea **adaptable**: en celular exactamente como está; en computador, un diseño de escritorio que aproveche el ancho.

## Regla de oro

- **Celular (< 1024 px): no cambia nada.** Ni distribución, ni tamaños, ni barra inferior, ni Dock. Las pruebas que hoy pasan deben seguir pasando igual.
- **Computador (≥ 1024 px, prefijo `lg:` de Tailwind):** diseño de escritorio. Entre 768 y 1023 px (tablet) puede usar el diseño de celular un poco más ancho (hasta 640 px), sin barra lateral.
- Mismos componentes y datos: solo cambian clases responsivas y, donde haga falta, un contenedor de grilla. Nada de duplicar pantallas ni lógica.

## Diseño de escritorio (≥ 1024 px)

1. **Marco** (`src/app/Layout.tsx`)
   - Encabezado (logo + usuaria + franja) a todo el ancho de la ventana, contenido interno hasta `max-w-[1280px]` centrado.
   - Debajo: **barra lateral izquierda** fija de ~232 px con la navegación (Agenda, Sala, Revisar con su contador, Directora si corresponde), ítem activo en azul oficial con fondo azul claro y la manchita rosada; y a la derecha el contenido, hasta ~1000 px de ancho, con padding 24–32 px.
   - Reutiliza `BarraInferior`: en `lg:` se transforma en la barra lateral (o crea `NavegacionLateral` que use los mismos destinos; sin duplicar la lista de destinos — extráela a un arreglo compartido).
   - La barra inferior fija y el espacio que reserva (`paddingBottom`) **no existen** en `lg:`.
2. **Registrar (Dock)** en escritorio: en vez de barra fija abajo, los 3 botones (Foto, Grabar, Escribir) van en la parte superior de la barra lateral como un bloque "Registrar", o como fila de botones arriba a la derecha del contenido de la Agenda y la Ficha. Mismos botones, mismo `useCaptura`, mismos `aria-label`.
3. **Agenda**: dos columnas — izquierda (≈ 2/3) la tira de la semana y la jornada; derecha (≈ 1/3) el aviso de "por revisar", la línea del registro IEA y un resumen breve. La tira de la semana se puede ver más amplia.
4. **Mi sala (planilla)**: la tabla ocupa todo el ancho del contenido, columnas más holgadas, nombres completos sin truncar.
5. **Revisar**: tarjetas de sugerencia en **grilla de 2 columnas**; la foto del post-it un poco más grande.
6. **Ficha del niño/a**: dos columnas — izquierda el resumen/aviso y "Cómo va · por ámbito"; derecha "Su agenda" (fotos) y los Registros.
7. **Directora**: tarjetas de sala en grilla de 3 columnas.
8. **Hojas inferiores** (`HojaInferior`, menús, corregir, captura): en escritorio se muestran como **diálogo centrado** (ancho ~520 px, esquinas redondeadas en los 4 lados, fondo oscurecido), no pegadas abajo. En celular siguen como hoja inferior.
9. **Avisos/toasts** (`aviso.tsx`): en escritorio abajo a la derecha, ancho ~380 px.
10. **Entrada**: en escritorio, tarjeta centrada de ~560 px sobre el fondo con manchas suaves; la lista de usuarias en 2 columnas si cabe.

## Requisitos para que abra en cualquier celular

- Mantén `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">`; actualiza `theme-color` al azul oficial `#0063BD` en `index.html` y en el manifiesto PWA de `vite.config.ts`.
- Nada debe provocar scroll horizontal en 320, 360, 375, 390, 412 px ni en 768, 1024, 1280, 1440 px. Usa `min-w-0`, `overflow-x-auto` solo dentro de la planilla, e imágenes con `max-w-full`.
- Respeta las zonas seguras del iPhone (`env(safe-area-inset-bottom)`) en la barra inferior y el Dock.
- Que funcione en Safari iOS y Chrome Android: evita APIs no soportadas sin respaldo; `dvh` con respaldo `vh`.
- Que la app funcione servida desde una **subcarpeta** (p. ej. GitHub Pages en `/Hackathon/`): agrega `base: './'` en `vite.config.ts` si no rompe nada, y usa rutas relativas para íconos/manifest (`start_url: './'`, `scope: './'`).

## Pruebas

- Agrega `src/app/adaptable.test.tsx` (jsdom) que compruebe que los componentes de escritorio usan clases `lg:` y que en celular siguen la barra inferior y el Dock (basta verificar presencia de clases y elementos; jsdom no aplica media queries).
- `npm test` en verde (no bajes de 128 + las nuevas) y `npm run build` sin errores.
- Revisa con el navegador (`npm run build` + `npm run preview -- --port 4180`, ciérralo al terminar) en 360, 390, 768, 1280 y 1440 px.

## Cómo terminar

- Actualiza `.kiro/steering/diseno-visual.md` con una sección "Adaptable: celular y escritorio" y `PROGRESO.md` con lo hecho.
- No hagas commits ni push. No dejes servidores corriendo.
- Responde con un resumen corto y el resultado de pruebas y build.
