# Huellita · formato mejorado

App para que las tías de Fundación Integra registren evidencias del desarrollo de los niños y niñas en 2 toques. La IA las ordena por niño/a, núcleo y nivel (5 núcleos y 9 niveles, la misma rúbrica del backend), y la tía solo confirma.

Hackathon AWS Breaking Barriers Chile 2026 · Desafío 1 de Fundación Integra.

## Estructura
- `.kiro/steering/`: reglas permanentes del proyecto (producto, privacidad, interfaz, rúbrica y tecnología).
- `.kiro/specs/app-tias/`: requisitos, diseño y plan de tareas por fases.
- `.kiro/diseno/prototipo.html`: referencia visual obligatoria.
- `DEMO.md`: guion de la demo de 3 minutos.
- `PROGRESO.md`: qué se hizo en cada tanda de tareas.
- `PENDIENTES.md`: lo detectado que queda fuera del spec o de esta fase.
- `data/rubrica_e1.json`: rúbrica E-1, **copia exacta** de `integra-backend/data/processed/rubrica.json` (5 núcleos × 9 niveles de 0 a 36 meses, 90 conductas observables). Si el backend la cambia, se vuelve a copiar; una prueba avisa si quedan distintas.
- `data/nucleos_e1.json`: nombre visible y sigla de cada núcleo (lo único que el backend no trae).
- `data/catalogo_oa_bcep.json`: los 206 Objetivos de Aprendizaje de las BCEP 2018 (referencia; la app no lo usa).
- `data/semilla.json`: datos ficticios de la demo (1 jardín, 3 salas, 36 niños/as, historial y guiones de captura).
- `data/demo/`: fotos de post-its de ejemplo (de la presentación del desafío), solo para probar la lectura en la Fase 3.

## Fases
1. Interfaz completa con datos locales e IA simulada (sin AWS).
2. Login y datos en AWS Amplify (Cognito, DynamoDB y S3).
3. IA real: Bedrock (Claude visión y clasificación) y Transcribe.
4. Vista directora y privacidad avanzada (Rekognition para difuminar caras, Guardrails).

## Formato mejorado
Esta carpeta es la versión con el **formato mejorado** de Huellita. La versión anterior (diseño de post-its) está en la carpeta `huellita/` del repositorio, sin cambios.
- **Inicio**: la semana, el aviso de lo que falta revisar, la sala del registro y 4 botones: subir foto, grabar audio, escribir y subir audio.
- **Sala**: planilla por núcleo con el número de cada nivel en su color (un color por nivel, del 1 al 9). Revisar con la foto real del post-it y ficha por núcleo.
- Una sola tipografía (Carlito, equivalente de Calibri) y la paleta del manual de Integra; encabezado institucional.
- **Para el backend:** cada evidencia puede traer `foto` (imagen del post-it) y `textoExtraido`, y `evidencias()` debe devolverlas en orden de llegada; los núcleos usan el código `dominio` del backend (`motor_grueso`…) y los niveles van del 1 al 9. El audio subido sigue las reglas del transcriptor (`servicio_transcripcion`): formato por sus primeros bytes y hasta 4 MB. Ver `PROGRESO.md`.
- `huellita-demo.html`: la app completa en un solo archivo (doble clic).
