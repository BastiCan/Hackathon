# Huellita · formato mejorado — Auditoría UX/UI para las tías de jardín (25 a 60 años)

Informe de diseño · es-CL · auditoría de solo lectura sobre `origin/main`
Código auditado: `c:\dev\hackaton\.worktrees\huellita-ux\huellita-formato-mejorado\`

**Marcas de rigor:** `[V]` = verificado leyendo el código o midiendo con el navegador. `[S]` = supuesto o inferencia.

**Cómo se verificó** (detalle en la sección G): lectura completa del código de las 6 pantallas y los 18 componentes; cálculo de 60 pares de contraste con un script de Node sobre los hex reales; y medición en un navegador Chromium de verdad (Edge sin interfaz) sobre `huellita-demo.html`, recorriendo Entrada → Agenda → Sala → Revisar → Ficha → hojas inferiores a **188, 320, 375 y 390 px**, más dos corridas con la preferencia de tamaño de letra del navegador alterada.

---

## A. Resumen ejecutivo

1. **La app ignora el tamaño de letra que la tía configuró en su teléfono.** `src/estilos.css:8` fija `html { font-size: 16px }` y los 82 tamaños de texto de la app son `px` absolutos. Medido: con el navegador en "letra grande" (`defaultFontSize=32`) la app se queda en 16 px y la planilla en **12 px**. La única preferencia que sí la mueve es el "tamaño mínimo de letra", y cuando la mueve **la interfaz se rompe**: los números de nivel se cortan dentro de su recuadro de 20×20 y la columna "Último" se sale de la pantalla `[V]`. Para la cohorte sobre 45 años esto no es un detalle: es el primer gesto que hace cualquier persona con presbicia y la app no responde.

2. **La pantalla más importante es la menos legible.** En la planilla de la sala, **210 de 215 nodos de texto están bajo 16 px**: 101 a 12 px y 100 a 13 px. Hay **91 números de nivel de 20×20 px con dígito de 12 px** en una sola pantalla `[V]` (`src/components/ChipNivel.tsx:37`, `src/pages/MiSala.tsx:169`). El steering propio del proyecto prohíbe bajar de 13 px (`.kiro/steering/interfaz.md`) y pide 16 px de base: la planilla incumple las dos reglas.

3. **Las 64 celdas de la rúbrica no están explicadas en ninguna parte alcanzable.** Los códigos de columna (IA, CC, CM, LV, LA, EN, ES, PM) se explican solo con `title` en un `<abbr>` (`src/pages/MiSala.tsx:120`), que **en un teléfono no se puede mostrar**; la leyenda explica el semáforo y la bandera pero **nunca los 8 niveles ni los colores de ámbito** (`src/components/HojaLeyenda.tsx`); y el botón "?" que la abre queda **fuera de pantalla a 375 px** (medido: ocupa de x=353 a x=397 en un ancho útil de 360, en una fila que se arrastra 53 px con la barra de desplazamiento oculta por `.sin-barra`) `[V]`. Resultado: una tía nueva ve 144 números y no tiene cómo averiguar qué significan sin un manual.

4. **"Corregir" es el único punto del flujo que se parece a un formulario, y es el que peor resiste.** La hoja mide 1072 px de alto contra 792 px visibles: el botón **"Guardar corrección" nace fuera de pantalla** `[V]`. Pide 2 listas desplegables (18 niños, 8 núcleos) y elegir entre 8 tarjetas de nivel con **89 palabras de descriptores pedagógicos**, y **no muestra la nota original** que se está corrigiendo, así que hay que recordarla (`src/components/HojaCambiar.tsx`).

5. **Con zoom al 200% la app deja de funcionar, no solo de verse bien.** Medido a 188 px de ancho útil (equivalente a 375 px con zoom 200%): **16 px de desborde horizontal** en Agenda, Sala y Revisar; los días de la semana caen a **25×56 px**; Confirmar/Corregir/Descartar a **33×44 px**; y el **menú de la usuaria colapsa a 0×44 px**, es decir, desaparece el único acceso a "cambiar de sala", "cambiar de usuaria" y "reiniciar" `[V]`. Esto incumple WCAG 2.1 SC 1.4.10 (Reflow) y 2.5.5.

6. **Para un lector de pantalla, la planilla está vacía.** `NumeroNivel` lleva `aria-hidden="true"` (`src/components/ChipNivel.tsx:35`) y `etiquetaTarjeta()` (`src/lib/vistas.ts:304`) no incluye los niveles por núcleo: la celda no anuncia nada. Además la fila se abre con un `onClick` sobre `<tr>` sin `role` ni `tabIndex` (medido: `tabIndex=-1, role=null`), así que **la planilla no se opera con teclado** `[V]`.

7. **La paleta institucional está bien resuelta en texto y mal resuelta en los indicadores pequeños.** Los 24 pares de texto principales cumplen AA con holgura (la base da 15,17:1), pero fallan los elementos no textuales que llevan información: punto de frescura amarillo **2,15:1**, puntos de ámbito amarillo **1,50:1** y verde **2,39:1**, anillo naranjo de "revisar avance" **2,84:1**, bordes de tarjeta **1,29:1**, y el dígito de nivel sobre la manchita decorativa cae a **3,14:1** (ámbito rojo) y **3,48:1** (revisar avance) `[V]`. Todos bajo el 3:1 que exige WCAG 1.4.11.

8. **Lo que ya está bien hecho hay que protegerlo.** La barra de captura (48 px, siempre ícono **más** rótulo, Grabar destacado al centro), la navegación inferior con ícono y rótulo, la captura real en 2 toques sin formulario previo, el "nunca esperar a la IA", la tarjeta de Revisar con "Huellita leyó" y la confianza explicada en palabras accionables, el resumen de la ficha en lenguaje llano, el respeto de `prefers-reduced-motion`, el zoom del navegador no bloqueado y cero fotos de niños. El encargo es **subir el resto a ese nivel**, no rediseñar `[V]`.

---

## B. Inventario: qué está realmente listo

Estado: **Listo** = terminado y usable en terreno · **Parcial** = funciona pero con un hueco de diseño o de lógica · **Maqueta** = se dibuja pero no hace lo que promete · **Pendiente** = no existe.

### B.1 Pantallas

| Pantalla | Ruta | Estado | Evidencia | Hueco |
|---|---|---|---|---|
| Entrada (elegir usuaria) | `/entrada` | **Listo** | `src/pages/Entrada.tsx:46-100`; medido: 25 controles, 0 bajo 44×44 | Es andamio de demo; en Fase 2 la reemplaza Cognito `[V]` |
| Agenda (inicio) | `/` | **Listo** | `src/pages/Agenda.tsx:56-262`; semana, aviso, IEA, 8 períodos con foto real | Textos a 13–15 px; "1 registros" en el `aria-label` (`:115`) `[V]` |
| Sala (planilla) | `/sala` | **Parcial** | `src/pages/MiSala.tsx:103-196`; 18 filas × 8 núcleos, medido 375 px de ancho, cabe | 12 px, sin leyenda alcanzable, sin teclado, sin lectura por voz `[V]` |
| Revisar | `/revisar` | **Listo** | `src/pages/Revisar.tsx:100-186`; confirmar, corregir, descartar, lote, deshacer | No muestra el descriptor del nivel al confirmar `[V]` |
| Ficha del niño/a | `/nino/:id` | **Listo** | `src/pages/FichaNino.tsx:85-283`; resumen, 8 núcleos por ámbito, tira de fotos, historial | Muestra los 8 núcleos de una vez; `tasks.md` 9 pedía 4 + "Ver los 8" `[V]` |
| Directora (salas) | `/directora` | **Listo** | `src/pages/Directora.tsx:36-60`; 3 salas con % y núcleo menos registrado | — |
| Sala en solo lectura | `/directora/sala/:id` | **Listo** | `src/pages/MiSala.tsx:32,56-66` reutiliza `MiSala` con `soloLectura` | Hereda todos los problemas de la planilla `[V]` |

### B.2 Captura

| Pieza | Estado | Evidencia | Hueco |
|---|---|---|---|
| Barra de captura (Foto · Grabar · Escribir) | **Listo** | `src/app/Dock.tsx:18,61-74`: 48 px mínimo, ícono + rótulo, Grabar en `bg-grabar` al centro con `1.3fr` | Lo mejor de la app `[V]` |
| Foto del post-it | **Parcial** | `src/components/Captura.tsx:20-88`; `capture="environment"`, abre la cámara sola (`:30-34`), reduce a 1000 px (`src/lib/fotos.ts:31-46`) | **No hay "sacar otra foto"**: con vista previa el único botón es "Enviar foto" (`:78-87`) `[V]` |
| Audio | **Listo** | `src/components/Captura.tsx:94-209`; MediaRecorder, reloj, tope 60 s, salida clara si no hay micrófono (`:168-181`) | Sin medidor de nivel ni aviso de ruido ambiente `[V]` |
| Texto | **Listo** | `src/components/Captura.tsx:214-247`; foco puesto, ejemplo en el `placeholder` | — |
| Vuelta inmediata + aviso | **Listo** | `src/app/captura.tsx:36-45`; `src/services/captura.ts:78-99` procesa en segundo plano | El aviso no lleva a Revisar `[V]` |
| Cola sin conexión | **Pendiente** | Declarado en `PENDIENTES.md:10-14`; requisito 1.7 es de Fase 2 | Honesto en la documentación `[V]` |

### B.3 Componentes

| Componente | Estado | Evidencia | Nota |
|---|---|---|---|
| `Boton` | **Parcial** | `src/components/Boton.tsx:33-34`: `min-h-tactil` (44), `text-[15px]`, `px-2` en compacto | Sin `min-width`; medido 100×44 en Revisar y 33×44 con zoom `[V]` |
| `NumeroNivel` | **Parcial** | `src/components/ChipNivel.tsx:30-52` | 12 px a `tamano=20`, `aria-hidden`, manchita al 50% encima `[V]` |
| `ChipNivel` | **Parcial** | `src/components/ChipNivel.tsx:56-66` | Solo se usa en 1 lugar (`HojaGestionNino.tsx:63`) `[V]` |
| `Avatar` | **Listo** | `src/components/Avatar.tsx:17-36`; iniciales, nunca foto | Aro de frescura de 2 px: amarillo 2,15:1 `[V]` |
| `Miniatura` | **Listo** | `src/components/Miniatura.tsx:15-66`; foto real o tipo de nota | Rótulo "Audio"/"Nota" a 12 px (`:44`) `[V]` |
| `Mancha` | **Listo** | `src/components/Mancha.tsx:28-52`; `aria-hidden`, `pointer-events-none` | Baja el contraste del dígito que tapa `[V]` |
| `TarjetaSugerencia` | **Listo** | `src/components/TarjetaSugerencia.tsx:117-210` | La pieza mejor diseñada de la app `[V]` |
| `TarjetaError` | **Listo** | `src/components/TarjetaSugerencia.tsx:216-242`; ofrece "Escribirla" | Salida clara ante fallo `[V]` |
| `HojaInferior` | **Parcial** | `src/components/HojaInferior.tsx:29-56`: foco atrapado, Escape, foco devuelto | El único "Cerrar" es el asa, que parece para arrastrar (`:77-83`) `[V]` |
| `HojaCambiar` (Corregir) | **Parcial** | `src/components/HojaCambiar.tsx:30-93` | Botón primario fuera de pantalla; `role="radio"` sin flechas `[V]` |
| `HojaLeyenda` | **Parcial** | `src/components/HojaLeyenda.tsx:11-35` | Explica frescura y bandera; **no** niveles ni ámbitos `[V]` |
| `HojaNucleo` | **Listo** | `src/components/HojaNucleo.tsx:29-66`; "Ahora" y "Siguiente", 65 palabras, cabe sin desplazar | Buen tamaño de bocado `[V]` |
| `HojaMenu` / `HojaGestionNino` | **Listo** | `src/components/HojaMenu.tsx:26-95`; `HojaGestionNino.tsx:57-168` con confirmación | — |
| Aviso flotante (toast) | **Parcial** | `src/app/aviso.tsx:17,45-78`; `role="status"`, Deshacer | 5 s fijos, sin pausa: el Deshacer se escapa `[V]` |

### B.4 Lógica que condiciona la UX

| Pieza | Estado | Evidencia |
|---|---|---|
| Rúbrica 8×8 desde datos | **Listo** | `src/lib/rubrica.ts:60-93`; medido: 8 núcleos × 8 niveles = **64 celdas**, 3–5 conductas cada una `[V]` |
| Reglas de evaluación | **Listo** | `src/lib/evaluacion.ts` + `evaluacion.test.ts` (28 casos según `PROGRESO.md:444`) `[V]` |
| Agenda por períodos | **Listo** | `src/lib/agenda.ts:15-24` (8 períodos), `:118-164` |
| Modelos de vista | **Listo** | `src/lib/vistas.ts` |
| `DataServiceLocal` | **Listo** | `src/services/datos.ts:22` (`huellita:v1`), `:194-211` |
| `IAServiceSimulado` | **Listo** | `src/services/ia.ts:49` (latencia 1500 ms), `:196-205` |
| Reducción de foto en el dispositivo | **Listo** | `src/lib/fotos.ts:31-46` |
| **Colores de nivel 1–8** | **Maqueta** | `src/lib/rubrica.ts:35-44` define los 8 colores y `src/lib/vistas.ts:277,357` los calcula, **pero ningún componente los dibuja**. `colorChipNivel()` y `colorTextoNivel()` (`src/components/colores.ts:66-74`) **no se usan en ninguna parte** `[V]` |

### B.5 Discrepancias entre documentación y código

| Lo que dice la documentación | Lo que hace el código | Juicio |
|---|---|---|
| `interfaz.md`: "Pantalla 1: Mi sala (inicio, ruta `/`)" con grilla de tarjetas de niños | `/` es **Agenda**; `/sala` es una **planilla** (`src/app/App.tsx:20-21`) | `interfaz.md` quedó obsoleto pero sigue con `inclusion: always`: **contradice al steering vigente** `[V]` |
| `interfaz.md`: barra inferior con 3 destinos | 4 destinos (`src/app/destinos.ts:28-48`) | Ídem `[V]` |
| `interfaz.md`: ficha con 4 núcleos + "Ver los 8" | Muestra los 8 agrupados por ámbito (`src/pages/FichaNino.tsx:120-175`) | Reconocido en `PENDIENTES.md:19-26` `[V]` |
| `interfaz.md`: vacío "Todo al día. Buen trabajo, tía." | "Todo revisado / Cuando registres algo nuevo, aparecerá aquí." (`src/pages/Revisar.tsx:136-137`) | El código sigue a `diseno-visual.md`, que prohíbe las frases simpáticas. **Gana el código** `[V]` |
| `interfaz.md`: "Aceptar las de certeza alta" | "Confirmar los de confianza alta (N)" (`src/pages/Revisar.tsx:128`) | El código es mejor copy `[V]` |
| `interfaz.md`: azul `#1F4E9A`, "tipografía sans-serif del sistema" | `#0063BD` y Carlito (`tailwind.config.js:30,78`) | Superado por `estetica-integra.md` `[V]` |
| `requirements.md` 4.3: "Observados **este mes**" | "Observados en **30 días**" (`src/lib/vistas.ts:201`) | Resuelto a propósito (`PENDIENTES.md:30`) `[V]` |
| `PROGRESO.md:368`: Guardar `#237A47`, globo `#C83B3B` | `guardar: '#437A19'`, `aviso.globo: '#C41F15'` (`tailwind.config.js:72,76`) | La tabla de contrastes de `PROGRESO.md` **ya no describe la paleta vigente** `[V]` |
| `PROGRESO.md:533`: "la planilla cabe completa" a 360 px | Cabe a 375 y 390 px; **a 320 px se arrastra 20 px** (medido) | Cierto en el rango declarado, falso en el borde `[V]` |
| `accesibilidad.test.tsx:33-41`: lista de clases que "declaran 44 px" incluye `nino`, `h-[54px]`, `h-[76px]` | Esas clases **ya no existen** en el código | Lista zombi: la prueba pasa por clases que nadie usa `[V]` |
| `accesibilidad.test.tsx:91`: "ningún control bajo 44×44" | Medido en el navegador: 2 controles de **41×44 y 43×44** en la planilla | La prueba compara **clases**, no geometría, y `flex-1` es un comodín: **no puede detectar un ancho menor a 44** `[V]` |

