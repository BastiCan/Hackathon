# Huellita

App para que las tías de Fundación Integra registren evidencias del desarrollo de los niños y niñas en 2 toques. La IA las ordena por niño/a, núcleo y nivel (1–8), y la tía solo confirma.

Hackathon AWS Breaking Barriers Chile 2026 · Desafío 1 de Fundación Integra.

## Estructura
- `.kiro/steering/`: reglas permanentes del proyecto (producto, privacidad, interfaz, rúbrica y tecnología).
- `.kiro/specs/app-tias/`: requisitos, diseño y plan de tareas por fases.
- `.kiro/diseno/prototipo.html`: referencia visual obligatoria.
- `DEMO.md`: guion de la demo de 3 minutos.
- `PROGRESO.md`: qué se hizo en cada tanda de tareas.
- `PENDIENTES.md`: lo detectado que queda fuera del spec o de esta fase.
- `data/rubrica_8_niveles.json`: rúbrica de 8 núcleos × 8 niveles con conductas observables (derivada de las BCEP 2018).
- `data/catalogo_oa_bcep.json`: los 206 Objetivos de Aprendizaje de las BCEP 2018.
- `data/semilla.json`: datos ficticios de la demo (1 jardín, 3 salas, 36 niños/as, historial y guiones de captura).
- `data/demo/`: fotos de post-its de ejemplo (de la presentación del desafío), solo para probar la lectura en la Fase 3.

## Fases
1. Interfaz completa con datos locales e IA simulada (sin AWS).
2. Login y datos en AWS Amplify (Cognito, DynamoDB y S3).
3. IA real: Bedrock (Claude visión y clasificación) y Transcribe.
4. Vista directora y privacidad avanzada (Rekognition para difuminar caras, Guardrails).
