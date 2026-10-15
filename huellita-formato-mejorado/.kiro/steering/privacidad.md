---
inclusion: always
---

# Privacidad de los niños y niñas (reglas obligatorias)

Estas reglas aplican a todo el código, los datos de prueba y los prompts de IA. Si una tarea entra en conflicto con ellas, gana la privacidad y hay que avisarlo.

1. **Nunca usar reconocimiento facial.** El niño/a se identifica por el nombre o apodo escrito o dicho en la evidencia, comparado contra la lista de su sala, o porque la tía lo selecciona. Prohibido usar Rekognition `SearchFaces`, `IndexFaces` o `CompareFaces`.
2. **Nunca mostrar fotos de caras de niños en la interfaz.** Los avatares son círculos con iniciales. Si una foto de evidencia tiene caras, se difuminan antes de guardarla (en la Fase 4, con Rekognition `DetectFaces`).
3. **Minimizar los datos (formato mejorado).** Se guarda la **foto del post-it o de la nota** (reducida, para que la tía la vea en la agenda y en Revisar). Las fotos donde aparezcan niños o niñas **se difuminan antes de guardarse o no se guardan** (backend). Los audios no se guardan: solo su transcripción. En el frontend de la demo, las fotos viven en el navegador (`localStorage`) y nunca salen del dispositivo.
4. **Seudonimizar.** En la base de datos el niño/a se identifica por un ID (`NINO-00042`). El nombre visible vive solo en el registro del niño, nunca en logs ni en nombres de archivo.
5. **No enviar datos sensibles innecesarios a la IA.** Al modelo se le envía la evidencia y la lista de nombres de pila de la sala, nada más: ni RUT, ni fecha de nacimiento completa, ni dirección, ni datos de la familia.
6. **Acceso por rol.** La tía ve solo su(s) sala(s); la directora ve su jardín. Todo cambio de evaluación guarda quién lo hizo y cuándo.
7. **Datos de prueba 100% ficticios.** Nunca usar nombres reales de niños, jardines ni personas. Ningún RUT, ni siquiera inventado.
8. **Nada de datos sensibles en la URL** (nada de `?nino=Martina`; usar IDs).
9. **No usar `console.log` con datos de niños** en el código final.
