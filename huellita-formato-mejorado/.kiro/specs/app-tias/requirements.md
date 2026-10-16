# Requisitos: Huellita (app para tías de Integra)

> **Actualización (15-10-2026):** la app pasó a la rúbrica E-1 del backend (5 núcleos × 9 niveles, `data/rubrica_e1.json`) y la Agenda se reemplazó por Inicio. Donde este documento diga 8 núcleos, nivel 1–8 o `rubrica_8_niveles.json`, mandan `.kiro/steering/rubrica.md` e `interfaz.md`. Detalle en `PROGRESO.md`.

## Introducción
Huellita convierte la evidencia que las tías ya generan en la sala (post-its, audios y notas breves) en evaluaciones ordenadas por niño/a, núcleo y nivel (1–8), con validación de la tía en un toque. El objetivo es reducir la documentación de 4 h a menos de 15 min por semana, cuidando la privacidad de los niños y niñas. Ver el steering en `.kiro/steering/` (producto, privacidad, interfaz, rúbrica y tecnología).

## Glosario
- **Evidencia**: registro capturado por una tía (foto, audio o texto) más el texto extraído.
- **Sugerencia**: propuesta de la IA a partir de una evidencia (niño/a, núcleo, nivel, conducta, cita y certeza), en estado `pendiente`, `aceptada`, `cambiada` o `descartada`.
- **Evaluación validada**: sugerencia aceptada o cambiada por una tía. Solo estas cuentan para niveles y frescura.
- **Nota de sala**: evidencia no evaluativa o grupal (por ejemplo, asistencia, clima del grupo).

---

### Requisito 1: Captura rápida de evidencia
**Historia:** Como tía, quiero registrar lo que observo en 2 toques, en el formato que me acomode, para no dejar de estar con los niños.

1. CUANDO la tía está en Mi sala o en la ficha de un niño/a, EL SISTEMA DEBERÁ mostrar siempre visibles los botones Foto, Audio y Texto.
2. CUANDO la tía toca Foto, EL SISTEMA DEBERÁ abrir la cámara trasera del dispositivo (o el selector de archivos en escritorio) y, tras confirmar la foto, enviarla a procesar.
3. CUANDO la tía toca Audio, EL SISTEMA DEBERÁ empezar a grabar de inmediato, mostrar un contador y detenerse con un toque o a los 60 s, enviando el audio a procesar.
4. CUANDO la tía toca Texto, EL SISTEMA DEBERÁ abrir un área de texto con el foco puesto y un botón Enviar.
5. CUANDO se envía una evidencia, EL SISTEMA DEBERÁ devolver el control a la tía de inmediato con el aviso "Listo, lo verás en Revisar", sin esperar a que termine el procesamiento.
6. SI la captura se inicia desde la ficha de un niño/a, ENTONCES EL SISTEMA DEBERÁ asociar ese niño/a a la evidencia por defecto.
7. SI no hay conexión, ENTONCES EL SISTEMA DEBERÁ guardar la evidencia en una cola local y procesarla al recuperar la conexión (Fase 2+).
8. EL SISTEMA NO DEBERÁ pedir que la tía elija niño/a, núcleo o nivel antes de capturar.

### Requisito 2: Procesamiento de la evidencia con IA
**Historia:** Como tía, quiero que la app entienda mi nota y me proponga a qué niño, núcleo y nivel corresponde, para no tener que clasificarla yo.

1. CUANDO llega una evidencia de foto, EL SISTEMA DEBERÁ extraer el texto manuscrito o impreso (Fase 3: Bedrock con Claude visión).
2. CUANDO llega una evidencia de audio, EL SISTEMA DEBERÁ transcribirla al español (Fase 3: Amazon Transcribe).
3. CUANDO hay texto extraído, EL SISTEMA DEBERÁ generar una sugerencia por cada niño/a mencionado, con niño/a, núcleo, nivel 1–8, conducta observable de la rúbrica, cita textual de respaldo y certeza (Alta/Media/Baja).
4. SI el texto describe al grupo completo o no es evaluativo, ENTONCES EL SISTEMA DEBERÁ clasificarlo como nota de sala.
5. SI un nombre no coincide con ningún niño/a de la sala, ENTONCES EL SISTEMA DEBERÁ marcar el niño/a como "por confirmar" con certeza Baja.
6. EL SISTEMA DEBERÁ usar únicamente niveles y conductas presentes en `data/rubrica_8_niveles.json`.
7. EL SISTEMA NO DEBERÁ enviar a la IA datos del niño/a distintos del nombre de pila y el ID (ver privacidad).

### Requisito 3: Revisión y validación por la tía
**Historia:** Como tía, quiero confirmar o corregir las sugerencias con un toque, para que la evaluación siga siendo mía.

