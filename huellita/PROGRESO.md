# Progreso: Fase 1, tareas 1 a 4

Fecha: 14-10-2026. Spec: `.kiro/specs/app-tias/tasks.md` (tareas 1 a 4 marcadas `[x]`).

## Qué se hizo

### Tarea 1 · Proyecto base
Vite 5 + React 18 + TypeScript en la raíz, creado a mano porque la carpeta ya tenía
`.kiro/`, `data/` y `README.md` (el generador de Vite no acepta carpetas con contenido).
No se borró nada.

- Tailwind CSS con los colores del steering (`nivel.1`…`nivel.8`, `frescura.*`, `integra`),
  PostCSS y Autoprefixer.
- React Router, `lucide-react`, Vitest y `vite-plugin-pwa` (manifest "Huellita",
  color de tema `#1F4E9A`, ícono SVG en `public/icono.svg`).
- Alias `@data` → `data/` y `@` → `src/` (en `vite.config.ts` y en `tsconfig.app.json`),
  con `resolveJsonModule` para importar la rúbrica y la semilla.
- Scripts: `dev`, `build`, `test`, `test:watch`, `preview`.
- `src/app/App.tsx` es por ahora solo la cáscara con el enrutador; las pantallas son
  las tareas 5 a 9.

### Tarea 2 · Tipos y rúbrica
- `src/lib/tipos.ts`: el modelo del diseño (`Jardin`, `Sala`, `Usuaria`, `Nino`,
  `Evidencia`, `Sugerencia`) más `EvaluacionValidada` (sugerencia validada + fecha de
  la evidencia) y los tipos de la semilla y de la rúbrica.
- `src/lib/rubrica.ts`: carga `data/rubrica_8_niveles.json` y expone `niveles()`,
  `nucleos()`, `codigosNucleos()`, `descriptor()`, `conductas()`, `celda()`,
  `nombreNivel()`, `nombreNucleo()`, `colorNivel()`, `todasLasCeldas()` y
  `nivelSiguiente()`. Los núcleos y los rangos de edad (`"32–40 meses"`) se leen de los
  datos: no hay niveles ni conductas escritos a mano.

### Tarea 3 · Lógica de evaluación
`src/lib/evaluacion.ts`, funciones puras con la fecha "hoy" inyectable:
`diasEntre`, `edadMeses`, `edadAniosMeses`, `nivelEsperado`, `nivelEsperadoEnFecha`,
`nivelActualPorNucleo`, `nivelGeneral`, `revisarAvance`, `ultimaEvaluacion`, `frescura`,
`diasDesdeUltimaEvaluacion`, `observarAhora`, `resumenSala`, `evaluacionesValidadas` y
`evaluacionesDe`.

Puntos finos de las reglas:
- Rangos de edad: borde inferior inclusivo y superior exclusivo (12 meses → nivel 2).
  Sobre 72 meses se queda en el nivel 8.
- **Revisar avance** compara cada una de las 2 últimas evaluaciones del núcleo con el
  nivel esperado para la edad que tenía el niño/a **en la fecha de esa evidencia**
  (`nivelEsperadoEnFecha`), exige fechas (días) distintas y nunca marca con una sola.
- Nivel general: mediana redondeada hacia abajo de los núcleos con evidencia; los
  núcleos sin evidencia quedan en `null`, nunca en 0.
- Frescura: `< 14` verde, `14–30` amarillo, `> 30` o sin evidencia rojo.

Pruebas (`src/lib/evaluacion.test.ts`, 28 casos): frescura en 13, 14, 30 y 31 días y sin
evidencia; bordes de los 8 rangos de edad; bandera con 1 evidencia (no), 2 bajas en
fechas distintas (sí), 2 el mismo día (no) y 2 bajas solo para la edad de hoy pero
normales para la edad de su fecha (no); y con `data/semilla.json` + `fechaDemo`
(2026-10-15): **solo Josefa (NINO-00001) queda marcada, en el núcleo LV**, su nivel
general es 4 (mediana de 4,4,4,4,2) y el resumen de Medio Menor A da
"observados este mes 14 de 18 · núcleo menos cubierto CC".
`src/lib/rubrica.test.ts` (4 casos) revisa la carga de la rúbrica y los colores.

### Tarea 4 · Servicios locales
- `src/services/datos.ts`: interfaz `DataService` + `DataServiceLocal`. Parte de
  `data/semilla.json`, guarda en `localStorage` con la clave `huellita:v1`, avisa a la
  interfaz con `suscribir()` y tiene `reiniciarDemo()`. Las lecturas devuelven copias
  para que las pantallas no muten el estado. Las fotos y audios quedan **solo en
  memoria**: no se persisten (privacidad). `validar()` guarda quién y cuándo, y si la
  tía cambió algo deja la sugerencia en `cambiada` conservando el `original`.
