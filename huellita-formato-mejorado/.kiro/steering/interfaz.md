---
inclusion: always
---

# Interfaz: reglas de diseño

## Principios
- **Celular primero** (ancho de referencia 375 px) y usable con **una mano**: las acciones principales van abajo, al alcance del pulgar.
- **Máximo 2 toques para registrar** una evidencia desde la pantalla de inicio.
- **Cero formularios para capturar.** La tía no elige niño, núcleo ni nivel antes de capturar; eso lo propone la IA y ella lo revisa después. Lo único que se elige es la **sala**, y viene puesta.
- **Áreas táctiles de al menos 44×44 px.** Texto base de 16 px; nunca menos de 13 px.
- **Español de Chile**, frases cortas, verbo primero en botones ("Registrar", "Aceptar", "Cambiar"). Nada de jerga técnica ("IA", "JSON", "modelo"): decir "Huellita leyó…" o "Sugerencia".
- **Accesible**: contraste AA, `aria-label` en botones con solo ícono y foco visible. El nivel nunca depende solo del color: el número va siempre escrito.
- Debe verse bien también en escritorio (vista directora), con un ancho máximo de contenido de 1100 px.

## Navegación
Barra inferior fija: **Inicio** · **Sala** · **Revisar** (con contador de pendientes) · **Directora** (visible solo para el rol directora). Los 4 botones de captura viven en la pantalla de Inicio y, en la ficha del niño/a, en la barra de captura sobre la navegación.

## Pantalla 1: Inicio (ruta `/`)
- Rótulo "Inicio · sala", fecha larga y "Hoy".
- **Semana** de lunes a viernes: hoy en azul y un punto por registro de cada día (naranjo si falta revisarlo). Solo informa; no se navega por días.
- **Aviso de pendientes**: "N por revisar" → lleva a `/revisar`. Se oculta si N = 0. Debajo, el próximo registro IEA y los observados en 30 días.
- **Registrar en [sala]**: selector con las salas de la usuaria (si tiene una sola, solo se nombra). Cambiarla cambia la sala de trabajo, la misma de Sala y Revisar.
- **4 botones grandes**: **Subir foto** (cámara o galería) · **Grabar audio** (destacado en rojo) · **Escribir** · **Subir audio** (una nota de voz ya grabada).

## Pantalla 2: Sala (ruta `/sala`)
- Planilla: una fila por niño/a y una columna por núcleo (MG, MF, LC, SE, CO) con el **número del nivel en el color de su nivel**, y la columna "Último" con el punto de frescura.
- Filtros en chips: Todos (n) · Sin registro (n) · Revisar avance (n). Leyenda de los 9 colores bajo la tabla y hoja "Qué significan los colores" (ícono "?").
- "Revisar avance": bandera junto al nombre y aro naranjo en el número de ese núcleo; nunca fondo rojo.
- **Resumen de la sala** en una línea: "Observados en 30 días: X de Y · Menos registrado: Z" (mismo corte de 30 días que el semáforo y la vista directora).

## Pantalla 3: Revisar (ruta `/revisar`)
- Título y botón secundario **"Confirmar los de confianza alta"**.
- Una **tarjeta por sugerencia**:
  - origen (ícono foto/audio/texto · fecha y hora · tía que registró);
  - **fragmento original** citado (texto leído del post-it o transcripción);
  - el niño/a (o "Toda la sala" si es una observación grupal);
  - núcleo, **nivel sugerido** (número en su color y nombre, por ejemplo "9 Secuencias y autonomía creciente") y conducta observable de la rúbrica;
  - **certeza**: Alta (verde), Media (naranjo), Baja (gris). Nunca porcentajes;
  - 3 botones: **Confirmar** · **Corregir** (selector de niño, núcleo y nivel 1–9 con las conductas de cada nivel en ese núcleo) · **Descartar**.
- Si una evidencia menciona a 2 niños, se generan 2 tarjetas.
- Si la evidencia no es evaluativa (por ejemplo, "hoy bajó la asistencia"), se muestra como **nota de sala** con "Guardar en la sala" o "Descartar".

## Pantalla 4: Ficha del niño/a (ruta `/nino/:id`)
- Encabezado: volver, avatar con iniciales, nombre, edad en años y meses, sala.
- **Resumen** de 2 líneas en lenguaje simple y **"Para observar esta semana"**: 1 o 2 conductas observables del nivel siguiente en el núcleo que más lo necesita.
- **Cómo va · por núcleo**: los 5 núcleos con su nivel actual (número en su color y nombre del nivel), bandera si está en "revisar avance". Al tocar uno se ve el nivel actual y el siguiente.
- **Historial** (línea de tiempo): fecha · núcleo · nivel · tía que registró · fragmento. Filtro por núcleo.
- Barra **"Registrar para [nombre]"**: abre la captura con el niño ya asociado (y en su sala).

## Pantalla 5: Directora (ruta `/directora`)
- Tarjetas por sala: nº de niños, % observados en los últimos 30 días, nº con "revisar avance", núcleo menos registrado. Al tocar una sala se abre su planilla en modo lectura.
- Acciones de gestión: mover un niño/a de sala y darlo de baja (con confirmación).

## Flujo de captura (hoja, sin cambiar de ruta)
- **Subir foto**: el sistema ofrece cámara o galería → vista previa → "Enviar foto". "Tomar foto" abre la cámara directo.
- **Grabar audio**: graba al tiro con contador de segundos; máximo 60 s; al detener se envía solo.
- **Escribir**: un área de texto con el foco puesto y un botón "Enviar".
- **Subir audio**: elegir una nota de voz (m4a, mp3, wav, ogg, webm, flac o amr, hasta 4 MB, las mismas reglas del transcriptor del backend), escucharla y "Enviar audio".
- Al terminar: un aviso "Listo, lo verás en Revisar" y la tía vuelve a donde estaba. **Nunca bloquear la pantalla esperando a la IA.**

## Colores
- **Colores de nivel**: un color por nivel, del cálido al azul oscuro, usados **solo** en números, etiquetas y puntos de nivel:
  1 `#EF7A6A` · 2 `#F59E4C` · 3 `#F7CB4D` · 4 `#B7D351` · 5 `#72BE5B` · 6 `#3FB3A3` · 7 `#56A3E3` · 8 `#2F6BC4` · 9 `#233F86`. Texto en tinta del 1 al 7 y en blanco en el 8 y el 9 (todos AA).
- **Semáforo de frescura** (punto junto a la fecha del último registro): verde `#2E9E5B`, amarillo `#E0A800`, rojo `#D64545`. No mezclarlo con los colores de nivel.
- **Revisar avance**: bandera y aro en naranjo oscuro, nunca fondo rojo.
- El resto sigue la paleta del manual de Integra (ver `diseno-visual.md`).
- Incluir siempre una **leyenda** de los colores accesible desde Sala (ícono "?").