---

## C. Sistema de diseño actual

### C.1 Tokens reales

**Color** (`tailwind.config.js:19-78`, `src/components/colores.ts:17-40`, `src/components/ambitos.ts:30-45`)

| Grupo | Tokens |
|---|---|
| Texto | `tinta #22262E` · `tinta-2 #58585A` · `tinta-3 #686F7B` |
| Superficies | `fondo #F5F8FC` · `papel #FFFFFF` · `cuadricula #E6EBF2` · `linea #DCE3EF` |
| Institucional | `integra #0063BD` · `integra.claro #E3EFFA` · `integra.oscuro #004C91` |
| Logo / ámbitos | `rojo #DD271D` · `amarillo #FFCD07` · `azul #0063BD` · `verde #67BC27` |
| Ámbitos suaves | dps `#FDE3E1`/`#A01810` · com `#FFF3C2`/`#6B5200` · ent `#E6F5DA`/`#2B5A0C` |
| Acentos | `rosado #E43C84` / `.suave #FBE1EC` / `.oscuro #C01E63` · `naranjo #F07818` / `.suave #FDE7D3` / `.texto #9A4708` |
| Acción | `guardar #437A19` · `grabar #C41F15` · `aviso.globo #C41F15` |
| Frescura | `verde #2E9E5B` · `amarillo #E0A800` · `rojo #D64545` |
| Niveles 1–8 | `#E8664F #F08A3E #F2C14E #9BC53D #5A9E3A #3A9E9A #3D7DD8 #1F3B6B` — **definidos y nunca dibujados** `[V]` |

**Forma y espacio:** radios `tarjeta 16` · `hoja 20` · `chip 10` · `boton 12` · `campo 10`; sombra única `shadow-tarjeta`; anchos `tia 480` · `contenido 1100` · escritorio `232 + 1000` (`tailwind.config.js:80-110`); huecos inferiores 84 / 132 / 156 px más zona segura de iPhone (`src/estilos.css:69-77`); espaciado en múltiplos de 2 px con muchos valores sueltos (`py-[10px]`, `px-[6px]`, `gap-[2px]`, `pb-[2px]`).

**Tipografía:** una familia, **Carlito** 400 y 700 (`src/main.tsx:7-8`, `tailwind.config.js:79-83`), con Calibri y Trebuchet MS de respaldo. Interlineado base 1,45 (`src/estilos.css:13`).

### C.2 Escala tipográfica efectiva (medida en el navegador a 375 px)

| Tamaño | Dónde | Nodos medidos |
|---|---|---|
| 34 px | Reloj de grabación (`Captura.tsx:200`) | 1 |
| 26 px | "Huellita" en la Entrada | 1 |
| 22 px | `h1` de todas las pantallas (`estilos.css:30`) | 1 por pantalla |
| 18 px | "Todo revisado" (`Revisar.tsx:136`) | 1 |
| 17 px | `h2` (`estilos.css:34`) y número del día | 1–6 |
| 16 px | Dock, destinos laterales, nombre de período con notas, área de texto | **8–12** |
| **15 px** | **Cuerpo real de la app**: párrafos, filas de la tarjeta, chips de filtro, opciones de hoja | **34–49** |
| **14 px** | Resumen IEA, cita truncada de la agenda, detalle de usuaria, edad del niño | **11–16** |
| **13 px** | Rótulos `.rotulo`, etiquetas de núcleo, horas, barra inferior, contadores, usuaria del encabezado, **toda la planilla** | **26–100** |
| **12 px** | **Números de nivel**, encabezados de columna de la planilla, rótulo de miniatura, pie de la tira de la ficha | **3–101** |

Nodos bajo 16 px por pantalla (medido): Entrada 93 · Agenda 95 · **Sala 210 de 215** · Revisar 75 `[V]`.

