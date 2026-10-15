---
inclusion: always
---
# Reglas de dominio (decisiones del equipo — no cambiarlas sin preguntar)

## 1. Rúbrica y edad
La rúbrica del dataset es **una sola escala continua** de 9 niveles (0–36 meses) con dos archivos que se usan juntos:
- `ruta_niveles.csv`: por nivel, su **rango de edad orientativo** (`edad_min_meses`–`edad_max_meses`) y una **descripción integradora**.
- `manifestaciones.csv`: por nivel y dominio, las **conductas observables** concretas (2 por nivel × dominio = 90).

**No hay ventana por edad ni por tramo.** La búsqueda (RAG) y el LLM consideran **todos los niveles**. Los niveles lejanos no se
confunden; la dificultad real está entre **niveles vecinos** y se resuelve con el detalle de la conducta (§5), no filtrando.

### La edad se usa SOLO en código, después de evaluar
- `edad_meses` = meses completos entre `fecha_nacimiento` y la fecha de la nota (fórmula del diccionario:
  `12*(a2-a1)+(m2-m1)-1[d2<d1]`, mínimo 0).
- `niveles_esperados` = niveles cuyo rango `[edad_min_meses, edad_max_meses]` contiene la edad (bordes inclusivos, así que
  en un borde hay dos: 12 meses → [5, 6]). Si la edad supera 36 meses → [9] con `fuera_de_rango_rubrica = true`; en ese caso
  un nivel 9 se marca `ACORDE` (con la bandera) y uno menor `BAJO_LO_ESPERADO`.
- `comparacion_edad` del nivel sugerido: `BAJO_LO_ESPERADO` (nivel < mín), `ACORDE`, `SOBRE_LO_ESPERADO` (nivel > máx).
- Es **información, no alarma**: una sola observación muestra lo que el niño/a hizo ese día (un piso), no su techo. Un niño de
  30 meses que "camina" no está atrasado; la tía solo anotó que caminaba. Las alertas de rezago vendrán después, con varias
  observaciones.
