---
inclusion: always
---

# Sistema de evaluación: núcleos, niveles y rúbrica

## Estructura (Bases Curriculares de la Educación Parvularia 2018)
- **3 ámbitos → 8 núcleos → 206 Objetivos de Aprendizaje (OA)**, repartidos en 3 tramos: Sala Cuna (hacia los 2 años), Medio (hacia los 4) y Transición (hacia los 6).
- Los 8 núcleos y sus códigos:

| Código | Núcleo | Ámbito |
|---|---|---|
| IA | Identidad y Autonomía | Desarrollo Personal y Social (transversal) |
| CC | Convivencia y Ciudadanía | Desarrollo Personal y Social (transversal) |
| CM | Corporalidad y Movimiento | Desarrollo Personal y Social (transversal) |
| LV | Lenguaje Verbal | Comunicación Integral |
| LA | Lenguajes Artísticos | Comunicación Integral |
| EN | Exploración del Entorno Natural | Interacción y Comprensión del Entorno |
| ES | Comprensión del Entorno Sociocultural | Interacción y Comprensión del Entorno |
| PM | Pensamiento Matemático | Interacción y Comprensión del Entorno |

## Los 8 niveles de Integra (rúbrica)
| Nivel | Nombre | Tramo | Edad orientativa |
|---:|---|---|---|
| 1 | Comenzando | Sala Cuna | 0–12 meses |
| 2 | Explorando | Sala Cuna | 12–24 meses |
| 3 | Desarrollando | Medio | 24–32 meses |
| 4 | Afianzando | Medio | 32–40 meses |
| 5 | Integrando | Medio | 40–48 meses |
| 6 | Ampliando | Transición | 48–56 meses |
| 7 | Consolidando | Transición | 56–64 meses |
| 8 | Profundizando | Transición | 64–72 meses |

- La rúbrica completa (8 núcleos × 8 niveles, con descriptor, conductas observables y OA de referencia) está en `data/rubrica_8_niveles.json`. **Es la única fuente de verdad**: el código la carga y nunca escribe niveles ni conductas a mano.
- Los 206 OA están en `data/catalogo_oa_bcep.json`.
- La presentación de Integra menciona **10 núcleos**, pero las BCEP definen 8. La app debe tratar los núcleos como **configuración** (lista cargada desde datos), para agregar más sin cambiar código.
- El contenido de cada nivel es una propuesta del equipo derivada de las BCEP; Integra debe validarlo.

## Reglas de cálculo (implementar en `src/lib/evaluacion.ts`, con pruebas)
- **Edad en meses** = meses completos entre la fecha de nacimiento y hoy.
- **Nivel esperado por edad** = el nivel cuyo rango de edad orientativa contiene la edad.
- **Nivel actual de un núcleo** = el nivel de la evidencia **validada** más reciente de ese núcleo. Si no hay evidencia, el núcleo queda "sin evidencia" (no 0).
- **Nivel general del niño/a** = mediana redondeada hacia abajo de los niveles actuales de los núcleos con evidencia.
- **Revisar avance** (bandera) en un núcleo = las **2 últimas evidencias validadas** de ese núcleo, de fechas distintas, tienen cada una nivel ≤ (nivel esperado **para la edad que tenía el niño/a en la fecha de esa evidencia**) − 2. Nunca se marca con una sola evidencia. Comparar con la edad en la fecha evita marcar a un niño/a por registros antiguos de cuando era más pequeño/a.
- **Frescura** = días desde la última evidencia validada (de cualquier núcleo): < 14 verde, 14–30 amarillo, > 30 o ninguna rojo.
- **Observar ahora** = elegir el núcleo con la evidencia validada más antigua (o sin evidencia) y mostrar 1–2 conductas observables del nivel actual + 1 de ese núcleo (o del nivel esperado si no hay evidencia).
- **Certeza** de una sugerencia: Alta si el nombre coincide exacto con un niño/a de la sala **y** la evidencia describe una conducta reconocible de la rúbrica; Media si solo una de las dos condiciones se cumple; Baja en otro caso.
