# PENDIENTES

Cosas detectadas que **no** son del spec de la Fase 1 o que dependen de otra
fase. Aquí quedan anotadas para no agregarlas por cuenta propia
(`.kiro/steering/tecnologia.md`).

## Para cerrar la Fase 1 fina

1. **Íconos PNG de la PWA** (192 y 512 px, uno enmascarable). Hoy el manifiesto
   usa solo `public/icono.svg`: la app se instala, pero Android recorta mejor un
   PNG enmascarable. Falta generar las imágenes.
2. **Captura sin conexión de verdad** (requisito 1.7, Fase 2): hoy la evidencia
   se guarda en memoria o `localStorage` y la IA simulada corre al tiro. Con red
   caída no hay cola de reintentos, porque todavía no hay backend al que mandar.
3. **Textos del prototipo que el spec pide distintos**: la ficha muestra
   4 núcleos + "Ver los 8" (lo pide `tasks.md` 9), mientras el prototipo lista
   los 8 de una vez. Y los nombres de núcleo salen de
   `data/rubrica_8_niveles.json` ("Exploración del Entorno Natural"), no de las
   versiones cortas del prototipo ("Entorno natural"), porque `rubrica.md` manda
   que el contenido salga de los datos.

## Dudas para Integra

4. **"Observados este mes" vs. "últimos 30 días"**: el panel de la sala usa el
   mes calendario (14 de 18 en Medio Menor A) y la vista directora usa 30 días
   (16 de 18), porque así lo piden `interfaz.md` y `tasks.md` 14. Conviene
   unificar el criterio.
5. **"Núcleo menos cubierto"**: hoy es el núcleo con evidencia validada de menos
   niños/as distintos, con empates resueltos por el orden de la rúbrica. Si se
   contaran evaluaciones en vez de niños/as, en Medio Menor A cambiaría de CC a
   EN.
6. **Contenido de la rúbrica de 8 niveles**: es una propuesta del equipo derivada
   de las BCEP 2018. Integra tiene que validar descriptores y conductas.

## Fuera de este repositorio (equipo de backend)

7. Amplify, Cognito, DynamoDB, S3, Lambda, Bedrock, Transcribe, Rekognition y
   hosting. El punto de conexión son las interfaces `DataService` e `IAService`
   de `src/services/`.
8. Difuminado de caras en las fotos de evidencia (Fase 4, Rekognition
   `DetectFaces`) y borrado de archivos originales a las 24 h (ciclo de vida de
   S3). En la Fase 1 los archivos nunca salen del dispositivo ni se persisten.