- `src/services/ia.ts`: interfaz `IAService` + `IAServiceSimulado` con latencia de 1,5 s.
  Orden de resolución: guion de `demoCapturas` para foto o audio sin texto → calce exacto
  con un guion → nombres de la sala (sin tildes ni mayúsculas) + mejor conducta de la
  rúbrica → nombre desconocido ("por confirmar", certeza baja, sin `ninoId`) → nota de
  sala. El nivel propuesto es el nivel actual del niño/a en ese núcleo, o el esperado por
  edad si no tiene evidencia, y la conducta siempre sale de la rúbrica.
- `src/services/captura.ts`: `capturar(formato, archivo?, texto?, ninoId?)` guarda la
  evidencia y devuelve al tiro; la IA corre en segundo plano y al terminar guarda las
  sugerencias y marca la evidencia como `lista` (o `error`, sin trazas técnicas).
- Pruebas: `src/services/ia.test.ts` (10 casos: nombre exacto → certeza alta, nombre con
  tilde, dos niños → 2 sugerencias, texto grupal → `nota_sala`, nombre desconocido →
  certeza baja sin `ninoId`, guiones de foto y audio, conducta y nivel dentro de la
  rúbrica, latencia) y `src/services/datos.test.ts` (10 casos: semilla, salas por rol,
  persistencia en `localStorage`, validar, cambiar, descartar, suscripción, reiniciar
  demo, dar de baja y los 3 casos de `capturar`).

## Comandos

```powershell
npm install        # ya ejecutado
npm run dev        # desarrollo en http://localhost:5173
npm run build      # tsc -b + vite build (incluye el service worker de la PWA)
npm test           # Vitest, una pasada
npm run preview    # sirve dist/ para probar la PWA sin red
```
En Windows, si `npm` falla por la política de ejecución de scripts, usar `npm.cmd`.

## Resultado

- `npm run build`: **sin errores** (Vite 5.4.11, `dist/` con `sw.js` y
  `manifest.webmanifest`, 7 entradas en el precaché).
- `npm test`: **52 pruebas en 4 archivos, todas en verde**
  (`rubrica` 4, `evaluacion` 28, `ia` 10, `datos` 10).
- Privacidad revisada en lo construido: no hay `console.log`, los archivos de foto y
  audio no se persisten, a la IA solo se le pasa ID, nombre de pila y niveles ya
  calculados (nunca la fecha de nacimiento) y los avatares con iniciales quedan para la
  tarea 6.

## Decisiones y dudas

1. `revisarAvance(evaluaciones, fechaNacimiento)` recibe la fecha de nacimiento en vez
   del `nivelEsperado` que insinuaba el diseño, porque la regla necesita la edad **en la
   fecha de cada evidencia**. Es el único cambio de firma respecto de `design.md`.
2. `DataService` quedó con 5 métodos extra que el diseño no listaba y que las pantallas
   necesitan: `hoy()` (fecha de la demo inyectable), `usuarias()` (pantalla de entrada de
   la tarea 5), `salaActual()`/`cambiarSala()` (menú de la tía) y `evidencias()` +
   `marcarEvidencia()` (origen de cada sugerencia en Revisar y estado de error).
3. **"Observados este mes"** se calculó como el mes calendario de la fecha "hoy"
   (14 de 18 en Medio Menor A). La vista directora de la Fase 4 pide "últimos 30 días",
   que da 16 de 18. Confirmar con Integra cuál quiere en el panel de la sala.
4. **"Núcleo menos cubierto"** = el núcleo con evidencia validada de menos niños/as
   distintos, con empate resuelto por el orden de la rúbrica. En Medio Menor A empatan CC
   y EN con 9 niños, así que sale CC; si se contaran evaluaciones en vez de niños, saldría
   EN. Confirmar el criterio.
5. `IAServiceSimulado` recibe en el contexto los niveles actuales del niño/a (calculados
   en el dispositivo) para proponer un nivel coherente. En la Fase 3, a Bedrock se le
   manda solo `{id, nombre}`, como manda `privacidad.md`.
6. El `npm test` lleva `--passWithNoTests` desde la tarea 1 (cuando todavía no había
   pruebas). Se puede quitar ahora que hay 4 archivos de pruebas.