`.kiro/steering/interfaz.md` manda "texto base de 16 px; nunca menos de 13 px". **El cuerpo real es 15 px y hay 101 nodos a 12 px en una sola pantalla: se incumplen las dos reglas** `[V]`.

### C.3 Contrastes calculados (WCAG 2.1, sobre los hex reales)

Cumplen con holgura (muestra): base `#22262E` sobre `#FFFFFF` **15,17:1**; `tinta-2` **7,10:1**; `integra` sobre blanco **5,97:1**; blanco sobre `guardar` **5,20:1**; blanco sobre `grabar` **5,91:1**; blanco sobre `rosado.oscuro` **5,82:1**; `naranjo.texto` sobre `naranjo.suave` **5,35:1**; etiquetas de ámbito **6,55 / 6,66 / 7,17:1**; `tinta` sobre amarillo del logo **10,10:1**; "Deshacer" amarillo sobre tinta **10,10:1**.

**Incumplimientos** (todos calculados, ninguno estimado):

| # | Qué | Par | Ratio | Mínimo | Dónde |
|---|---|---|---|---|---|
| C-1 | Dígito de nivel sobre la manchita del ámbito rojo (50%) | `#A01810` / `#ED857F` | **3,14:1** | 4,5 | `ChipNivel.tsx:38-48` |
| C-2 | Dígito de nivel en "revisar avance" sobre su manchita | `#9A4708` / `#F7B076` | **3,48:1** | 4,5 | `ChipNivel.tsx:22,38-48` |
| C-3 | Día seleccionado, esquina con mancha amarilla al 35% | `#FFFFFF` / `#59887D` | **4,01:1** | 4,5 | `Agenda.tsx:122-129` |
| C-4 | Punto de frescura amarillo | `#E0A800` / `#FFFFFF` | **2,15:1** | 3,0 | `MiSala.tsx:181-183`, `Avatar.tsx:25` |
| C-5 | Punto de ámbito amarillo (semana, leyenda, ficha) | `#FFCD07` / `#FFFFFF` | **1,50:1** | 3,0 | `Agenda.tsx:143-149`, `MiSala.tsx:199-206` |
| C-6 | Punto de ámbito verde | `#67BC27` / `#FFFFFF` | **2,39:1** | 3,0 | ídem |
| C-7 | Anillo naranjo de "revisar avance" | `#F07818` / `#FFFFFF` | **2,84:1** | 3,0 | `ChipNivel.tsx:22` |
| C-8 | Borde de tarjeta `linea` | `#DCE3EF` / `#FFFFFF` | **1,29:1** | 3,0 | todas las tarjetas |
| C-9 | Borde de fila `cuadricula` | `#E6EBF2` / `#FFFFFF` | **1,20:1** | 3,0 | `MiSala.tsx:134` |
| C-10 | Velo de la hoja inferior sobre el fondo | mezcla / `#F5F8FC` | **2,47:1** | 3,0 | `HojaInferior.tsx:59` |
| C-11 | Blanco sobre `rosado` pleno (si alguna vez se usa en texto) | `#FFFFFF` / `#E43C84` | **3,98:1** | 4,5 | token `rosado.DEFAULT` |
| C-12 | `colorTextoNivel(7)`: blanco sobre nivel 7 | `#FFFFFF` / `#3D7DD8` | **4,10:1** | 4,5 | `colores.ts:66-68` (hoy sin uso) |

Nada del cuerpo de texto llega a **AAA (7:1)**: `integra` sobre blanco 5,97; `tinta-3` 5,06; naranjo sobre naranjo suave 5,35. Para presbicia conviene empujar lo secundario hacia 7:1 `[S]`.

### C.4 Objetivos táctiles (medidos a 375 px, luego a 188 px)

| Elemento | 375 px | 188 px (zoom 200%) | Juicio |
|---|---|---|---|
| Botones del dock (Foto/Grabar/Escribir) | 48 px de alto (`Dock.tsx:64`) | se corta el 3.º | **Bien** a tamaño normal |
| Destinos de la barra inferior | 125×64 (y 102×64 a 320 px) | 58×64 | **Bien** |
| Confirmar / Corregir / Descartar | **100×44** con 8 px de aire | **33×44** | Al mínimo; **falla** con zoom |
| Días de la semana | ~62×56 | **25×56** | **Falla** con zoom |
| Nombre del niño/a en la planilla | **41×44** y **43×44** (nombres cortos) | — | **Falla** el ancho |
| Fila de la planilla (`<tr>`) | 375×47 | — | Toca bien, **no se teclea** |
| Celda de núcleo | **25×47**, no interactiva | — | No se puede tocar un nivel |
| Botón "?" de la leyenda | 44×44 pero **de x=353 a x=397** | — | **Fuera de pantalla** |
| Menú de la usuaria | ≥44 a 320 px | **0×44** | **Desaparece** con zoom |
| Fila de núcleo en la ficha | 282×50 | — | **Bien** |
| Opción de nivel en Corregir | 309×102 | — | **Bien** (pero 8 seguidas) |

Nada de la app llega al ideal de **48×48 con 8 px de separación**, salvo el dock. El token existe (`minHeight.tactil: 44px`) pero no hay token de 48 ni `min-w` en `Boton` (`src/components/Boton.tsx:33`) `[V]`.

### C.5 Jerarquía

Solo dos pesos (Carlito trae 400 y 700), así que todo el énfasis vive en el color y el tamaño; con 15 px de cuerpo y 13 px de rótulo, la diferencia entre "importante" y "secundario" es de **2 px**. Los rótulos de sección usan mayúscula sostenida con `tracking` (`src/estilos.css:116`), el patrón más lento de leer para una lectora con presbicia `[S]`. El naranjo de "atención" se usa también como contenedor del resumen positivo de la ficha (`src/pages/FichaNino.tsx:116`), lo que diluye su significado `[V]`.

---

## D. Auditoría por flujo

Cohortes: **50-60** = tía con presbicia y poca práctica móvil · **25-35** = tía rápida · **ambas**.

### D.1 Flujo global y marco de la app

| # | Hallazgo | Sev. | Cohorte | Evidencia | Por qué duele en terreno |
|---|---|---|---|---|---|
| G-1 | `html { font-size: 16px }` en px absolutos más 82 tamaños `px` fijos: la app **no obedece** el tamaño de letra del navegador ni del sistema. Medido con `defaultFontSize=32`: sigue en 16 px / 12 px | **Bloqueante** | 50-60 | `src/estilos.css:8` | Es lo primero que hace quien no ve de cerca. Si no funciona, la tía concluye que la app "no se puede agrandar" y deja de intentarlo |
| G-2 | `-webkit-text-size-adjust: 100%` desactiva el inflado de texto del navegador móvil | **Alta** | 50-60 | `src/estilos.css:9` | Cierra la segunda vía de agrandar sin tocar el zoom `[V]` el código, `[S]` el efecto exacto en Chrome Android |
| G-3 | Con el tamaño mínimo de letra del navegador en 22 px, los recuadros de nivel siguen midiendo 20×20 y **el dígito se corta**; "Último" se sale; nombres truncados; el globo de pendientes se monta sobre el ícono | **Bloqueante** | 50-60 | medido; cajas fijas en `ChipNivel.tsx:37` | La tía que **sí** logra agrandar la letra se queda sin leer los datos. Peor que no poder agrandar |
| G-4 | A 188 px útiles (375 px con zoom 200%): **16 px de desborde horizontal** en Agenda, Sala y Revisar | **Alta** | 50-60 | medido | Leer arrastrando en dos ejes, de pie y con una mano, es inviable. Incumple SC 1.4.10 |
| G-5 | A 188 px el **menú de la usuaria colapsa a 0×44** y desaparece | **Bloqueante** | 50-60 | `src/app/Encabezado.tsx:40-52`: el logo es `flex-none`, el botón `min-w-0` | Con zoom se pierde "cambiar de sala", "cambiar de usuaria" y "reiniciar". `diseno-visual.md` manda esconder el cargo antes que achicar el logo; el código achica el botón entero |
| G-6 | Cuerpo real a 15 px y rótulos a 13 px en mayúscula sostenida con `tracking` | **Alta** | 50-60 | medido; `src/estilos.css:116` | Con presbicia incipiente, 15 px a brazo extendido en patio exterior obliga a acercar el teléfono: un gesto que no existe cuando se supervisan 25 párvulos |
| G-7 | Sin enlace "saltar al contenido"; con lector de pantalla hay que recorrer encabezado y franja en cada pantalla | **Baja** | ambas | `src/app/Layout.tsx:62-85` | Fricción menor pero acumulativa |
| G-8 | El aviso flotante dura 5 s fijos y lleva dentro el **Deshacer**, sin pausa ni reaparición | **Alta** | 50-60 | `src/app/aviso.tsx:17,40` | Leer "Guardado en la ficha de Josefa", entender, decidir y tocar Deshacer en 5 s, mientras se vigila la sala, no alcanza. Roza SC 2.2.1 |
| G-9 | Los 8 colores de nivel se calculan y nunca se dibujan; `colorChipNivel`/`colorTextoNivel` son código muerto | **Media** | ambas | `src/lib/vistas.ts:277,357`; `src/components/colores.ts:66-74` | El nivel queda codificado **solo** como número chico. Se perdió el canal visual que haría innecesario leer el dígito |
| G-10 | El flujo de captura no dice **nada** sobre lo que pasa con la foto, aunque `privacidad.md` 3 trate las caras como asunto central | **Media** | ambas | `src/components/Captura.tsx:38-40`, `:69-72` | La privacidad es parte visible de la experiencia solo en la Entrada y en la vista directora; en el momento de sacar la foto no hay ni una línea |

### D.2 Entrada

| # | Hallazgo | Sev. | Cohorte | Evidencia | Por qué duele |
|---|---|---|---|---|---|
| E-1 | Pantalla limpia, 0 controles bajo 44×44, avatar de 44 px, detalle de sala, aviso de datos ficticios | — | — | `src/pages/Entrada.tsx:74-96` | **Fortaleza**: el mejor primer contacto de la app |
| E-2 | "Registro de observaciones de la sala para educadoras y técnicas de párvulos" a 15 px, y el detalle de cada usuaria a 14 px | **Media** | 50-60 | `src/pages/Entrada.tsx:62,86` | El texto que identifica en qué sala entra es el más chico de la tarjeta |
| E-3 | Se lista a la directora junto a las tías sin separarlas | **Baja** | ambas | `src/pages/Entrada.tsx:78-92` | Artefacto de demo; en Fase 2 lo reemplaza Cognito `[S]` |

