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
3. **Nombres visibles de los núcleos**: el backend solo trae los códigos
   (`motor_grueso`…). Los nombres ("Motor grueso", "Lenguaje y comunicación"…) y
   las siglas de la planilla (MG, MF, LC, SE, CO) están en
   `data/nucleos_e1.json`; si el equipo de backend los define, se copian de ahí.
4. **Corregir no cambia la conducta**: si la tía corrige el núcleo o el nivel,
   la conducta guardada sigue siendo la que propuso Huellita. Falta que elija la
   conducta del nuevo nivel (son 2 por nivel y núcleo) o que se limpie.
## Dudas para Integra
5. ~~"Observados este mes" vs. "últimos 30 días"~~ **Resuelto en la revisión final:** Mi sala y la vista directora usan los últimos 30 días (16 de 18 en Medio Menor A).
6. **"Núcleo menos cubierto"**: hoy es el núcleo con evidencia validada de menos
   niños/as distintos, con empates resueltos por el orden de la rúbrica. Si se
   contaran evaluaciones en vez de niños/as, el resultado podría cambiar.
7. **Contenido de la rúbrica E-1**: es la del dataset sintético del desafío
   (9 niveles de 0 a 36 meses), la misma del backend. No es un instrumento
   clínico validado: Integra tiene que validar niveles y conductas, y decidir qué
   pasa con los niños/as de más de 36 meses (hoy quedan en el nivel 9).
## Fuera de este repositorio (equipo de backend)
8. Amplify, Cognito, DynamoDB, S3, Lambda, Bedrock, Transcribe, Rekognition y
   hosting. El punto de conexión son las interfaces `DataService` e `IAService`
   de `src/services/`.
9. **Audio al transcriptor** (`servicio_transcripcion`, rama
   `feature/transcriptor-audio`): Grabar audio y Subir audio ya entregan el
   archivo a `IAService.procesar`, revisado con las mismas reglas del
   transcriptor (formato por sus primeros bytes, hasta 4 MB). Falta el adaptador
   que lo mande, **siempre a través del backend**: la clave `x-api-key` del
   transcriptor nunca va en el navegador.
10. **Nómina compartida**: los niños/as de la demo todavía no son los del dataset
    E-1 (IDs y nombres de `integra-backend/tests/fixtures/nomina_demo.json`).
11. Difuminado de caras en las fotos de evidencia (Fase 4, Rekognition
    `DetectFaces`) y borrado de archivos originales a las 24 h (ciclo de vida de
    S3). En la Fase 1 los archivos nunca salen del dispositivo ni se persisten.
