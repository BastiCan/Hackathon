---
inclusion: always
---

# Producto: Huellita

## Contexto
Hackathon AWS Breaking Barriers Chile 2026, desafío 1 de Fundación Integra: "IA para el Desarrollo Infantil: de la Observación a la Acción".

Integra atiende a más de 85.000 niños y niñas en más de 1.200 jardines y salas cuna. Cada tía (educadora o técnica de párvulos) dedica en promedio **4 horas a la semana** a pasar en limpio sus observaciones para saber en qué nivel de desarrollo está cada niño/a. Son 11.000 horas semanales a nivel institucional que no se pasan en la sala.

Hoy las tías observan durante el juego y las rutinas, y anotan en **post-its**, cuadernos, fotos y audios. Lo que les quita tiempo es juntar, ordenar y convertir esas notas en evaluaciones por núcleo y nivel, que después alimentan el IEA (Instrumento de Evaluación para el Aprendizaje). El IEA se completa 3 veces al año: abril, agosto y noviembre.

## Qué es Huellita
Una app web móvil (PWA) donde la tía:
1. **Captura** en 2 toques una evidencia: foto del post-it (sacada o de la galería), audio de voz (grabado o una nota de voz ya grabada) o texto corto, en la sala que elige.
2. La IA **lee, identifica al niño/a, el núcleo, la conducta observable y sugiere un nivel** (1–9, rúbrica E-1 del backend) con su certeza.
3. La tía **confirma, cambia o descarta** la sugerencia con un toque.
4. Todo se ordena solo en la **ficha del niño/a** y en el **panel de la sala**, que muestra a quién falta observar y quién necesita apoyo.

## Usuarias
- **Tía de sala** (principal): usa el celular con una mano, muchas veces con un niño en brazos. Tiene poco tiempo y conocimiento técnico variable. Necesita que todo sea rápido, claro y en español simple de Chile.
- **Directora del jardín** (secundaria): revisa el avance de todas las salas, por lo general desde un computador.

## KPI
Bajar el tiempo de documentación de **4 h/semana a menos de 15 min/semana**. Toda decisión de diseño se evalúa contra esto: si agrega toques o formularios, está mal.

## Principios no negociables
- **La IA sugiere y la tía decide.** Nunca se guarda una evaluación sin validación humana.
- **No es diagnóstico.** Nunca usar la palabra "rezago" ni lenguaje clínico en la interfaz. Usar "revisar avance" o "reforzar".
- **La falta de registro no significa falta de aprendizaje.** El semáforo mide frescura de la evidencia, no desempeño.
- **Privacidad de los niños primero** (ver `privacidad.md`).
- El idioma de la interfaz es español de Chile, con tono cercano y simple ("tía", "sala", "jardín").