### D.3 Agenda (inicio)

| # | Hallazgo | Sev. | Cohorte | Evidencia | Por qué duele |
|---|---|---|---|---|---|
| A-1 | Los puntos de ámbito de la semana miden **5 px** y usan amarillo (1,50:1) y verde (2,39:1): invisibles | **Media** | 50-60 | `src/pages/Agenda.tsx:143-149` | Es el único indicador de "qué se registró ese día". No se ve, y el `aria-label` solo dice cuántos |
| A-2 | `aria-label` del día: "lun 12, **1 registros**" | **Baja** | ambas | `src/pages/Agenda.tsx:115` | Suena a máquina. La app presume de español cuidado |
| A-3 | El dígito de nivel del registro va a `tamano=20` → **12 px**, `aria-hidden`, sobre manchita | **Alta** | 50-60 | `src/pages/Agenda.tsx:298` | En la agenda el nivel es información, no adorno |
| A-4 | La cita se corta a 2 líneas y al tocar **salta** a Revisar o a la ficha; nunca se lee completa en su sitio | **Media** | ambas | `src/pages/Agenda.tsx:288-292`, `:274-279` | La tía toca para leer más y la app la cambia de pantalla: pierde el lugar |
| A-5 | Un registro en proceso dice "Leyendo tu nota…" solo en la agenda, sin `aria-live` ni indicador de avance | **Media** | ambas | `src/pages/Agenda.tsx:284` | Si no está en la agenda, los 1,5 s de la IA son silencio total |
| A-6 | 8 períodos siempre desplegados, con 5 tonos rotando y una mancha por tarjeta | **Baja** | 50-60 | `src/pages/Agenda.tsx:35-48,186-200` | Mucho color por pantalla; los períodos vacíos ocupan espacio sin aportar `[S]` |
| A-7 | El aviso "N por revisar" es un botón de 44 px con rótulo claro y flecha | — | — | `src/pages/Agenda.tsx:164-178` | **Fortaleza** |

### D.4 Capturar (Foto · Grabar · Escribir)

| # | Hallazgo | Sev. | Cohorte | Evidencia | Por qué duele |
|---|---|---|---|---|---|
| F-1 | Dock de 48 px, ícono **más** rótulo, Grabar en rojo al centro y más ancho, siempre visible en Agenda y ficha | — | — | `src/app/Dock.tsx:18,61-74` | **Fortaleza**: cumple "nunca ícono sin rótulo" y es alcanzable con el pulgar |
| F-2 | **No hay "sacar otra foto"**: con vista previa el único botón es "Enviar foto"; para repetir hay que cerrar la hoja y empezar de nuevo | **Alta** | ambas | `src/components/Captura.tsx:78-87` | Luz de patio, mano ocupada, post-it movido: la foto mala es el caso **normal**, no la excepción |
| F-3 | La cámara se abre sola al montar la hoja | **Media** | 50-60 | `src/components/Captura.tsx:28-34` | Sorprende: la pantalla cambia sin que la tía haya tocado nada. Si el navegador lo bloquea queda "Abrir la cámara", que es el camino explicable `[V]` |
| F-4 | Audio sin medidor de nivel ni aviso de ruido | **Media** | ambas | `src/components/Captura.tsx:183-209` | En sala con 25 niños el audio sale sucio y la tía solo lo descubre en Revisar |
| F-5 | "Cuenta qué hizo y quién. Máximo 60 segundos." y la salida a "Escribir la nota" si no hay micrófono | — | — | `src/components/Captura.tsx:168-181,203-205` | **Fortaleza**: instrucción y salida de emergencia |
| F-6 | El aviso "Listo, lo verás en Revisar" **no lleva** a Revisar | **Media** | ambas | `src/app/captura.tsx:40` | Dice dónde está la cosa pero no abre la puerta: un toque regalado por captura |
| F-7 | No se puede capturar varias notas seguidas sin reabrir la hoja cada vez | **Media** | 25-35 | `src/app/captura.tsx:36-45` | La tía que junta 6 post-it del día hace 6 ciclos completos |

### D.5 Revisar la sugerencia de Huellita

| # | Hallazgo | Sev. | Cohorte | Evidencia | Por qué duele |
|---|---|---|---|---|---|
| R-1 | Tarjeta con N.º, origen, foto real ampliable, "Huellita leyó" entrecomillado y ficha de 5 filas con la confianza explicada ("Baja: revisa el nombre y el nivel") | — | — | `src/components/TarjetaSugerencia.tsx:51-114,166-187` | **Fortaleza**: es el mejor trabajo de la app y el corazón del producto |
| R-2 | Para saber si el nivel propuesto es correcto hay que **entrar a Corregir** y leer los 8 descriptores: la tarjeta muestra la conducta pero no el descriptor del nivel | **Alta** | ambas | `src/components/TarjetaSugerencia.tsx:180` | La acción principal ("Confirmar") pide una validación que la pantalla no permite hacer. O se confirma a ciegas, o se paga el costo completo de Corregir |
| R-3 | "Confianza **Baja**" se pinta en `text-tinta-2`, el mismo gris del texto secundario | **Media** | 50-60 | `src/components/TarjetaSugerencia.tsx:19-23` | Lo que más hay que mirar es lo que menos resalta |
| R-4 | Los 3 botones miden 100×44 a 375 px y **33×44** con zoom 200%; el ícono de Confirmar/Corregir desaparece bajo 380 px | **Alta** | 50-60 | medido; `src/components/TarjetaSugerencia.tsx:189-199` | Tres objetivos de 33 px pegados, con una sola mano: confirmar y descartar quedan a un error de distancia |
| R-5 | Confirmar y Descartar son **inmediatos**, con 5 s de Deshacer: no hay confirmación legible para la acción destructiva | **Alta** | 50-60 | `src/pages/Revisar.tsx:69-74`; `src/app/aviso.tsx:17` | Descartar borra evidencia del desarrollo de un niño. 5 s de ventana es poco para una lectora lenta |
| R-6 | Hoja "Corregir": **scrollHeight 1072 vs 792 visibles**, el botón "Guardar corrección" nace fuera de pantalla | **Bloqueante** | 50-60 | medido; `src/components/HojaCambiar.tsx:84-92` | La tía no ve cómo terminar. El patrón de una hoja que sube ya sugiere "esto es corto": el engaño es doble |
| R-7 | Corregir pide 3 decisiones (niño, núcleo, nivel) con 8 tarjetas de **89 palabras** de descriptores, y **no muestra la nota original** | **Alta** | ambas | `src/components/HojaCambiar.tsx:30-83` | Hay que recordar lo que decía el post-it mientras se leen descriptores curriculares. Carga de memoria de trabajo pura |
| R-8 | `role="radiogroup"` / `role="radio"` sin navegación por flechas | **Media** | ambas | `src/components/HojaCambiar.tsx:60-66` | Para teclado y lector de pantalla el grupo promete un comportamiento que no entrega |
| R-9 | "Confirmar los de confianza alta (1)" como botón secundario de ancho completo | — | — | `src/pages/Revisar.tsx:126-130` | **Fortaleza**: es el atajo que la cohorte 25-35 necesita |
| R-10 | El contador de pendientes cambia sin anuncio tras los 1,5 s de la IA | **Media** | ambas | `src/app/hooks.ts:122-135`; `src/app/BarraInferior.tsx:71-82` | Entrar a Revisar justo después de capturar muestra la lista vieja y luego aparecen cosas solas |
| R-11 | Vacío "Todo revisado / Cuando registres algo nuevo, aparecerá aquí." | — | — | `src/pages/Revisar.tsx:134-139` | **Fortaleza**: informa el estado y el siguiente paso sin frase simpática |

### D.6 Sala (planilla) — el punto más riesgoso

| # | Hallazgo | Sev. | Cohorte | Evidencia | Por qué duele |
|---|---|---|---|---|---|
| S-1 | **210 de 215 nodos bajo 16 px**, con 101 a 12 px y 100 a 13 px | **Bloqueante** | 50-60 | medido; `src/pages/MiSala.tsx:106,109,179,199` | Es la pantalla de la que la tía saca sus conclusiones del día. Hoy exige acercarse el teléfono a la cara |
| S-2 | **91 recuadros de nivel de 20×20 con dígito de 12 px**, dos de ellos en 3,14:1 y 3,48:1 por la manchita decorativa | **Bloqueante** | 50-60 | medido; `src/components/ChipNivel.tsx:37-48`; `src/pages/MiSala.tsx:169` | 144 celdas conceptuales resueltas con el elemento más chico y menos contrastado de la app |
| S-3 | Los códigos IA/CC/CM/LV/LA/EN/ES/PM se explican **solo** con `title` en un `<abbr>`, que no se puede mostrar en un teléfono | **Alta** | ambas | `src/pages/MiSala.tsx:120` | Sin equivalente táctil, los 8 encabezados son jeroglíficos. La tía sabe los núcleos, pero no necesariamente las siglas de esta app |
| S-4 | El botón "?" de la leyenda queda **de x=353 a x=397 en 360 px útiles**, en una fila que se arrastra 53 px con la barra de desplazamiento oculta (`.sin-barra`) | **Alta** | 50-60 | medido; `src/pages/MiSala.tsx:75,91-99`; `src/estilos.css:181-185` | La única ayuda de la app está escondida detrás de un gesto invisible. Diseñado a 375 px según `diseno-visual.md`, y a 375 px no se ve |
| S-5 | La leyenda **no explica los 8 niveles ni los colores de ámbito**: solo frescura y bandera | **Alta** | ambas | `src/components/HojaLeyenda.tsx:13-34` | Aun llegando a la ayuda, lo que no se entiende sigue sin explicarse |
| S-6 | Los números **no son tocables**: la celda mide 25×47 y no responde; tocar la fila abre la ficha | **Alta** | ambas | `src/pages/MiSala.tsx:160-175` | Para saber qué es "4" en Lenguaje Verbal: tocar fila → buscar el núcleo → tocar la fila del núcleo. Tres toques y un cambio de contexto para una pregunta de un toque |
| S-7 | La fila se activa con `onClick` sobre `<tr>` (medido `tabIndex=-1`, `role=null`) | **Alta** | ambas | `src/pages/MiSala.tsx:134-136` | No se opera con teclado; con lector de pantalla no se anuncia como activable |
| S-8 | `NumeroNivel` es `aria-hidden`, y `etiquetaTarjeta()` no incluye los niveles por núcleo: **las 144 celdas no existen para un lector de pantalla** | **Alta** | ambas | `src/components/ChipNivel.tsx:35`; `src/lib/vistas.ts:304-316` | La tabla queda vacía justo en su contenido |
| S-9 | Los nombres se truncan a `max-w-[96px]` y dos botones miden **41×44 y 43×44** | **Media** | 50-60 | medido; `src/pages/MiSala.tsx:149-152` | "Maximili…", "Benjamí…" en la pantalla donde se busca a un niño por su nombre |
| S-10 | Punto de frescura amarillo a **2,15:1** y puntos de ámbito a 1,50 / 2,39:1 | **Media** | 50-60 | calculado; `src/pages/MiSala.tsx:181,199-206` | El semáforo no se ve. Se salva porque los días van en texto al lado ("20 d") |
| S-11 | A 320 px la planilla se arrastra 20 px en horizontal | **Baja** | ambas | medido | Gama baja de 320 px sigue existiendo en terreno `[S]` |
| S-12 | Los chips de filtro traen el conteo dentro ("Todos 18", "Revisar avance 1") y usan `aria-pressed` | — | — | `src/pages/MiSala.tsx:76-90,210-231` | **Fortaleza** |