- El código **agrega esta información al `comentario`** de la sugerencia, en lenguaje simple (ej.: "Para su edad (31 meses) lo
  esperado es el nivel 9; esta observación muestra una conducta de nivel 8."). Así la tía la ve sin que el LLM conozca la edad.

Valores de referencia para los tests de `edad.py`:
| edad_meses | niveles_esperados |
|---|---|
| 0 | [1] |
| 2 | [1, 2] |
| 5 | [3] |
| 12 | [5, 6] |
| 14 | [6] |
| 24 | [8] |
| 31 | [9] |
| 40 | [9] + fuera_de_rango_rubrica |

### Qué ve el LLM y qué no
- **Sí**: las descripciones de los 9 niveles (`ruta_niveles`) y las manifestaciones candidatas que trae la búsqueda (de cualquier nivel).
- **No**: edad, nivel esperado ni historial del niño/a. Si el modelo sabe que el niño tiene 31 meses, tiende a sugerir el nivel 9
  y esconde justo los rezagos. Por eso la comparación con la edad la hace el código.

## 2. Tipos de resultado
- `Observacion.tipo`: `PARTICULAR` | `GENERAL` | `NO_IDENTIFICADO`
- `NO_IDENTIFICADO.error`: `NO_ENCONTRADO` (0 candidatos) | `AMBIGUO` (≥2) | `FUERA_DE_SALA` (el nombre es de otra sala del mismo jardín). Siempre con `candidatos` (top 3 por similitud).
- `Observacion.evaluabilidad` (solo PARTICULAR): `EVALUABLE` | `NO_EVALUABLE`
- `NO_EVALUABLE.motivo`: `ESTADO_O_SALUD` | `JUICIO_SIN_CONDUCTA` | `CONDUCTA_ADULTO` | `LOGISTICA_O_FAMILIA` | `OTRO`
- **Clasificación = códigos de manifestación.** El LLM solo elige `id_manifestacion` (de las 90; el esquema no permite
  inventar códigos). **Nivel, dominio y texto_observable NO los genera el LLM**: salen de un cruce con
  `data/processed/rubrica.json` (`MAN-L08-LC-01` → nivel 8, lenguaje_comunicacion, "Combina dos palabras…"). Es solo una
  sugerencia: la tía puede aceptarla, cambiarla o descartarla.
- Resultado por observación PARTICULAR evaluable:
  - `manifestaciones`: lista de `{id_manifestacion, nivel, dominio, texto_observable, frase_evidencia, certeza}` (máx. 3).
  - `nivel`: el nivel del código con mayor certeza (empate → el que más se repite). **No evaluable o sin correspondencia →
    `nivel = null`** (nunca 0: un 0 parecería un nivel real bajo el 1 y ensuciaría promedios y gráficos).
  - `certeza`: la del código elegido como `nivel` (`alta` | `media` | `baja`, §5).
  - `comentario`: por qué ese código; si **otro código es viable**, cuál y qué detalle lo definiría; y la nota de edad (§1).
  - Respaldo: `otro_codigo_viable`, `edad_meses`, `niveles_esperados`, `comparacion_edad`.
- Errores a nivel de captura (rechazan la nota completa): `TEXTO_VACIO`, `EDUCADORA_DESCONOCIDA`, `SALA_DESCONOCIDA`.
- Los errores de identificación son **por fragmento**: la captura sigue procesando los demás.

## 3. Separación e identificación
- Un fragmento con N sujetos ("Pedro y Emilio clasificaron hojas") → N observaciones con el mismo texto.
- **Sujeto ≠ mencionado**: en "Naiara: 'tía mira la Pascal tiene moco'" el sujeto es Naiara; Pascal no recibe observación.
- Adultos nombrados ("viene el Alexi", su papá) no generan observaciones.
- `texto_literal` debe existir en el original (comparación normalizada: minúsculas, sin tildes, espacios colapsados).
- Apodos y errores de lectura: "la Sofi" → Sofía; "Naiara" ≈ "Nayara". El LLM propone, `nombres.py` confirma contra la nómina.

## 4. Evaluabilidad (criterio del equipo)
Un fragmento particular es **evaluable** si cumple TODO:
1. Describe una **conducta observable** del niño/a (hace, dice, gesticula).
2. La conducta es **del niño/a**, no del adulto ("le cambié el pañal" ✗).
3. No es solo un **estado o dato de salud** ("llegó con sueño", "tiene fiebre" ✗).
4. No es un **juicio sin conducta** ("estuvo precioso", "se portó bien" ✗).
5. No es **logística o familia** ("lo retiran temprano" ✗).
6. Se relaciona con al menos un dominio de la rúbrica.

Ante la duda entre EVALUABLE y NO_EVALUABLE → **EVALUABLE** (la tía rechaza con un toque; la evidencia perdida no se recupera).
Las NO_EVALUABLE se guardan igual, nunca se borran.

## 5. Evaluación de nivel
- Primero se extraen **conductas atómicas** con atributos `iniciativa`, `apoyo`, `complejidad`, `tipo_contenido`.
- La búsqueda usa la **acción interpretada**, no el texto crudo, sobre las **90 manifestaciones** (sin filtro de nivel). Como los
  vecinos se parecen (L07-MG-02 y L09-MG-02 dicen ambos "sube peldaños"), la búsqueda trae a los dos y el LLM decide por el detalle.
- El LLM usa **juntas** la descripción del nivel (visión integradora) y la manifestación (evidencia concreta) para elegir el código.
- Rasgos que separan vecinos (el LLM debe fijarse en ellos): pasos de una instrucción (L06-LC-02 uno / L08-LC-02 dos), palabras
  combinadas (L08-LC-01 dos / L09-LC-01 tres o más), apoyo al subir (L07-MG-02 con apoyo o gateando / L09-MG-02 alternando o
  reuniendo los pies), bloques (L06-MF-01 dos / L08-MF-01 cuatro o más), imitar vs colaborar (L06-SE-02 / L09-SE-02).
- Una observación puede generar sugerencias en **varios dominios**.
- **Few-shot**: el prompt incluye los 9 ejemplos resueltos de `data/processed/fewshot.json` (1 por nivel). Sus códigos,
  observaciones y niños están excluidos de la validación (`tests/fixtures/validacion_100.json`).
- **Consolidación** de `N_CORRIDAS_EVALUAR` corridas (candidatas barajadas en cada una), por código:
  - Se queda un código si lo eligió la **mayoría** de las corridas.
  - `certeza` del código: **alta** si lo eligieron todas y ninguna marcó `otro_codigo_viable`; **media** si lo eligió la mayoría
    o alguna marcó otro código viable; **baja** si ningún código tuvo mayoría (entonces se toma el más votado).
  - Los códigos votados por una minoría se mencionan en el `comentario` como alternativas ("Otra lectura: MAN-L08-LC-02").
  - `comentario` final = comentario del LLM de una corrida mayoritaria + alternativas + nota de edad del código.
- Todo código debe existir en `rubrica.json` (lo garantiza el esquema) y `frase_evidencia` debe ser literal del fragmento.

## 6. Casos de prueba canónicos (notas reales de la PPT de Integra)
Versión ejecutable con niños/as reales del dataset y resultado esperado: `tests/fixtures/notas_prueba.json` (15 casos)
sobre `tests/fixtures/nomina_demo.json`. En esa nómina, "Naiara" es variante de escritura de Nayara (NINO-00487).

| Nota | Esperado |
|---|---|
| "Nayara: cuando salía del baño se da cuenta que a la tía se le caen los individuales, ella se agacha, recoge los individuales, los ordena y se los pasa a la tía" | EVALUABLE; socioemocional nivel 9 (colaboración espontánea); NO debe quedar solo como motor grueso nivel 6 |
| "Sofía mira por la ventana y dice 'viene el Alexi'" | EVALUABLE; lenguaje 8 o 9, certeza media; el comentario menciona el otro nivel; "Alexi" es adulto → sin observación |
| "Naiara: 'tía mira la Pascal tiene moco'" | 1 observación para Nayara (lenguaje 9); Pascal mencionado sin observación |
| "Rusi: la primera semana tenía más dificultades para hacer actividades de equilibrio, pero al pasar aprox. un mes se ve un gran avance, ya que logra pasar por circuitos de desafíos sin ayuda de adulto" | EVALUABLE; motor grueso; se evalúa el estado final; certeza media o baja, el comentario dice qué falta saber del circuito |
| "Sofía 25 abril: – sigue instrucciones – reconoce colores" | EVALUABLE; certeza media o baja; el comentario dice que podría ser otro nivel según si la instrucción era de uno o dos pasos |
| "Esta semana los niños han tenido desregulaciones emocionales" | GENERAL |
| "Hoy bajó la asistencia, mucha tos" | GENERAL |
| "Pedro llegó con sueño" | NO_EVALUABLE (ESTADO_O_SALUD), nivel null |
| "Pedro dijo 'no quiero' y empujó el plato" | EVALUABLE; lenguaje 7 u 8; comparacion_edad BAJO_LO_ESPERADO (31 meses → esperado 9), como información |
