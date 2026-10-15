# Orden: poner el logo oficial en el encabezado

Trabajas en esta carpeta (`huellita-formato-mejorado/`), solo frontend. No toques nada fuera de ella.

Lee primero `.kiro/steering/diseno-visual.md` y `src/app/Encabezado.tsx`.

## Qué cambiar

Hoy el encabezado es una franja azul (`bg-integra`) con un sello **dibujado a mano** (`SelloInstitucional`: banderita + "Gobierno de Chile | INTEGRA"). Hay que reemplazarlo por el **logo real**, que ya está en:

`src/assets/marca/logo-mineduc-integra.png`

Es un PNG horizontal de **fondo blanco**: a la izquierda el bloque azul/rojo "Ministerio de Educación · Gobierno de Chile" y a la derecha "INTEGRA · Red de Salas Cuna y Jardines Infantiles".

Como el logo tiene fondo blanco, **no lo pongas sobre azul**. Hazlo así:

1. **Barra superior blanca** (`bg-white`, borde inferior `border-linea`), alto mínimo 56 px, padding horizontal 16 px.
   - Izquierda: el logo con `<img>`, alto ~36 px en celular y ~44 px desde `sm`, ancho automático, `alt="Ministerio de Educación, Gobierno de Chile · Integra"`. Que **nunca se deforme ni se corte** a 360 px de ancho.
   - Derecha: el botón de la usuaria (nombre + cargo + chevron) que ya existe, ahora con texto `text-tinta` / `text-tinta-suave` en vez de blanco. Mantén el `aria-label`, el área táctil ≥ 44 px y que abra `HojaMenu`.
   - Si a 360 px el logo y el nombre no caben juntos, esconde el cargo (o acorta) antes que achicar el logo por debajo de 32 px.
2. **Mantén `FranjaLogo`** (los 4 colores) justo debajo, tal cual.
3. Elimina `SelloInstitucional` y reemplaza sus usos (búscalo también en `src/pages/Entrada.tsx`). En la pantalla de Entrada el logo puede ir más grande (~56–64 px de alto, centrado).
4. Actualiza el comentario del componente (ya no es un sello dibujado).

## Pruebas (importante)

Hoy hay pruebas que dicen "en esta pantalla no hay ninguna imagen" (privacidad: nunca fotos de niños/as). Con el logo eso cambia. **No borres esas pruebas**; ajústalas para que sigan protegiendo lo mismo:
- `src/app/App.test.tsx` líneas ~78–79: buscan el texto "Gobierno" e "INTEGRA"; cámbialas para comprobar que existe el `img` del logo con su `alt`.
- `src/app/App.test.tsx` líneas ~117 y ~213, y `src/app/accesibilidad.test.tsx` ~142–151: que ignoren **solo** la imagen del logo (por ejemplo, excluir el `img` dentro de `header`, o permitir exactamente ese `alt`) y sigan exigiendo cero fotos de niños/as en el resto.

## Cómo terminar

- `npm test` en verde (hoy son 128 pruebas; no bajes el número) y `npm run build` sin errores.
- Actualiza `.kiro/steering/diseno-visual.md` (sección del encabezado) y agrega una línea en `PROGRESO.md` bajo "Formato mejorado": "Encabezado con logo oficial Mineduc + Integra".
- No hagas commits ni push. No levantes servidores que queden corriendo (si usas `npm run preview`, ciérralo al terminar).
- Al final responde con un resumen corto de lo que cambiaste y el resultado de las pruebas.