1. EL SISTEMA DEBERÁ listar en Revisar todas las sugerencias pendientes de las salas de la tía, de la más reciente a la más antigua, con el contador visible en la navegación.
2. CUANDO la tía toca Sí, EL SISTEMA DEBERÁ guardar la sugerencia como evaluación validada con la tía y la fecha y hora.
3. CUANDO la tía toca Cambiar, EL SISTEMA DEBERÁ permitir modificar niño/a, núcleo y nivel (mostrando el descriptor de cada nivel) y guardar como evaluación validada en estado `cambiada`, conservando la sugerencia original.
4. CUANDO la tía toca Descartar, EL SISTEMA DEBERÁ marcar la sugerencia como descartada sin afectar niveles.
5. CUANDO la tía toca "Aceptar las de certeza alta", EL SISTEMA DEBERÁ validar todas las pendientes con certeza Alta y mostrar cuántas aceptó, con opción de deshacer durante 5 s.
6. EL SISTEMA DEBERÁ mostrar en cada tarjeta la cita original que respalda la sugerencia.
7. EL SISTEMA NO DEBERÁ mostrar la certeza como porcentaje.

### Requisito 4: Panel de la sala
**Historia:** Como tía, quiero ver de un vistazo cómo va mi sala y a quién me falta observar.

1. EL SISTEMA DEBERÁ mostrar una tarjeta por niño/a activo de la sala con iniciales, nombre de pila, punto de frescura, nivel general y bandera de "revisar avance" si corresponde.
2. EL SISTEMA DEBERÁ ofrecer los filtros Todos, Sin registro (frescura roja) y Revisar avance, con su conteo.
3. EL SISTEMA DEBERÁ mostrar el resumen "Observados este mes: X de Y · Núcleo menos cubierto: Z".
4. EL SISTEMA DEBERÁ calcular frescura, nivel general y bandera según las reglas de `rubrica.md`.
5. CUANDO la tía toca una tarjeta, EL SISTEMA DEBERÁ abrir la ficha de ese niño/a.
6. EL SISTEMA DEBERÁ mostrar una leyenda que explique el semáforo y la bandera.

### Requisito 5: Ficha del niño/a
**Historia:** Como tía, quiero ver el progreso de cada niño/a y qué observar después, para apoyarlo mejor y refrescar mi memoria.

1. EL SISTEMA DEBERÁ mostrar nombre, edad en años y meses, sala y un resumen breve en lenguaje simple.
2. EL SISTEMA DEBERÁ mostrar el nivel actual de cada uno de los 8 núcleos con su color de nivel, o "sin evidencia".
3. EL SISTEMA DEBERÁ mostrar la sugerencia "Observar ahora" según las reglas de `rubrica.md`.
4. EL SISTEMA DEBERÁ mostrar el historial de evaluaciones validadas (fecha, núcleo, nivel, tía, cita), filtrable por núcleo.
5. EL SISTEMA DEBERÁ permitir ver, para cada núcleo, el descriptor y las conductas del nivel actual y del siguiente, como apoyo a la tía.

### Requisito 6: Sesión y roles
**Historia:** Como tía o directora, quiero entrar y ver solo lo que me corresponde.

1. EL SISTEMA DEBERÁ permitir elegir el usuario de demo (Fase 1) o iniciar sesión con Cognito (Fase 2).
2. CUANDO la usuaria es tía, EL SISTEMA DEBERÁ mostrar solo sus salas.
3. CUANDO la usuaria es directora, EL SISTEMA DEBERÁ mostrar todas las salas de su jardín y la pantalla Directora.

### Requisito 7: Vista directora (Fase 4)
**Historia:** Como directora, quiero ver el avance de todas las salas y gestionar la matrícula.

1. EL SISTEMA DEBERÁ mostrar por sala: nº de niños, % observados en 30 días, nº con revisar avance y núcleo menos cubierto.
2. EL SISTEMA DEBERÁ permitir mover un niño/a a otra sala y darlo de baja, con confirmación y registro de quién lo hizo.

### Requisito 8: Privacidad
1. EL SISTEMA NO DEBERÁ mostrar fotos de niños en la interfaz; los avatares son iniciales.
2. EL SISTEMA NO DEBERÁ usar reconocimiento facial.
3. EL SISTEMA DEBERÁ registrar autor y fecha de cada validación o cambio.
4. EL SISTEMA DEBERÁ borrar los archivos originales 24 h después de procesarlos (Fase 2+).
5. EL SISTEMA NO DEBERÁ incluir datos de niños en URLs ni en logs.

### Requisito 9: Calidad y uso
1. EL SISTEMA DEBERÁ funcionar en celulares de 360 px de ancho sin desplazamiento horizontal.
2. EL SISTEMA DEBERÁ ser instalable como PWA y abrir la última pantalla usada sin conexión (Fase 1: datos locales).
3. EL SISTEMA DEBERÁ cumplir contraste AA y tener `aria-label` en los botones con solo ícono.