### D.7 Ficha del niño/a

| # | Hallazgo | Sev. | Cohorte | Evidencia | Por qué duele |
|---|---|---|---|---|---|
| N-1 | Resumen en lenguaje llano ("Avanza bien en Corporalidad y Movimiento. Conviene acompañar de cerca Lenguaje Verbal.") más "Para observar esta semana" con 2 conductas concretas | — | — | `src/pages/FichaNino.tsx:116-137`; `src/lib/vistas.ts:330-348` | **Fortaleza mayor**: es el único lugar donde la app traduce la rúbrica a algo accionable |
| N-2 | Las filas de núcleo miden 282×50 y abren `HojaNucleo` con "Ahora" y "Siguiente" (65 palabras, cabe sin desplazar) | — | — | medido; `src/components/HojaNucleo.tsx:38-64` | **Fortaleza**: el tamaño de bocado correcto |
| N-3 | Nada indica que las filas de núcleo se puedan tocar: sin flecha, sin borde, sin "ver detalle" | **Alta** | 50-60 | `src/pages/FichaNino.tsx:143-173` | La mejor explicación de la rúbrica está detrás de una affordance invisible |
| N-4 | "Explorando · revisar avance (esperado 4)" | **Media** | 50-60 | `src/pages/FichaNino.tsx:156-159` | "(esperado 4)" es jerga de la app: no dice esperado para qué ni según qué |
| N-5 | La tira "Su agenda" se arrastra en horizontal con la barra oculta y pies a **12 px** | **Media** | 50-60 | `src/pages/FichaNino.tsx:183,187` | Las fotos de post-it, que son la memoria visual de la tía, quedan tras un gesto invisible |
| N-6 | El resumen positivo usa el contenedor `.aviso` naranjo, el mismo de "por revisar" | **Media** | ambas | `src/pages/FichaNino.tsx:116`; `src/estilos.css:120-123` | Si todo es naranjo, nada es urgente |
| N-7 | El filtro del historial es un `<select>` nativo de 15 px truncado a 180 px | **Baja** | 50-60 | `src/pages/FichaNino.tsx:199-212` | Nativo es lo correcto; el tamaño no |
| N-8 | No existe "Ver los 8" ni agrupación progresiva: los 8 núcleos siempre desplegados | **Baja** | ambas | `src/pages/FichaNino.tsx:120-175` vs `tasks.md` 9 | Decisión consciente y defendible; se anota por la discrepancia |

### D.8 Dónde falla para la cohorte 25-35

| # | Hallazgo | Sev. | Evidencia | Por qué duele |
|---|---|---|---|---|
| J-1 | Tras capturar hay que **buscar** Revisar en la barra: el aviso no es un atajo | **Media** | `src/app/captura.tsx:40` | Un toque extra por captura, varias veces al día |
| J-2 | 1,5 s de IA sin barra de avance ni "casi listo" | **Media** | `src/services/ia.ts:49` | A quien espera fluidez, el silencio se siente como que no pasó nada |
| J-3 | Sin captura múltiple: 6 post-it = 6 ciclos de abrir hoja, cámara, enviar | **Media** | `src/app/captura.tsx:36-45` | Es justo el caso de uso del final de la jornada |
| J-4 | "Confirmar los de confianza alta" existe pero **no hay** "descartar todas", ni confirmar deslizando, ni atajos de teclado en escritorio | **Media** | `src/pages/Revisar.tsx:113-131` | El lote está a medio camino |
| J-5 | Corregir obliga a pasar por 8 tarjetas largas aunque solo se quiera mover el nivel de 4 a 5 | **Media** | `src/components/HojaCambiar.tsx:60-83` | Falta un "+1 / −1" o un paso rápido junto al nivel sugerido |
| J-6 | `conSalida()` bloquea toda la pantalla 160 ms por acción (`if (saliendo.length > 0) return;`) | **Baja** | `src/pages/Revisar.tsx:29-37` | Confirmar tres seguidas rápido se siente trabado; los toques rápidos se pierden |
| J-7 | Nada se puede hacer desde la planilla: para registrar hay que volver a Agenda o entrar a la ficha | **Media** | `src/app/Layout.tsx:33` (`conDock` solo en `/` y ficha) | Ve "Tomás, 40 días" y no puede registrarle nada ahí mismo |
| J-8 | Sin búsqueda de niño/a: 18 filas hoy, 36 en la semilla | **Baja** | `src/pages/MiSala.tsx:103-196` | Con salas más grandes se vuelve recorrido visual `[S]` |

### D.9 Accesibilidad concreta

**Lo que hoy está bien** `[V]`: roles y nombres accesibles en todos los controles de las 6 rutas (verificado por `accesibilidad.test.tsx:84-106` y por lectura); `role="dialog"` con `aria-modal`, foco atrapado, Escape y devolución del foco (`HojaInferior.tsx:29-56`); foco visible de 3 px azul con `outline-offset: 2px`, que da 5,60:1 contra el fondo (`estilos.css:37-42`); `prefers-reduced-motion` anula toda animación y transición, incluido el pulso del botón de grabar (`estilos.css:193-200`); `lang="es-CL"` en el documento (`index.html:2`); viewport **sin** `maximum-scale` ni `user-scalable=no`, así que el pinza-zoom funciona (`index.html:5`); orden de foco coherente con el orden visual, porque dock y barra inferior van después de `<main>` en el DOM (`Layout.tsx:84-87`) y la barra lateral es `display:none` en celular; `sr-only` para el sufijo "por revisar" del contador (`BarraInferior.tsx:79`) y para la etiqueta del filtro (`FichaNino.tsx:200`); `aria-pressed` en chips y días; texto alternativo correcto y nunca una cara de niño.

**Lo que falta** `[V]`:

| # | Hallazgo | Sev. | Evidencia |
|---|---|---|---|
| X-1 | Sin **ninguna** región viva para los cambios asíncronos: el contador de pendientes, la aparición de sugerencias tras 1,5 s y el paso de "Leyendo tu nota…" a listo no se anuncian. El único `role="status"` real es el aviso flotante y los párrafos de carga | **Alta** | `src/app/aviso.tsx:57`; `src/app/hooks.ts:122-135` |
| X-2 | Niveles por núcleo invisibles para lector de pantalla (`aria-hidden` + `etiquetaTarjeta` incompleta) | **Alta** | `ChipNivel.tsx:35`; `vistas.ts:304-316` |
| X-3 | `<tr>` activable sin `role` ni `tabIndex`: la planilla no se opera con teclado | **Alta** | `MiSala.tsx:134-136` |
| X-4 | `role="radiogroup"`/`role="radio"` y `role="toolbar"` sin navegación por flechas | **Media** | `HojaCambiar.tsx:60-66`; `MiSala.tsx:72-75` |
| X-5 | Zoom 200%: 16 px de desborde y controles bajo 44 px; el menú de la usuaria desaparece. **SC 1.4.10 no se cumple** | **Alta** | medido |
| X-6 | Tamaño de letra del sistema o del navegador: ignorado (G-1) y, cuando se impone, la maqueta se rompe (G-3) | **Bloqueante** | medido |
| X-7 | Contraste no textual bajo 3:1 en 7 indicadores que llevan información (C-4 a C-10) | **Media** | calculado |
| X-8 | Los diálogos no marcan el fondo como `inert`/`aria-hidden`: en modo navegación el lector sigue leyendo lo de atrás | **Baja** | `HojaInferior.tsx:58-74` |
| X-9 | Los botones que abren hojas no declaran `aria-expanded`/`aria-haspopup` | **Baja** | `Encabezado.tsx:41-48`; `MiSala.tsx:91-99` |
| X-10 | Significado transmitido solo por color o forma sin rótulo visible: bandera de "revisar avance", punto de frescura, puntos de ámbito, manchitas | **Media** | `MiSala.tsx:153-157,181`; `Agenda.tsx:143-149` |

**Qué garantizan hoy las pruebas y qué no** `[V]`:

