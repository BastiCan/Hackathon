---
inclusion: always
---

# Sistema de evaluación: núcleos, niveles y rúbrica

## La rúbrica es la del backend (E-1)
- Huellita usa la misma rúbrica que `integra-backend`: una escala continua de **9 niveles (0 a 36 meses) en 5 núcleos**, con **2 conductas observables por nivel y núcleo** (90 en total, cada una con su código `MAN-LNN-DD-NN`).
- `data/rubrica_e1.json` es **copia exacta** de `integra-backend/data/processed/rubrica.json` (la prueba de `src/lib/rubrica.test.ts` avisa si se desalinean). `data/nucleos_e1.json` agrega solo lo que el backend no trae: el nombre visible y la sigla de cada núcleo. **Son la única fuente de verdad**: el código carga núcleos, niveles y conductas desde ahí y nunca los escribe a mano.
- Los núcleos son **configuración** (lista cargada desde datos), en el orden del backend. El código del núcleo es el `dominio` del backend:

| Código | Sigla | Núcleo |
|---|---|---|
| motor_grueso | MG | Motor grueso |
| motor_fino | MF | Motor fino |
| lenguaje_comunicacion | LC | Lenguaje y comunicación |
| socioemocional | SE | Socioemocional |
| cognitivo | CO | Cognitivo |

## Los 9 niveles
| Nivel | Nombre | Edad orientativa |
|---:|---|---|
| 1 | Atención y regulación inicial | 0–2 meses |
| 2 | Interacción y control emergente | 2–4 meses |
| 3 | Alcance y exploración corporal | 4–6 meses |
| 4 | Sedestación y comunicación intencional | 6–9 meses |
| 5 | Movilidad y propósito | 9–12 meses |
| 6 | Autonomía funcional inicial | 12–18 meses |
| 7 | Representación y combinación inicial | 18–21 meses |
| 8 | Combinación y participación | 21–27 meses |
| 9 | Secuencias y autonomía creciente | 27–36 meses |

- El dataset E-1 es sintético y no es un instrumento clínico validado: Integra debe validar el contenido.
- `data/catalogo_oa_bcep.json` (los 206 OA de las BCEP 2018) queda solo como referencia; la app no lo usa.

## Reglas de cálculo (implementar en `src/lib/evaluacion.ts`, con pruebas)
- **Edad en meses** = meses completos entre la fecha de nacimiento y la fecha de referencia.
- **Niveles esperados por edad** = los niveles cuyo rango [mínimo, máximo] contiene la edad, con **bordes inclusivos** como en el backend (12 meses → 5 y 6). Sobre 36 meses queda el 9 (fuera del rango de la rúbrica).
- **Nivel esperado** = el menor de los niveles esperados: el mismo piso que usa el backend para "bajo lo esperado", así en un borde nunca se le pide de más a un niño/a.
- **Nivel actual de un núcleo** = el nivel de la evidencia **validada** más reciente de ese núcleo. Si no hay evidencia, el núcleo queda "sin evidencia" (no 0).
- **Nivel general del niño/a** = mediana redondeada hacia abajo de los niveles actuales de los núcleos con evidencia.
- **Revisar avance** (bandera) en un núcleo = las **2 últimas evidencias validadas** de ese núcleo, de fechas distintas, tienen cada una nivel ≤ (nivel esperado **para la edad que tenía el niño/a en la fecha de esa evidencia**) − 2. Nunca se marca con una sola evidencia.
- **Frescura** = días desde la última evidencia validada (de cualquier núcleo): < 14 verde, 14–30 amarillo, > 30 o ninguna rojo.
- **Observar ahora** = elegir el núcleo con la evidencia validada más antigua (o sin evidencia) y mostrar 1–2 conductas observables del nivel actual + 1 de ese núcleo (o del nivel esperado si no hay evidencia).
- **Sugerencia**: como en el backend, el núcleo, el nivel y la conducta salen de la conducta de la rúbrica que mejor calza con la nota, nunca de la edad. Si ninguna calza bien, la IA simulada propone el nivel actual del niño/a en ese núcleo (o el esperado) con certeza media.
- **Certeza** de una sugerencia: Alta si el nombre coincide exacto con un niño/a de la sala **y** la evidencia describe una conducta reconocible de la rúbrica; Media si solo una de las dos condiciones se cumple; Baja en otro caso.
