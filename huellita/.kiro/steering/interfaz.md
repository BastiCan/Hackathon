---
inclusion: always
---

# Interfaz: reglas de diseño

## Principios
- **Celular primero** (ancho de referencia 375 px) y usable con **una mano**: las acciones principales van abajo, al alcance del pulgar.
- **Máximo 2 toques para registrar** una evidencia desde la pantalla de inicio.
- **Cero formularios para capturar.** La tía no elige niño, núcleo ni nivel antes de capturar; eso lo propone la IA y ella lo revisa después.
- **Áreas táctiles de al menos 44×44 px.** Texto base de 16 px; nunca menos de 13 px.
- **Español de Chile**, frases cortas, verbo primero en botones ("Registrar", "Aceptar", "Cambiar"). Nada de jerga técnica ("IA", "JSON", "modelo"): decir "Huellita leyó…" o "Sugerencia".
- **Accesible**: contraste AA, `aria-label` en botones con solo ícono y foco visible.
- Debe verse bien también en escritorio (vista directora), con un ancho máximo de contenido de 1100 px.

## Navegación
Barra inferior fija con 3 destinos: **Mi sala** · **Revisar** (con contador de pendientes) · **Directora** (visible solo para el rol directora). Los 3 botones de captura (Foto, Audio, Texto) viven sobre la barra en la pantalla Mi sala y en la ficha del niño.

## Pantalla 1: Mi sala (inicio, ruta `/`)
- Encabezado: nombre de la sala y menú de la tía (cambiar de sala, cerrar sesión).
- **Aviso de pendientes** (amarillo suave): "N registros por revisar" → lleva a `/revisar`. Se oculta si N = 0.
- **Filtros en chips**: Todos (n) · Sin registro (n) · Revisar avance (n).
- **Grilla de tarjetas de niños/as** (3 columnas en celular, 6 en escritorio). Cada tarjeta muestra:
  - un avatar circular con las **iniciales** (nunca foto);
  - el nombre de pila;
  - un **punto de frescura**: verde < 14 días desde la última evidencia validada, amarillo 14–30 días, rojo > 30 días o sin evidencia;
  - una etiqueta con el **nivel general** ("N4");
  - una **bandera** si algún núcleo está en "revisar avance".
  - Al tocarla se abre `/nino/:id`.
- **Resumen de la sala** en una línea: "Observados este mes: X de Y · Núcleo menos cubierto: Z".
- **Barra de captura**: 3 botones grandes, **Foto** · **Audio** (botón primario, destacado) · **Texto**.

## Pantalla 2: Revisar (ruta `/revisar`)
- Título "Revisar (N)" y botón secundario **"Aceptar las de certeza alta"**.
- Una **tarjeta por sugerencia**:
  - origen (ícono foto/audio/texto · fecha y hora · tía que registró);
  - **fragmento original** citado (texto leído del post-it o transcripción), en tipografía distinta;
  - chip con el niño/a (o "Toda la sala" si es una observación grupal);
  - núcleo, **nivel sugerido** (número y nombre, por ejemplo "4 Afianzando") y conducta observable de la rúbrica;
  - **certeza**: Alta (verde), Media (amarilla), Baja (gris). Nunca porcentajes;
  - 3 botones: **Sí** (primario verde) · **Cambiar** (abre un selector de niño, núcleo y nivel 1–8 mostrando el descriptor de cada nivel) · **Descartar** (ícono X).
- Si una evidencia menciona a 2 niños, se generan 2 tarjetas.
- Si la evidencia no es evaluativa (por ejemplo, "hoy bajó la asistencia"), se muestra como **nota de sala** con los botones "Guardar como nota" o "Descartar".
- Si no quedan pendientes, mostrar el estado vacío "Todo al día. Buen trabajo, tía."

## Pantalla 3: Ficha del niño/a (ruta `/nino/:id`)
- Encabezado: volver, avatar con iniciales, nombre, edad en años y meses, sala.
- **Resumen** de 2 líneas en lenguaje simple (en la Fase 1 se genera con plantilla; en la Fase 3 con IA).
- **Barras por núcleo** (8 núcleos): nivel actual 1–8 con su color de nivel, y bandera si está en "revisar avance". Mostrar 4 núcleos y un botón "Ver los 8".
- Tarjeta **"Observar ahora"**: 1 o 2 sugerencias concretas tomadas de las conductas observables del nivel siguiente en el núcleo con menos evidencia reciente.
- **Historial** (línea de tiempo): fecha · núcleo · nivel · tía que registró · fragmento. Filtro por núcleo.
- Botón **"Registrar para [nombre]"**: abre la captura con el niño ya asociado.

## Pantalla 4: Directora (ruta `/directora`, Fase 4)
- Tabla o tarjetas por sala: nº de niños, % observados en los últimos 30 días, nº con "revisar avance", núcleo menos cubierto. Al tocar una sala se abre su vista Mi sala en modo lectura.
- Acciones de gestión: mover un niño/a de sala y darlo de baja (con confirmación).

## Flujo de captura (overlay, sin cambiar de ruta)
- **Foto**: `<input type="file" accept="image/*" capture="environment">` → vista previa → "Enviar". Mensaje: "Huellita está leyendo tu nota…".
- **Audio**: botón grande para grabar o detener (MediaRecorder) con contador de segundos; máximo 60 s; al detener se envía solo.
- **Texto**: un área de texto con el foco puesto y un botón "Enviar". Sugerencia de ejemplo: "Martina armó una torre de 6 bloques y contó hasta 5".
- Al terminar: un aviso "Listo, lo verás en Revisar" y la tía vuelve a donde estaba. **Nunca bloquear la pantalla esperando a la IA.**

## Colores
- **Colores de nivel** (de la rúbrica de Integra), usados **solo** en barras y etiquetas de nivel:
  1 `#E8664F` · 2 `#F08A3E` · 3 `#F2C14E` · 4 `#9BC53D` · 5 `#5A9E3A` · 6 `#3A9E9A` · 7 `#3D7DD8` · 8 `#1F3B6B`.
- **Semáforo de frescura** (punto en la tarjeta): verde `#2E9E5B`, amarillo `#E0A800`, rojo `#D64545`. No mezclarlo con los colores de nivel.
- **Revisar avance**: ícono de bandera en ámbar, nunca fondo rojo.
- Base: fondo blanco o gris muy claro, acento azul Integra `#1F4E9A`, bordes finos y sin sombras pesadas. Tipografía sans-serif del sistema.
- Incluir siempre una **leyenda** del semáforo accesible desde Mi sala (ícono "?").