| Prueba | Garantiza | No cubre |
|---|---|---|
| `accesibilidad.test.tsx` (17 casos) | Nombre accesible de todo control en 6 rutas; `role="dialog"` + `aria-modal`; ciclo de foco; Escape; cero imágenes de niños; 3 botones de captura con `min-h-[48px]` | **Geometría real**: compara cadenas de clases, con comodines `flex-1`, `nino`, `h-[54px]`, `h-[76px]` (las tres últimas ya no existen). **No detecta ancho < 44** (los 41×44 y 43×44 medidos pasan). No mide contraste, zoom, tamaño de letra del sistema, regiones vivas, orden de foco ni operación por teclado |
| `adaptable.test.tsx` (22 casos) | Que existan las clases `lg:` de las dos navegaciones y de las 6 pantallas; una sola lista de destinos; `min-w-0`; `max-w-full`/`w-auto` en imágenes | jsdom **no aplica media queries ni calcula layout**: "sin scroll horizontal" se infiere de clases, no se mide. El desborde de 16 px a 188 px no lo ve nadie |
| `App.test.tsx` / `demo.test.tsx` | Que las pantallas se dibujen con los textos esperados y que el guion de la demo corra de punta a punta | Nada visual ni de accesibilidad real |

**Hueco de método:** las tres pruebas verifican **intenciones escritas en clases**, no resultados. La app pasa 150 pruebas en verde y aun así tiene 2 controles bajo 44 px de ancho, 16 px de desborde con zoom y 101 nodos a 12 px. Un medidor en navegador real (lo que se hizo para este informe) es lo que falta en el repositorio `[V]`.

### D.10 Carga cognitiva de la rúbrica 8 × 8

Los datos: **64 celdas** (8 núcleos × 8 niveles) con 3 a 5 conductas observables cada una (medido sobre `data/rubrica_8_niveles.json`). En pantalla de teléfono, la planilla muestra **144 celdas conceptuales simultáneas** (18 niños × 8 núcleos) `[V]`.

Cómo se presenta hoy:

- **`NumeroNivel`** (`ChipNivel.tsx:30-52`): un dígito. A `tamano=20` son 12 px, con una manchita decorativa al 50% encima y `aria-hidden`. El color codifica el **ámbito**, no el nivel, así que el "4" de Lenguaje Verbal y el "4" de Pensamiento Matemático se ven distintos por una razón que no tiene que ver con el nivel. Y los 8 colores de nivel que `interfaz.md` define para esto existen en el código pero **no se dibujan** (G-9) `[V]`.
- **`HojaNucleo`** (`HojaNucleo.tsx:38-64`): aquí sí está bien resuelto. Dos bloques, "Ahora" y "Siguiente", con descriptor y conductas: 65 palabras medidas, cabe sin desplazar. Es la pieza que hace entendible la rúbrica.
- **`HojaLeyenda`** (`HojaLeyenda.tsx:13-34`): explica frescura y bandera. **No explica los niveles.**
- **`HojaCambiar`** (`HojaCambiar.tsx:60-83`): las 8 opciones con descriptor, 89 palabras, 1072 px de alto.

**Veredicto: no, una tía no puede elegir sin leer un manual, y el camino para aprender está cerrado** `[V]`.

La cadena se corta en tres puntos: (a) los números de la planilla **no son tocables** (S-6), así que la curiosidad no tiene a dónde ir; (b) los códigos de columna solo se explican con `title`, inservible en teléfono (S-3); (c) la leyenda no cubre niveles y además su botón queda fuera de pantalla (S-4, S-5). La única explicación buena de la rúbrica —`HojaNucleo`— vive a **tres toques** desde la planilla y detrás de una fila sin affordance (N-3).

El contraste con lo bueno es revelador: **la ficha ya resolvió el problema**. "Avanza bien en Corporalidad y Movimiento. Conviene acompañar de cerca Lenguaje Verbal" más 2 conductas concretas es exactamente lo que una tía necesita, y **no menciona ningún número** (`vistas.ts:330-348`). La planilla hace lo opuesto: 144 números sin traducción. La lección está dentro del propio producto.

### D.11 Flujo del post-it fotografiado

Lo que ya existe y funciona `[V]`: la foto se reduce en el dispositivo a 1000 px / JPEG 0,72 (`fotos.ts:31-46`) y se guarda en la evidencia; se muestra **real y derecha** en tres lugares —miniatura de 56 px en la agenda (`Agenda.tsx:281`), tamaño completo ampliable en Revisar (`TarjetaSugerencia.tsx:69-95`) y tira de 84 px en la ficha (`FichaNino.tsx:185`)—; el texto leído se cita entre comillas bajo el rótulo "Huellita leyó" (`TarjetaSugerencia.tsx:97-99`); si no se pudo leer, `TarjetaError` ofrece **"Escribirla"** en vez de dejar a la tía sin salida (`TarjetaSugerencia.tsx:216-242`); y los registros llevan número ("N.º 0325"), como un libro de registro.

Qué le falta para ser **el** camino y no un extra:

| # | Hallazgo | Sev. | Evidencia | Qué falta |
|---|---|---|---|---|
| P-1 | No se puede **repetir** la foto sin cerrar y empezar de nuevo | **Alta** | `Captura.tsx:78-87` | "Sacar otra" junto a "Enviar foto". Con luz de patio y mano ocupada, repetir es lo normal |
| P-2 | **Una foto por vez**: no existe "varias notas de una vez" | **Alta** | `app/captura.tsx:36-45` | Es el caso real: la tía junta los post-it del día y los fotografía al final. Hoy son 6 ciclos completos |
| P-3 | Ninguna ayuda de encuadre: solo el texto "Encuadra el post-it o la hoja completa" | **Media** | `Captura.tsx:38-40` | Marco guía o aviso de "se ve oscuro / movido" antes de enviar |
| P-4 | Nada dice qué pasa con la foto ni advierte sobre caras | **Media** | `Captura.tsx:69-72`; `privacidad.md` 3 | Una línea: "La foto queda en tu teléfono. Trata de no incluir caras." |
| P-5 | No se puede fotografiar **desde la planilla**, que es donde la tía detecta a quién le falta registro | **Media** | `Layout.tsx:33` | Dock también en `/sala` |
| P-6 | La foto de la agenda es una miniatura de 56 px no ampliable | **Baja** | `Agenda.tsx:281` | En Revisar sí se amplía; en la agenda, no |
| P-7 | La jerarquía del dock pone **Grabar** al centro, en rojo y más ancho; Foto queda a la izquierda, igual que Escribir | **Media** | `Dock.tsx:18-22` | Si el papel y lápiz es lo que ya hacen, **Foto** debería ser el botón destacado. Hoy el diseño declara que lo principal es grabar audio, que es justo lo que peor funciona con 25 niños gritando |

---

## E. Recomendaciones priorizadas

Ninguna recomendación reescribe la app. Todas operan sobre lo que ya existe.

### E.1 Victorias rápidas (token, tamaño, rótulo o copy; sin tocar arquitectura)