7. El ícono de la PWA es un SVG único. Si se quiere instalar en Android con ícono
   enmascarable nítido, falta generar PNG de 192 y 512 px (quedó anotado, no es del spec).

## Siguiente

Tarea 5: layout, barra inferior con el contador de pendientes, pantalla de entrada de la
demo y menú de usuaria.


---

# Progreso: Fase 1, tareas 5 a 9 (pantallas)

Fecha: 14-10-2026. Tareas 5, 6, 7, 8 y 9 marcadas `[x]` en `tasks.md`. No se avanzó a la
tarea 10.

## Decisión previa: referencia visual

La orden `.kiro/ordenes/fase1-b.md` describe una estética plana (fondo blanco, tipografía
del sistema, barras horizontales por núcleo, botón "Sí"). El steering
`.kiro/steering/diseno-visual.md` declara que **la referencia visual obligatoria es
`.kiro/diseno/prototipo.html`** (post-its sobre cuaderno cuadriculado, Bricolage
Grotesque + Atkinson Hyperlegible + Kalam, escaleras de 8 escalones, botón "Guardar") y
que ante diferencias visuales **gana el prototipo**.

Se construyó según el **prototipo**, porque es la regla permanente del proyecto y resuelve
el empate de forma explícita. Lo que la orden pide y el prototipo no contradice sí se
respetó: los 3 botones Foto · **Audio** (azul Integra, relleno) · Texto, el aviso de
pendientes, los chips con conteo, la grilla de 3 columnas, el punto de frescura (como aro
del avatar), la bandera ámbar, la línea de resumen, el origen y la cita de cada nota, la
certeza, los 3 botones por tarjeta, "Observar ahora" ("Para observar esta semana"), el
historial como línea de tiempo y "Registrar para [nombre]". Si se prefiere la estética
plana, hay que cambiar `diseno-visual.md` y avisar.

## Qué se hizo

### Base visual (previa a la tarea 5)
- `tailwind.config.js`: todos los tokens del prototipo (`tinta`, `tinta-2`, `tinta-3`,
  `fondo`, `papel`, `cuadricula`, `linea`, `integra`/`claro`/`oscuro`, `postit.*`,
  `frescura.*`, `ambar`, `nivel.1`…`nivel.8`), fuentes `display`/`texto`/`mano`, radio de
  tarjeta 14 px, hoja 24 px, `max-w-tia` 480 px y `min-h-tactil` 44 px.
- `src/estilos.css`: base (16 px, `q` sin comillas automáticas, foco de 3 px) y las piezas
  que no salen con utilidades: `.cuaderno` (cuadrícula de 22 px), `.postit` (papel
  levantado + cinta), `.pila` (post-its rosa y lima detrás), `.aro` (aro de frescura),
  `.linea-tiempo` y `prefers-reduced-motion`.
- Tipografías **autoalojadas** con `@fontsource` (Bricolage Grotesque variable, Atkinson
  Hyperlegible 400/700 y Kalam 400), importadas en `main.tsx` y precargadas por el service
  worker: la PWA se ve igual sin conexión.

### Tarea 5 · Layout, navegación y sesión de demo
- `src/app/servicios.tsx`: `ProveedorServicios` + `useServicios()`. **Ninguna pantalla
  importa `semilla.json` ni toca `localStorage`**; todo pasa por `DataService`/`IAService`,
  y las pruebas inyectan sus propias implementaciones.
- `src/app/hooks.ts`: `useConsulta` (carga + resuscripción a `datos.suscribir`) y los
  hooks de pantalla `useSesion`, `useMiSala`, `useRevisar`, `useFicha` y `useNombreNino`.
  La fecha "hoy" sale siempre de `datos.hoy()` (= `fechaDemo`, 15-10-2026).
- `src/app/Layout.tsx`: marco centrado (máx. 480 px), `main` con el relleno que
  corresponda, dock en Mi sala y en la ficha, y barra inferior. Si la demo no tiene
  usuaria elegida, redirige a `/entrada`.
- `src/app/BarraInferior.tsx`: Mi sala · Revisar (globo rojo con el número de pendientes y
  texto "por revisar" para lectores de pantalla) · Directora (solo rol directora).