| # | Qué | Archivo y valor concreto | Por qué | Resuelve |
|---|---|---|---|---|
| V-1 | **Dejar que la letra crezca.** Cambiar `html { font-size: 16px }` por `html { font-size: 100% }` y quitar `-webkit-text-size-adjust: 100%` | `src/estilos.css:8-9` | Devuelve el control a la preferencia de la tía; es la corrección de mayor impacto y la de menor costo | G-1, G-2, X-6 |
| V-2 | **Subir la base a 17 px y el mínimo a 14 px.** Reemplazar en masa: `text-[12px]`→`text-[14px]`, `text-[13px]`→`text-[15px]`, `text-[14px]`→`text-[15px]`, `text-[15px]`→`text-[17px]`; `body` a `text-[17px]`; `h1` 22→26 px; `h2` 17→19 px | `src/estilos.css:13,30,34` y los 82 usos de `text-[…]` | 101 nodos a 12 px es insostenible con presbicia. Carlito además se ve más chica que su tamaño nominal | S-1, G-6, A-3, E-2, N-5, N-7 |
| V-3 | **Agrandar el número de nivel.** En `NumeroNivel`, subir la proporción de fuente de `0.58` a `0.72` y pasar `tamano` de 20 a **28** en la planilla y en la agenda | `src/components/ChipNivel.tsx:37`; `src/pages/MiSala.tsx:169`; `src/pages/Agenda.tsx:298` | 28 × 0,72 ≈ 20 px de dígito: legible de un vistazo y la celda de 25×47 lo admite | S-2, A-3 |
| V-4 | **Quitar la manchita decorativa de debajo del dígito.** En `NumeroNivel`, bajar `opacity` de `0.5` a `0.18` o mover la mancha fuera del área del dígito | `src/components/ChipNivel.tsx:44` | Recupera 3,14:1 → sobre 6:1 en el ámbito rojo y 3,48:1 → sobre 5:1 en revisar avance | C-1, C-2, S-2 |
| V-5 | **Rótulos que se entiendan.** Cambiar el "?" por un botón con texto **"¿Qué significan?"** y moverlo **antes** de los chips de filtro (primer hijo del `role="toolbar"`) | `src/pages/MiSala.tsx:72-99` | Lo saca de fuera de pantalla y deja de ser un ícono mudo | S-4, X-10 |
| V-6 | **Completar la leyenda.** Agregar a `HojaLeyenda` un bloque "Los 8 niveles" con `niveles()` (número, nombre y edad orientativa) y otro "Los colores" con los 3 ámbitos y sus núcleos | `src/components/HojaLeyenda.tsx:13-34`, usando `src/lib/rubrica.ts:97-100` | Es la pieza que falta para que las 64 celdas sean aprendibles sin manual | S-5, D.10 |
| V-7 | **Encabezados de columna con nombre corto visible.** Añadir bajo la sigla un `<span>` con las 3 primeras letras del núcleo, o rotular la columna con "LenVerb" en lugar de "LV" | `src/pages/MiSala.tsx:117-124` | `title` no se puede mostrar en un teléfono: hoy no hay forma de saber qué es "PM" | S-3 |
| V-8 | **Botones de 48 px con ancho mínimo.** En `Boton`, cambiar `min-h-tactil` por `min-h-[48px]`, agregar `min-w-[48px]` y subir `text-[15px]` a `text-[17px]`; agregar el token `minHeight.comodo: '48px'` | `src/components/Boton.tsx:33`; `tailwind.config.js:101-106` | Pasa del mínimo legal al ideal de 48×48 en los 3 botones de Revisar y en toda la app | R-4, C.4 |
| V-9 | **Darle tiempo al Deshacer.** Subir `DURACION_MS` de 5000 a **9000** y detener el reloj mientras el puntero o el foco estén sobre el aviso | `src/app/aviso.tsx:17,40` | 5 s no alcanzan para leer, entender y decidir mientras se vigila la sala | G-8, R-5 |
| V-10 | **El aviso de captura lleva a Revisar.** Pasar una acción al aviso: `aviso('Listo, lo verás en Revisar', () => navegar('/revisar'))` con el rótulo **"Ver ahora"** | `src/app/captura.tsx:40`; `src/app/aviso.tsx:61-74` | Ahorra un toque por captura y cierra el ciclo | F-6, J-1 |
| V-11 | **"Sacar otra foto".** Con vista previa, mostrar dos botones: `Enviar foto` (primario) y `Sacar otra` (secundario, que vuelve a disparar el input) | `src/components/Captura.tsx:78-87` | La foto mala es el caso normal en patio exterior | P-1, F-2 |
| V-12 | **Foto como botón principal del dock.** Cambiar la grilla a `grid-cols-[1.3fr_1fr_1fr]` y pasar `principal` de `audio` a `foto`, con Grabar en secundario | `src/app/Dock.tsx:18-22` | El papel y lápiz es lo que las tías ya hacen; el audio es lo que peor resiste el ruido de sala | P-7 |
| V-13 | **Subir el contraste de los indicadores.** `frescura.amarillo` `#E0A800`→`#8A6300` (2,15→5,2:1); puntos de ámbito con `TEXTO_AMBITO` en vez de `COLOR_AMBITO` (1,50→7,42:1 el amarillo); `ring` del chip de revisar a `naranjo.texto`; `linea` `#DCE3EF`→`#A9B6CC` (1,29→3,0:1); `cuadricula` `#E6EBF2`→`#BFC9D9` | `tailwind.config.js:23-25,66-70`; `src/components/colores.ts:33-37`; `src/components/ambitos.ts:33-37`; `src/components/ChipNivel.tsx:22` | Los 7 indicadores que llevan información están bajo 3:1 | C-4 a C-9, S-10, A-1 |
| V-14 | **Contraste del velo.** Subir `rgba(34,38,46,0.42)` a `rgba(34,38,46,0.60)` | `src/components/HojaInferior.tsx:59` | 2,47:1 no separa la hoja del fondo; con zoom la hoja se pierde | C-10 |
| V-15 | **"Cerrar" visible en las hojas.** Dejar el asa y añadir a su derecha un botón de 48 px con la palabra **Cerrar** | `src/components/HojaInferior.tsx:77-83` | Un asa parece para arrastrar; la cohorte 50-60 no prueba gestos | B.3, G-5 |
| V-16 | **"Confianza baja" que se vea.** `CLASE_CERTEZA.baja` de `text-tinta-2` a `text-naranjo-texto font-bold` | `src/components/TarjetaSugerencia.tsx:19-23` | Lo que exige más atención es hoy lo más apagado | R-3 |
| V-17 | **Afianzar las filas de núcleo de la ficha.** Añadir `<ChevronRight>` y el texto "Ver qué se espera" a la derecha de cada fila | `src/pages/FichaNino.tsx:143-173` | Desbloquea `HojaNucleo`, la mejor explicación de la rúbrica | N-3, D.10 |
| V-18 | **Lenguaje.** "(esperado 4)" → **"para su edad se espera nivel 4"**; expandir "IEA" la primera vez: "3.º registro del IEA (la evaluación de noviembre)"; el `aria-label` del día en singular cuando corresponda | `src/pages/FichaNino.tsx:158`; `src/pages/Agenda.tsx:172,115` | `interfaz.md` prohíbe la jerga; estos tres casos la dejan pasar | N-4, A-2 |
| V-19 | **Privacidad visible en la captura.** Añadir en `HojaFoto`: "La foto queda guardada en tu teléfono. Trata de que no salgan caras." | `src/components/Captura.tsx:38-40` | `privacidad.md` 3 trata las caras como asunto central y la interfaz nunca lo menciona | P-4, G-10 |
| V-20 | **Rótulos para la bandera y el punto.** Añadir `<span class="sr-only">revisar avance</span>` junto a cada `<Flag>` y un `title`/`sr-only` al punto de frescura | `src/pages/MiSala.tsx:153-157,181`; `src/pages/FichaNino.tsx:149-154` | Significado transmitido solo por forma | X-10 |
| V-21 | **Alinear la documentación con el código.** Marcar `.kiro/steering/interfaz.md` como histórico (igual que se hizo con `prototipo.html`) o reescribir sus pantallas 1 a 3; corregir la tabla de colores de `PROGRESO.md:368`; limpiar la lista zombi de `accesibilidad.test.tsx:33-41` | `.kiro/steering/interfaz.md`; `PROGRESO.md`; `src/app/accesibilidad.test.tsx` | Hoy hay dos contratos de diseño vigentes que se contradicen | B.5 |

### E.2 Cambios estructurales

| # | Qué | Archivos | Por qué | Resuelve |
|---|---|---|---|---|
| T-1 | **Que la planilla sobreviva a la letra grande.** Quitar el alto y ancho fijos de `NumeroNivel` (usar `min-w`/`min-h` en `em` con relleno), permitir que la fila crezca, y a partir del ancho donde dejan de caber 8 columnas conmutar a **2 columnas por ámbito** (3 bloques) en vez de arrastrar | `src/components/ChipNivel.tsx:30-52`; `src/pages/MiSala.tsx:103-196` | Hoy, cuando la letra crece, los datos se cortan. Es la condición para que V-1 y V-2 sean seguras | G-3, X-5, X-6, S-11 |
| T-2 | **Hacer tocable el nivel.** Convertir cada `<td>` en un botón que abra `HojaNucleo` con ese niño y ese núcleo, y reemplazar el `onClick` del `<tr>` por un enlace real en la celda del nombre | `src/pages/MiSala.tsx:134-175`; `src/components/HojaNucleo.tsx` | Cierra el circuito de aprendizaje de la rúbrica (un toque en lugar de tres) y arregla el teclado de un golpe | S-6, S-7, X-3, D.10 |
| T-3 | **Dar voz a la planilla.** Que cada celda anuncie "Lenguaje Verbal, nivel 2, revisar avance" (quitar `aria-hidden` de `NumeroNivel` cuando lleve información, o añadir `sr-only` en la celda) y ampliar `etiquetaTarjeta()` con los niveles por núcleo | `src/components/ChipNivel.tsx:35`; `src/lib/vistas.ts:304-316` | Las 144 celdas no existen para un lector de pantalla | X-2, S-8 |
| T-4 | **Reordenar la hoja "Corregir".** Fijar arriba la nota original ("Huellita leyó: …"), fijar abajo una barra con **Guardar corrección** siempre visible (`sticky bottom-0`), y colapsar niño y núcleo a dos filas de "cambiar solo si hace falta"; dejar como paso 1 el ajuste rápido de nivel (**−1 / nivel sugerido / +1**) y las 8 tarjetas largas tras "Ver los 8 niveles" | `src/components/HojaCambiar.tsx:30-93`; `src/components/HojaInferior.tsx:72` | Es el único formulario del flujo y hoy esconde su propio botón de salida | R-6, R-7, J-5 |
| T-5 | **Mostrar el descriptor al confirmar.** Agregar a la fila "Nivel" de `TarjetaSugerencia` el descriptor de `celda(nucleo, nivel).descriptor` en una línea, o un "¿qué es nivel 4?" que abra `HojaNucleo` | `src/components/TarjetaSugerencia.tsx:174-180` | Permite validar la sugerencia en la pantalla donde se pide validarla | R-2 |
| T-6 | **Capturar varias notas de una vez.** Permitir `multiple` en el input de foto y encolar: una evidencia por imagen, un solo aviso ("3 notas en camino") | `src/components/Captura.tsx:42-58`; `src/services/captura.ts:60-101` | Convierte el post-it en el camino real de fin de jornada | P-2, J-3 |
| T-7 | **Captura disponible en la planilla.** Extender `conDock` a `/sala` y rotular el dock con el niño/a cuando se entre desde una fila | `src/app/Layout.tsx:33`; `src/app/Dock.tsx:38-42` | La planilla es donde se detecta a quién falta observar; hoy no se puede actuar ahí | J-7, P-5 |
| T-8 | **Anunciar lo asíncrono.** Una región viva única en `Layout` que informe "Huellita leyó tu nota. Hay 4 registros por revisar" cuando cambie el contador, más un estado visible de progreso en la fila "Leyendo tu nota…" | `src/app/Layout.tsx:62-85`; `src/app/hooks.ts:122-135`; `src/pages/Agenda.tsx:284` | Los 1,5 s de la IA son hoy silencio total para quien no mira la agenda | X-1, A-5, R-10, J-2 |
| T-9 | **Confirmación legible para Descartar.** Pedir confirmación en una hoja ("¿Descartar esta nota? No se guardará ninguna evaluación") y dejar el Deshacer de 9 s solo para Confirmar | `src/pages/Revisar.tsx:69-74`; `src/components/TarjetaSugerencia.tsx:244-256` | Es la única acción destructiva del flujo y es la más fácil de tocar por error con 3 botones de 33 px | R-5, R-4 |
| T-10 | **Encabezado que no se coma su propio menú.** Dar `min-w-[96px]` al botón de la usuaria y permitir que el logo baje a `h-7` antes de que el botón colapse; por debajo de ~300 px, mostrar solo el ícono de menú con `aria-label` | `src/app/Encabezado.tsx:40-52,73-81` | Con zoom 200% desaparece el único acceso a cambiar de sala y reiniciar | G-5 |
| T-11 | **Un medidor en navegador real dentro del repositorio.** Un script de desarrollo que, sobre `vite preview` y por CDP, mida en 320/375/390/768/1280 px y con el tamaño mínimo de letra en 22 px: desborde horizontal, geometría de todo control (ancho **y** alto), tamaño de fuente efectivo y contraste resuelto, y falle la revisión si algo incumple | nuevo, junto a `vite.config.ts`; reemplaza las comprobaciones por clases de `accesibilidad.test.tsx:33-41` y `adaptable.test.tsx` | Los 150 casos en verde no detectaron 2 controles bajo 44 px de ancho, 16 px de desborde con zoom ni 101 nodos a 12 px: hoy se prueban intenciones, no resultados | D.9 |

### E.3 Orden sugerido

1. **Primero, lo que no se puede diferir:** V-1, V-2, V-3, V-4 junto con T-1. Van juntos porque agrandar la letra sin arreglar las cajas fijas empeora la pantalla (G-3).
2. **Después, lo que destraba el aprendizaje de la rúbrica:** V-5, V-6, V-7, V-17, T-2, T-5.
3. **Luego, el formulario y las acciones de riesgo:** T-4, V-8, V-9, V-16, T-9.
4. **Enseguida, el camino del post-it:** V-11, V-12, V-19, T-6, T-7.
5. **En paralelo y barato:** V-13, V-14, V-15, V-18, V-20, V-21.
6. **Como red de seguridad, antes de seguir iterando:** T-11, T-3, T-8, T-10.

---

## F. Defaults a prueba de edad (el "modo tía" sin bifurcar la app)

La tesis: **no hace falta un modo aparte.** Todo lo que necesita una tía de 58 años con presbicia también sirve a una de 28, porque lo que pide es tamaño, rótulos y vías visibles —nada de eso le quita velocidad a nadie—. Lo que **sí** se bifurcaría es la densidad, y ahí la respuesta es dejar que la decida el teléfono, no la app.

**Las 12 decisiones:**

1. **La letra la manda la usuaria, no la app.** `html { font-size: 100% }`, sin `text-size-adjust`, y medidas en `rem` donde sea posible. Si la tía puso "letra grande" en su teléfono, Huellita sale grande. Es la única decisión que vuelve innecesario un "modo tía".
2. **Cuerpo de 17 px y piso de 14 px.** Nada por debajo de 14 px, nunca, ni en rótulos ni en contadores ni en encabezados de tabla. Hoy el piso es 12 px.
3. **Objetivo táctil de 48 × 48 con 8 px de aire**, con ancho mínimo y no solo alto. El dock ya lo hace: es el patrón a copiar.
4. **Siempre ícono más rótulo.** Ningún ícono solo con información: ni el "?" de la leyenda, ni la bandera de revisar avance, ni los puntos de color. El dock y la barra inferior ya lo cumplen.
5. **Nunca un gesto como única vía.** Todo lo que hoy está tras un arrastre horizontal con la barra oculta (el "?" de la leyenda, la tira de fotos de la ficha, las columnas de la planilla en pantalla angosta) necesita un botón o un cambio de maqueta. Las hojas se cierran con un botón **Cerrar** con texto, no solo con el asa.
6. **Las cajas crecen con su contenido.** Ningún `width`/`height` fijo alrededor de texto: el número de nivel, los chips y las celdas en `em` con relleno. Es la condición para que el punto 1 no rompa nada.
7. **Dos niveles de jerarquía, no cinco.** Con solo 400 y 700 de peso, la jerarquía debe venir del tamaño (17 / 19 / 26 px) y no de cinco escalones de 12 a 15 px que a esa edad se ven iguales. Fuera la mayúscula sostenida con `tracking` en los rótulos de sección.
8. **El color acompaña, nunca informa solo.** Todo indicador cromático lleva texto al lado —la columna "Último" ya lo hace bien: punto **más** "20 d"—. Y los indicadores que informan llegan a 3:1; el texto, a 4,5:1, y lo secundario apunta a 7:1.
9. **Siempre se puede deshacer, y con tiempo para leerlo.** 9 segundos, reloj en pausa mientras se lee, y confirmación explícita solo para lo destructivo (Descartar). "La IA sugiere, la tía decide" también significa que equivocarse no cuesta nada.
10. **Cada pantalla dice qué pasó y qué sigue.** Toda espera tiene explicación visible y anuncio para lector de pantalla; todo error tiene salida (`TarjetaError` con "Escribirla" ya es el modelo); todo vacío dice qué hacer. Nada de pantallas que se quedan calladas 1,5 segundos.
11. **Cero formularios para capturar, y un solo formulario en toda la app.** La captura ya no pide nada: eso se mantiene. Corregir es el único formulario y debe caber de una vez, con su botón de guardar siempre visible y el ajuste rápido de nivel antes de los 8 descriptores.
12. **Español de Chile, sin jerga ni acrónimos sin explicar.** Verbo primero en los botones, siglas expandidas la primera vez ("IEA", "PM"), nada de "esperado 4" sin decir esperado para qué, y nunca un anglicismo. En esto la app está casi impecable: hay que cerrar los tres casos de V-18.

**Y una decisión de contenido, que es la más importante de todas:** la planilla debe aprender de la ficha. Un número del 1 al 8 no significa nada para nadie —la ficha lo demostró al traducirlo a "Avanza bien en Corporalidad y Movimiento. Conviene acompañar de cerca Lenguaje Verbal"—. Mientras la pantalla principal de datos siga siendo 144 números de 12 px sin traducción ni forma de consultarlos, el riesgo del producto no es que la tía no vea: es que **no le sirva**.

---

## G. Riesgos y supuestos

### G.1 Qué se verificó y cómo (reproducible)

Sin `node_modules` en el worktree (`npm install` no se corrió, para no modificarlo), así que **no se ejecutaron `npm test` ni `npm run build`**. Las cifras de pruebas y build salen de `PROGRESO.md:443-447` y están marcadas como tales.

La verificación visual y geométrica **sí** se hizo, sobre `huellita-demo.html` (la app completa en un archivo, que coincide con el código actual: Carlito, `#0063BD`, `font-size:16px`, `text-size-adjust`, sin rastro de Roboto). Herramientas: Microsoft Edge 'headless' (Chromium) en `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` y Node 22.22.2. Método: una página anfitriona en `%TEMP%` que carga la app en un `iframe` del ancho deseado con `--allow-file-access-from-files`, la recorre haciendo clic por texto (Entrada → Agenda → Sala → Revisar → Ficha → hojas) y escribe las mediciones en el DOM, que se extrae con `--dump-dom`; más capturas de pantalla con `--screenshot`. Preferencias de letra forzadas con `--blink-settings=defaultFontSize=…,minimumFontSize=…`. Contrastes calculados con un script de Node sobre los hex reales (fórmula WCAG 2.1, incluida la mezcla alfa de las manchas y del velo).

Todos los archivos temporales se borraron al terminar. Nada del worktree ni del repositorio se modificó.

### G.2 Lo que no se pudo verificar

| Qué | Por qué | Cómo verificarlo después |
|---|---|---|
| Que la app compile y las 150 pruebas sigan en verde | Sin `node_modules` y sin permiso para instalar en el worktree | `npm install && npm run build && npm test` en una copia |
| Comportamiento real en **Chrome de Android** con "Tamaño de fuente" y "Escala de texto" del sistema | Solo se forzaron las preferencias de Blink en escritorio. La conclusión G-1 es `[V]` en el código y en Chromium de escritorio; el detalle del inflado de texto de Chrome Android es `[S]` | Un teléfono Android de gama baja con el deslizador de tamaño de texto al máximo, en Agenda y Sala |
| Zoom del navegador de verdad al 200% y al 400% | Se simuló reduciendo el ancho útil a 188 px, que es el equivalente en CSS px. Es una buena aproximación pero no idéntica (el zoom real también escala las medias consultas de forma distinta) | Chrome a 375 px con `Ctrl+`+ hasta 200% y 400%, revisando Agenda, Sala, Revisar y la hoja Corregir |
| Lector de pantalla real (TalkBack / NVDA) | No hay entorno de prueba disponible. Los hallazgos X-1, X-2, X-3 y X-9 salen de leer el código y del árbol de accesibilidad implícito, no de escucharlos | TalkBack en Android recorriendo la planilla y la hoja Corregir |
| Cámara, micrófono y `MediaRecorder` reales | 'Headless' no tiene cámara ni micrófono; el flujo de foto y audio se auditó leyendo el código y los estados que sí se pudieron montar | Un teléfono real en patio exterior, con luz fuerte y ruido de sala |
| Rendimiento en Android de gama baja | No se midió. Las 326 evidencias de la semilla se recargan por completo en cada `suscribir` (`src/app/hooks.ts:67-91`), lo que es un candidato razonable a lentitud percibida en un equipo modesto `[S]` | Lighthouse con limitación de CPU 4× y un perfil de rendimiento al confirmar una sugerencia |
| Comportamiento con 25–30 niños por sala | La semilla tiene 18 en Medio Menor A y 36 en total (medido). El informe razona con 18 filas; con 30 la planilla empeora de forma proporcional `[S]` | Cargar una semilla de 30 y volver a medir la planilla |
| Instalación como PWA y uso sin conexión | No se compiló. `PENDIENTES.md:7-9` ya anota que faltan los PNG enmascarables de 192 y 512 px | `npm run build && npm run preview`, instalar en Android y abrir en modo avión |

### G.3 Supuestos de diseño declarados

- Se asume que `.kiro/steering/diseno-visual.md` es el contrato vigente y que `interfaz.md` quedó atrás, porque el código sigue al primero en todos los puntos donde se contradicen (B.5). Si la intención del equipo fuera la contraria, varios hallazgos cambian de signo `[S]`.
- Se asume que el equivalente en CSS px es la forma correcta de estimar el zoom del navegador para efectos de SC 1.4.10 `[S]`.
- Se asume que las tías conocen los 8 núcleos de las BCEP pero **no** las siglas de esta app ni el significado de los niveles 1 a 8, que son una propuesta del equipo aún sin validar por Integra (`PENDIENTES.md:35-38`). Si Integra ya usa estas siglas en sus instrumentos, S-3 baja de severidad `[S]`.
- Se asume que el teléfono es propio de la tía y de gama baja, según el contexto del encargo; no se verificó con datos de Integra `[S]`.
- La severidad "bloqueante" se usa para lo que impide completar una tarea o leer un dato a una tía de la cohorte 50-60, no para lo que rompe la aplicación: la app no se cae en ninguno de los casos medidos.