- `src/pages/Entrada.tsx`: tarjetas con las 5 usuarias de la semilla ("Tía Ana · Medio
  Menor A", "Directora Carmen · Todas las salas del jardín"…). La elección se recuerda.
- `src/components/HojaMenu.tsx`: menú de la tía con cambiar de sala (solo si tiene más de
  una), cambiar de usuaria y "Reiniciar demo" (vuelve a la entrada).
- Ruta `/directora` con un texto breve: la pantalla es la tarea 14, pero el destino existe
  para que la barra no tenga callejones.

### Tarea 6 · Mi sala
Encabezado con la fecha y el nombre de la sala + botón de menú con las iniciales de la
tía; **pila de pendientes** (post-it amarillo, número en Kalam, "notas por revisar ·
Huellita ya las ordenó") que lleva a `/revisar` y se oculta en 0; chips **Todos (18) ·
Sin registro (2) · Revisar avance (1)** más el botón "?" de la leyenda; grilla de 3
columnas con `TarjetaNino` (avatar de 54 px con iniciales y aro de frescura, nombre, chip
"N4" y bandera ámbar); línea "Observados este mes: 14 de 18 · Menos registrado: …";
estados de carga, error y vacío por filtro. La leyenda explica los 3 colores, la bandera y
que el aro mide frescura, no desempeño.

### Tarea 7 · Captura
- Dock sobre la barra: Foto y Texto en círculos de 54 px y **Audio al centro, 76 px, azul
  Integra con halo**. En la ficha el dock se rotula "Registrar para [nombre]" y asocia a
  ese niño/a (requisito 1.6).
- **Foto**: `input type=file accept="image/*" capture="environment"`, se intenta abrir la
  cámara al tiro, vista previa y "Enviar foto".
- **Audio**: `MediaRecorder` que parte de inmediato, pulso rojo, contador `0:SS` y tope de
  60 s (se envía solo). Sin permiso de micrófono: "No pudimos usar el micrófono" y botón
  "Escribir la nota".
- **Texto**: hoja con el foco en el área de texto y el ejemplo del prototipo.
- Al enviar, la hoja se cierra al tiro y aparece el aviso "Listo, lo verás en Revisar": la
  IA corre en segundo plano (`services/captura.ts`) y nunca bloquea la pantalla.

### Tarea 8 · Revisar
Fondo de cuaderno cuadriculado, "Confirma lo que Huellita leyó de tus notas.", "N
pendientes" y **"Aceptar las seguras (N)"**. Cada nota es un post-it rotado (amarillo,
rosa o lima, −1,2° a +1,1°) con origen (ícono · "Ayer, 15:50" · tía) y la cita en Kalam,
y debajo la tarjeta de lectura: niño/a con mini avatar (y `(decía "Agus")` si el nombre no
calzó exacto), certeza **Segura / Revisar / Poco segura** (nunca porcentajes), número de
nivel en cuadrado de color + nombre del nivel + núcleo, conducta de la rúbrica y los
botones **Guardar** (verde) · **Cambiar** · **X**. Además: nota de sala ("Guardar en la
sala"), tarjeta de error ("No pudimos leer esta nota" → "Escribirla" o descartar), hoja
**Cambiar** (niño/a, núcleo y los 8 niveles con su descriptor) y estado vacío "¡Todo al
día!". Todas las acciones avisan con **Deshacer** por 5 s.

### Tarea 9 · Ficha del niño/a
Volver a Mi sala, avatar de 64 px con aro de frescura, nombre y "2 años 10 meses · Medio
Menor A"; resumen por plantilla ("Avanza bien en X. Conviene observar más Y."); tarjeta
lima **"Para observar esta semana"** con 1–2 conductas de la rúbrica en Kalam; **"Cómo
va"** con 4 núcleos visibles + "Ver los 8", cada uno con su escalera de 8 escalones
pintada hasta el nivel actual, el texto "Nivel 4 · Afianzando" o "Sin registros aún" y la
bandera ámbar si corresponde; al tocar un núcleo se abre la hoja con el descriptor y las
conductas del nivel actual y del siguiente; **"Registros"** como línea de tiempo con
puntos del color del nivel, filtro por núcleo y las citas en Kalam.

## Pruebas

- `src/lib/vistas.test.ts` (14 casos): iniciales, fechas ("13 oct", "Jueves 15 de
  octubre", "Hoy, 09:12", "Ayer, 15:20"), etiquetas de formato y certeza, tarjetas de la
  sala con la semilla (18 niños/as, solo Josefa con bandera, nivel general 4), conteos y
  filtros, `aria-label` de la tarjeta, resumen de la sala y resumen de la ficha (sin
  lenguaje clínico).
- `src/app/App.test.tsx` (8 casos, jsdom): monta las pantallas con un `DataServiceLocal`
  en memoria y una IA sin latencia. Comprueba Mi sala (18 tarjetas, **0 `<img>`**: ninguna
  foto de niños), el filtro de revisar avance, la leyenda, Revisar (post-its, certeza,
  acciones), que guardar saca la nota de pendientes y ofrece Deshacer, "Aceptar las
  seguras", y la ficha (resumen, "Para observar", "Cómo va", "Ver los 8", "Registrar para
  Josefa" y el detalle de núcleo).
- `src/services/datos.test.ts`: +2 casos por los métodos nuevos (`usuariaElegida` y
  `salasDelJardin`).

## Resultado

- `npm run build`: **sin errores** (`tsc -b` + Vite 5.4.11; PWA con 13 entradas en el
  precaché, incluidas las fuentes `.woff2`).
- `npm test`: **76 pruebas en 6 archivos, todas en verde** (rúbrica 4, evaluación 28,
  vistas 14, IA 10, datos 12, pantallas 8).
- Revisión en Chrome (390 px y 360 px) de Mi sala, Revisar y la ficha:
  **sin desplazamiento horizontal** (`scrollWidth = clientWidth` en las 6 combinaciones) y
  **ningún control bajo 44×44 px**. Se corrigieron dos problemas encontrados así: el
  `select` del filtro por núcleo ensanchaba la ficha a 399 px (ahora va con ancho máximo y
  recortado) y el rótulo "Registrar para [nombre]" se leía sobre el contenido (ahora el
  dock lleva fondo parejo con un degradado corto arriba).
- Flujo probado de punta a punta en el navegador: escribir una nota → aviso "Listo, lo
  verás en Revisar" → el contador pasa de 3 a 4 → la nota llega a Revisar → "Cambiar" con
  los 8 niveles → "Cambiado y guardado" → descartar todo → "¡Todo al día!". Lo mismo con
  **audio** (micrófono simulado: contador corriendo y envío correcto) y como **directora**
  (ve los 3 destinos de la barra y las 3 salas en el menú).
- Privacidad: los avatares son siempre iniciales, no hay `console.*` en `src/`, las URLs
  solo llevan IDs (`/nino/NINO-00001`), las fotos y audios quedan en memoria (la vista
  previa de la foto se libera con `revokeObjectURL`) y a la IA se le sigue pasando solo
  ID, nombre de pila y niveles ya calculados.

## Decisiones

1. **Nombres de núcleos**: se usan tal como vienen de `data/rubrica_8_niveles.json`
   ("Exploración del Entorno Natural"), no las versiones cortas del prototipo
   ("Entorno natural"), porque `rubrica.md` manda que el contenido salga de los datos.
2. **`DataService` creció en 2 métodos**: `usuariaElegida()` (para saber si la demo ya
   tiene usuaria y mostrar la entrada; en la Fase 2 lo reemplaza Cognito) y
   `salasDelJardin()` (catálogo de nombres de sala para la entrada y, después, la vista
   directora). El acceso por rol sigue en `salas()`, `ninos()` y `sugerencias()`.
3. **Deshacer** se implementó guardando una copia de las sugerencias y devolviéndolas con
   `guardarSugerencias()`, sin agregar métodos nuevos al servicio.
4. **"Descartar" en una nota con error** marca la evidencia como `lista`: sale de Revisar
   sin inventar un estado nuevo en el modelo. Si el backend prefiere un estado
   `descartada` en `Evidencia`, es un cambio de una línea.
5. La ficha muestra **4 núcleos + "Ver los 8"** (como pide `tasks.md`), aunque el
   prototipo los lista todos.
6. El botón **"Registrar para [nombre]"** quedó como rótulo del dock de la ficha, no como
   un cuarto botón, para no sumar toques ni romper el dock del prototipo.
7. `vite.config.ts` ahora incluye `src/**/*.test.tsx` y se agregó `jsdom` como dependencia
   de desarrollo para la prueba de humo de las pantallas.
8. Los íconos son de `lucide-react` (los del prototipo son SVG a mano); el ícono de
   "Cambiar" se oculta bajo 380 px para que los 3 botones quepan sin recortes.

## Pendientes

1. **Tarea 10** (pulido final en 1280 px, contraste AA medido) y **11 a 14**: no se
   tocaron. La vista Directora sigue siendo un texto.
2. La captura sin conexión (requisito 1.7) es de la Fase 2: hoy la evidencia se guarda en
   memoria/`localStorage` y se procesa al tiro.
3. La hoja inferior no atrapa el foco dentro del diálogo (sí se cierra con Escape y
   devuelve el foco al cerrarse). Conviene un ciclo de foco completo en la tarea 10.
4. El `npm test` todavía lleva `--passWithNoTests`, heredado de la tarea 1; ya se puede
   quitar.
5. Siguen abiertas las dudas 3 y 4 de las tareas 1 a 4 ("observados este mes" vs. 30 días
   y el criterio de "núcleo menos cubierto").
6. Faltan los PNG de 192 y 512 px del ícono de la PWA (anotado en las tareas 1 a 4).


---

# Progreso: Fase 1, tareas 10 a 14 (cierre de la fase)

Fecha: 14-10-2026. Orden: `.kiro/ordenes/fase1-c.md`. Tareas 10, 11, 12, 13 y 14
marcadas `[x]` en `tasks.md`. Con esto la Fase 1 queda completa.

## Paso 1 · Ajuste fiel al prototipo

Se releyó `.kiro/diseno/prototipo.html` completo y se comparó pieza por pieza con
lo construido en las tareas 5 a 9 (que ya se había hecho según el prototipo). Lo
que faltaba o estaba distinto:

1. **Resumen de la sala**: ahora las dos cifras van en negrita y en tinta, como
   el prototipo ("Observados este mes: **14 de 18** · Menos registrado: **…**").
   Para eso `lib/vistas.ts` suma `partesResumenSala()`, con su prueba.
2. **Hoja "Cambiar"**: el título pasó a ser **"Cambiar evaluación"**, el del
   prototipo (antes decía "Cambiar lo que Huellita leyó").
3. **Tarjeta "Para observar esta semana"**: se le quitó la línea con el nombre
   del núcleo, que el prototipo no tiene.
4. **Aviso (toast)**: queda a 170 px del borde, como en el prototipo.
5. **Escritorio**: fuera de la columna de la app, el fondo es el azul `#D9E1EE`
   del prototipo (antes era el gris de la app hasta el infinito).
6. **Asa de las hojas inferiores**: se ve igual, pero ahora es el botón
   **Cerrar**, porque la hoja de la leyenda no tenía ningún control alcanzable
   con teclado.

Lo demás ya calzaba: tokens de color, las 3 tipografías autoalojadas con
`@fontsource`, pila de post-its, aro de frescura, dock con Audio de 76 px al
centro, cuaderno cuadriculado de 22 px, post-its rotados con cinta y cita en
Kalam, tarjeta de lectura con Guardar/Cambiar/X, certezas Segura · Revisar ·
Poco segura, tarjeta lima, escaleras de 8 escalones, línea de tiempo, hojas
inferiores con Deshacer y los textos exactos.

## Tarea 10 · Pulido visual y accesibilidad

Medido en **Chrome de verdad** (headless por CDP) contra `npm run preview`, en
**360, 390 y 1280 px**, en Mi sala, Revisar, la ficha, las dos pantallas de la
directora y con una hoja inferior abierta: **16 combinaciones sin desplazamiento
horizontal** (`scrollWidth === clientWidth`) y **ningún control bajo 44×44 px**.

Contraste AA medido igual, recorriendo todos los nodos de texto visibles y
resolviendo el fondo efectivo. La primera pasada encontró **4 problemas reales**,
todos heredados del prototipo, y se corrigieron:

| Qué | Antes | Ahora |
|---|---|---|
| Chip de nivel "N4" (12 px) | blanco sobre el color del nivel: 1,7 a 2,5:1 | pastel del mismo color con borde y número en tinta (≥ 8:1) |
| Número grande de nivel (20 px) | blanco sobre niveles claros: 1,7 a 2,5:1 | tinta en los niveles 1–6, blanco en 7 y 8 (≥ 3,4:1) |
| Origen del post-it (13 px) | `rgba(tinta,.7)` sobre post-it rosa: 4,23:1 | `rgba(tinta,.82)`: ≥ 5,7:1 |
| "N por revisar avance" (directora) | texto en ámbar: 3,99:1 | bandera en ámbar + texto en tinta |

Además, por la misma razón, dos tonos quedaron un punto más oscuros que el
prototipo (documentado en `tailwind.config.js`): el verde del botón **Guardar**
(`#237A47`, antes 3,4:1) y el rojo del globo de pendientes (`#C83B3B`). Los
colores de frescura del aro y de la leyenda no se tocaron. También se cambió el
destino inactivo de la barra y dos etiquetas de 12 px de `tinta-3` a `tinta-2`,
que sí cumple AA.

Otros arreglos de la tarea:
- **Foco atrapado** en las hojas inferiores (era un pendiente de la tanda
  anterior): el tabulador y Mayús+Tab circulan dentro del diálogo, Escape cierra
  y el foco vuelve a donde estaba.
- **Microinteracción** al resolver una nota: el post-it se despide con una
  transición de 0,16 s antes de salir de la lista; con
  `prefers-reduced-motion` no hay animación.
- Grilla de la sala en **6 columnas** en escritorio solo en la vista de la
  directora (las pantallas de la tía siguen a 480 px con 3 columnas).
- Prueba nueva `src/app/accesibilidad.test.tsx` (17 casos): todos los controles
  de las 6 rutas tienen nombre accesible, todos declaran 44 px o más, las hojas
  son `role="dialog"` con `aria-modal`, el foco cicla, Escape cierra y ninguna
  pantalla tiene `<img>`.

## Tarea 11 · PWA y sin conexión

`vite.config.ts`: el service worker (`generateSW`) ahora cachea
`js,css,html,svg,png,ico,webmanifest,woff,woff2`, tiene
`navigateFallback: 'index.html'` (así `/revisar` o `/nino/NINO-00001` abren sin
red), `cleanupOutdatedCaches` y `clientsClaim`.

Verificado sobre `dist/`: **17 entradas en el precaché** (635 KiB) con el index,
el JS —que ya lleva dentro la rúbrica y la semilla—, los estilos, el ícono, el
manifiesto y las 10 tipografías; `registerSW.js` queda inyectado en el index. Con
`npm run preview` responden 200 el index, `/sw.js`, `/manifest.webmanifest` y una
ruta interna (`/revisar`). La prueba de abrir el navegador en modo avión queda
para la demo: requiere un navegador con interfaz.

## Tarea 12 · Revisión de privacidad de la Fase 1

Revisión convertida en pruebas (`src/services/privacidad.test.ts`, 7 casos), para
que no se pueda romper sin que `npm test` avise:

- **ningún `console.*`** en `src/` (ni con datos de niños ni sin ellos);
- **nada de datos en las URLs**: solo IDs (`/nino/NINO-00001`, `/directora/sala/SALA-MMA`);
- **ni rastro de reconocimiento facial** (`IndexFaces`, `SearchFaces`, `CompareFaces`);
- **la IA recibe solo** `{id, nombre, nivelesActuales, nivelEsperado}`: nada de
  fecha de nacimiento ni apellido;
- **las fotos y audios no se persisten**: el archivo va a la IA en memoria y el
  `localStorage` nunca lo ve;
- los datos de prueba **no traen RUT** y de cada niño/a solo la inicial del
  apellido; todos los IDs son seudónimos `NINO-00042`.

A eso se suma, en las pruebas de pantallas, que **ninguna ruta dibuja `<img>`**:
los avatares son siempre iniciales.

## Tarea 13 · Guion de demo

`DEMO.md`: recorrido de 3 minutos con los 6 pasos del plan, tiempos por paso, qué
decir, los números exactos que van a aparecer (3 notas por revisar, 18 niños/as,
14 de 18 observados) y una tabla de qué hacer si algo se cae en vivo (sin
micrófono, sin cámara, demo desordenada).

El recorrido además corre solo en `src/app/demo.test.tsx`: reinicia la demo,
entra como tía Ana, captura una foto (guion de Josefa), la guarda, la ve en la
ficha, captura un audio (guion de Emilio), le cambia el nivel a 5 con "Cambiar",
guarda una nota de sala y termina entrando como directora.

## Tarea 14 · Pantalla Directora

- `/directora` (solo rol directora, hasta 1100 px): una tarjeta por sala con el
  nombre, barra de avance, **"X de Y observados en 30 días"**, cuántos están por
  **revisar avance** y el **núcleo menos registrado**. Todo se calcula con
  `lib/evaluacion.ts` sobre los datos de prueba, con la función nueva
  `tarjetaSala()` de `lib/vistas.ts` (con pruebas).
- Al tocar una sala se abre `/directora/sala/:salaId`: **la misma Mi sala en modo
  lectura**, sin dock de captura, sin pila de pendientes y sin menú de la tía.
- Al tocar un niño/a se abre una hoja con **Ver su ficha**, **Mover de sala** y
  **Dar de baja**; las dos últimas piden confirmación y solo cambian los datos de
  la demo (`moverNino` y `darDeBaja` del `DataService`, que ya existían).
- **Acceso por rol**: una tía que escriba `/directora` a mano vuelve a Mi sala, y
  la barra inferior sigue mostrando el destino solo a la directora.

## Resultado

- `npm run build`: **sin errores** (`tsc -b` + Vite 5.4.11; PWA con 17 entradas
  en el precaché).
- `npm test`: **110 pruebas en 9 archivos, todas en verde** (rúbrica 4,
  evaluación 28, vistas 17, IA 10, datos 12, privacidad 7, pantallas 14,
  accesibilidad 17, demo 1).
- Chrome a 360 / 390 / 1280 px: sin desplazamiento horizontal, sin controles bajo
  44 px y **sin texto bajo contraste AA** en las 6 rutas y las hojas inferiores.
- `npm run preview`: index, service worker, manifiesto y rutas internas en 200.

## Decisiones

1. **Donde el prototipo no llegaba a AA, gana la accesibilidad** y se documenta:
   chip de nivel en pastel, número de nivel en tinta en los niveles claros, y dos
   tonos (verde de Guardar y rojo del globo) un punto más oscuros. Los colores de
   nivel, frescura y ámbar siguen siendo los del steering en todo lo demás.
2. El **asa de las hojas** pasó a ser el botón Cerrar en vez de agregar una X
   nueva: se mantiene el dibujo del prototipo y la hoja gana un control con
   teclado.
3. La **vista directora en modo lectura** reutiliza `MiSala` con una prop
   `soloLectura` en vez de duplicar la pantalla.
4. **Mover de sala y dar de baja** viven en la hoja del niño/a dentro de la vista
   de la directora (el prototipo no define dónde van). Avisan con un toast y
   advierten que solo cambian los datos de la demo.
5. Se quitó `--passWithNoTests` del script `test` (venía de la tarea 1).
6. Para medir la tarea 10 se usó Chrome headless por CDP con un script temporal
   (WebSocket nativo de Node 24, sin dependencias nuevas); el script no quedó en
   el repositorio. Si se quiere repetir la medición, se vuelve a escribir en 40
   líneas o se usa Lighthouse.
7. Lo que no corresponde a la Fase 1 quedó anotado en **`PENDIENTES.md`**
   (íconos PNG de la PWA, cola sin conexión, dudas de criterio para Integra).

## Revisión final (hecha por Claude Code, 15-10-2026)

La revisión final de Kiro (orden `fase1-d.md`) se cortó dos veces antes de cambiar código: una porque se detuvo a pedido y otra por una falla del servicio de Kiro. Kiro alcanzó a medir la app contra el prototipo (`medidas.txt`): la fidelidad visual ya era casi exacta, así que esta revisión se concentró en errores funcionales y de experiencia de uso.

### Corregido
1. **Las notas nuevas no siempre aparecían primero en Revisar.** Se fechaban con el día de la demo y la hora real; a primera hora de la mañana (o pasada la medianoche) quedaban debajo de las notas de ejemplo de ese día. Ahora una captura siempre queda como la evidencia más reciente (`DataServiceLocal.marcaNuevaEvidencia`). La prueba de la demo había empezado a fallar justo por esto.
2. **Notas con dos niños/as en orden invertido.** El orden de Revisar no era estable para sugerencias de la misma nota, y la IA simulada no respetaba el orden de mención. Ahora sale primero quien aparece primero en la nota (por ejemplo, Tomás antes que Gaspar).
3. **Ficha incoherente con la bandera.** Si un núcleo está en "revisar avance", ahora el resumen lo nombra ("Conviene acompañar de cerca Lenguaje Verbal"), "Para observar esta semana" propone el siguiente paso en ese núcleo y "Cómo va" lo muestra primero (marcados, luego con registros y al final sin registros).
4. **"Observados" con dos números distintos.** Mi sala decía "este mes: 14 de 18" y la directora "16 de 18 en 30 días" para la misma sala. Ahora ambas usan los últimos 30 días (el mismo corte del semáforo): "Observados en 30 días: 16 de 18". Esto resuelve el punto 4 de `PENDIENTES.md`.
5. **La directora entraba a la sala de una tía.** Ahora entra directo a su resumen de salas (`/directora`).

### Resultado
- `npm test`: **115 pruebas en 9 archivos, todas en verde** (5 nuevas: resumen y orden de la ficha, orden de mención, marca de las evidencias nuevas).
- `npm run build`: sin errores.
- Revisado en el navegador en 375 px (Mi sala, captura de texto, Revisar y ficha) y en 1280 px (directora), sin desplazamiento horizontal.

### Sin tocar
- La fidelidad visual al prototipo (las medidas de Kiro coinciden al píxel o con 1–3 px de diferencia).
- La IA simulada sigue eligiendo la conducta por palabras en común; la clasificación real la hará el backend.
