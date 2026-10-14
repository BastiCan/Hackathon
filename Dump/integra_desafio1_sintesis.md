# Desafío 1 Integra — IA para el Desarrollo Infantil: síntesis y propuesta

> Hackatón AWS Breaking Barriers Chile 2026 (14–16 oct, FCFM U. de Chile).
> Fuentes revisadas: `bb-assets-e1-presentation.pptx` (incluidas las fotos de cuadernos y post-its de la diapositiva 5), `Referente_Curricular_Fundacion_Integra_2025.pdf`, `Modelo-Educacion-Emocional.pdf`, los `.md` del `dataset_e1_publico`, el propio dataset (`observaciones.csv` y otros), la conversación con Integra y las ideas del grupo.

---

## 0. El problema en una línea

Hoy una tía dedica **unas 4 horas a la semana** a documentar a su grupo, lo que suma **más de 11 mil horas semanales** en toda la institución, cerca del **10 % de su jornada**. El KPI estrella es bajar de **4 a 0 horas**. Para Integra, lo central es que **la educadora pueda identificar rezagos** a tiempo.

---

## 1. Cómo evalúa Integra (según los documentos)

### 1.1 ¿Cómo se evalúa?

Es una **evaluación diversificada y auténtica** (Referente Curricular, cap. II, §3.2):

- **Es cualitativa y se hace observando** en situaciones auténticas. El juego es "una instancia auténtica y privilegiada para observar".
- **No hay pruebas ni actividades de evaluación aparte.** Es parte del día a día, "sin la necesidad de planificar una instancia evaluativa".
- **Se evalúa a cada niño según su propio proceso** (ritmos, gustos, formas de expresarse), no comparándolo con el grupo.
- **Se registran los aprendizajes emergentes**: lo que el niño aprende sin que estuviera planificado también es evidencia válida.

### 1.2 ¿Cómo se hace una evaluación? (el proceso)

1. **Recolección de información**: observación y registro cualitativo de lo que el niño dice y hace.
2. **Juicio valorativo**: el equipo analiza lo registrado y saca conclusiones (aquí se asigna el nivel).
3. **Sugerencias y toma de decisiones**: se ajusta la planificación y lo que se le ofrece a cada niño.

La herramienta oficial es la **documentación pedagógica**, que tiene 5 hitos: observación y escucha activa → registro (notas, fotos, audio, video, trabajos de los niños) → interpretación y análisis → compartir y conversar los hallazgos → planificación y acción.

Las tías ya hacen el registro en sala, en post-its y cuadernos. Lo que les consume las 4 horas de escritorio es la interpretación: pasar esas notas a núcleos y niveles.

### 1.3 ¿Qué aspectos se evalúan?

- **El aprendizaje del niño**, según los **núcleos de aprendizaje** de las BCEP, agrupados en 3 ámbitos:
  - Desarrollo personal y social: Identidad y autonomía, Convivencia y ciudadanía, Corporalidad y movimiento.
  - Comunicación integral: Lenguaje verbal, Lenguajes artísticos.
  - Interacción y comprensión del entorno: Exploración del entorno natural, Comprensión del entorno sociocultural, Pensamiento matemático.
- En los cuadernos la tía anota **núcleo + indicador**. Por ejemplo, Identidad y autonomía → "colaboración frente a necesidades de sus pares"; Lenguaje verbal → "expresión oral".
- **Lo socioemocional, que atraviesa todos los núcleos** (Modelo de Educación Emocional): 5 competencias (Conciencia emocional, Regulación emocional, Autoestima y autonomía emocional, Vínculos bientratantes, Compromiso social y ético), divididas en 23 microcompetencias. La tabla 10 del Modelo las conecta con cada núcleo.
- **Los contextos para el aprendizaje**: interacciones, espacio y recursos, tiempo, planificación y trabajo con familias. Se evalúa el ambiente, no al niño.

### 1.4 La rúbrica: hay diferencias entre las fuentes

| | PPT Integra (diap. 7) | Dataset E-1 |
|---|---|---|
| Niveles | **8**: Comenzando, Explorando, Desarrollando, Afianzando, Integrando, Ampliando, Consolidando, Profundizando | **9** niveles por edad (0–36 meses) |
| Ejes | **10 núcleos** | **5 dominios**: motor grueso, motor fino, lenguaje/comunicación, socioemocional, cognitivo |
| Tramo | Sala cuna, nivel medio, transición | Solo hasta 36 meses |

- Las BCEP tienen **8 núcleos**, no 10.
- El dataset aclara que su ruta es "una síntesis para una hackathon", no un instrumento validado.
- **Decisión:** la rúbrica real que tiene el equipo es la que manda. El dataset se usa para la demo. La rúbrica debe quedar como **tabla configurable** (núcleo × nivel × conductas observables) para que sirvan ambas.

### 1.5 Tipos de anotaciones que hace una tía (fotos de la PPT)

| Tipo | Ejemplo real |
|---|---|
| Registro individual de un hecho (el más común) | "Nayara 25-mayo-2026: cuando salía del baño se da cuenta que a la tía se le caen los individuales, ella se agacha, recoge los individuales, los ordena y se los pasa a la tía" |
| Cita textual del niño | Sofía mira por la ventana y dice "viene el Alexi" (su papá); Naiara: "tía mira la Pascal tiene moco" |
| Nota de progreso en el tiempo | "Rusi: la primera semana tenía más dificultades para hacer actividades de equilibrio, pero al pasar aprox. un mes se ve un gran avance, ya que logra pasar por circuitos de desafíos sin ayuda de adulto" |
| Lista corta de logros | "Sofía 25 abril: – sigue instrucciones – reconoce colores" |
| Nota grupal (diario mural) | "Esta semana los niños han tenido desregulaciones emocionales…", "hoy bajó la asistencia, mucha tos" → **Integra confirmó que no se usan; se descartan** |

- La estructura base es **`Niño: hizo tal cosa…`**.
- Las notas se toman **por actividad o zona**: en una misma página aparecen varios niños.
- El encabezado de la página dice zona, núcleo e indicador.
- Están escritas a mano, con fechas en formatos distintos y faltas de ortografía.

### 1.6 Frecuencia: ¿cada niño semanal o a fin de mes?

- **Ningún documento fija una frecuencia por niño.** Lo que dicen: la evaluación es un proceso "constante, sistemático y dinámico"; la información se recoge "diariamente"; la planificación de corto plazo se ajusta cada día, semana, quincena o mes.
- **Lo que muestra el dataset:** las observaciones vienen en rachas, unas 4 seguidas separadas por **5 días** (1.733 de 2.450 intervalos), que cubren los 5 dominios en unas 2–3 semanas. Después hay pausas de **2 a 5 meses**.
- **Conclusión:**
  - **El registro se hace en el momento.** A fin de mes se pierden las citas y los detalles.
  - **La sistematización puede ser periódica**, y eso es lo que hace la IA. Lo semanal es lo natural, y a fin de mes puede salir un informe.

---

## 2. Lo que aclaró Integra en la conversación

| Tema | Aclaración |
|---|---|
| Rúbrica | La tía tiene una rúbrica (el equipo la tiene) y revisa si el niño cumple con lo que dice. La evaluación es dinámica: en sala cuna se miran los cambios significativos en cómo se comporta el niño a lo largo del tiempo |
| Notas grupales | **No sirven para esto.** Solo se usan las individuales |
| ¿Toda nota es evaluación? | **No.** Hay notas que no entregan información relevante |
| Captura | Que siga usando post-its **y además audio**, rápido. Las dos formas se suben a la app |
| Rol de la IA | La IA trabaja por debajo: identifica al niño y **solo sugiere un nivel**. La tía puede cambiar el nivel y el enfoque |
| Usuarios | Una educadora fija por sala, más sus asistentes de párvulos, que también están siempre en esa sala. **Todas ven la app** |
| Video | Se saca la información y **el archivo se borra de la nube** después de un tiempo, por temas legales |
| Alerta | Si un niño no tiene información, avisar que podría estar quedándose atrás respecto a sus compañeros (ver §4 para un ajuste a esta idea) |

---

## 3. Flujo propuesto de la app

**Paso 1 – Captura (en sala, unos segundos)**
- Audio con la estructura que ya usan: *"Nayara: recogió los individuales y me los pasó"*.
- Foto del cuaderno o del post-it (puede traer varios niños).
- Video corto.
- Texto.

**Paso 2 – Procesamiento automático con IA**
1. **Pasar a texto**: transcribir el audio, leer la letra a mano, extraer audio y cuadros clave del video.
2. **Separar** las observaciones por niño. Un mismo audio puede traer varios: *"Pedro y Emilio clasificaron hojas por tamaño, Esperanza por colores"*.
3. **Identificar al niño** cruzando el nombre con la lista de la sala, usando un diccionario de apodos. Si es ambiguo, la app pregunta en vez de adivinar.
4. **Filtrar**: decidir si la nota es evaluable o no, y descartar las grupales.
5. **Asociar a la rúbrica**: sugerir núcleo, indicador y nivel, con certeza alta/media/baja y **la frase de la nota que lo justifica**.
6. **Privacidad**: reemplazar los nombres por IDs antes de enviar la nota al modelo. Borrar automáticamente el audio y el video originales con una regla de expiración del almacenamiento.

**Paso 3 – Validación (bandeja de la tía)**
- Con un toque acepta la sugerencia, cambia el nivel o cambia el enfoque (núcleo o indicador).
- Las correcciones quedan guardadas para mejorar el sistema y medir cuánto acierta la IA.

**Paso 4 – Seguimiento**
- Una ficha por niño con su trayectoria en cada núcleo.
- Una vista de la sala con alertas y la misión del día.

---

## 4. Cómo detectar rezagos (es el centro del proyecto)

### 4.1 Dos alertas distintas

- **🟡 Sin evidencia reciente**: no hay observaciones del niño, o no las hay en algún núcleo. Casi siempre significa que **nadie lo ha observado**, típicamente los niños tranquilos. El README del dataset lo advierte: "una ausencia de registro no implica ausencia de aprendizaje". La acción es **"obsérvalo"**.
- **🔴 Posible rezago**: hay evidencia, pero el nivel está bajo lo esperado. La acción es **"atención con su desarrollo"**.

### 4.2 Señales de rezago (por niño y por núcleo)

| Señal | Cálculo | Ejemplo |
|---|---|---|
| Bajo lo esperado para su edad | Se compara el nivel validado con el rango de edad en meses de cada nivel en la rúbrica | 14 meses y sigue en nivel 4 (lo esperado es 5–6) |
| Estancamiento | Mismo nivel durante N semanas mientras la edad sale del rango de ese nivel | 3 meses en nivel 5 |
| Retroceso | Baja de nivel entre observaciones confirmadas | En el dataset hay 25 niños con una baja |
| Bajo sus pares de edad similar | Posición del niño respecto a niños de ±2 meses de edad (en sala cuna, dos meses de diferencia cambian mucho lo esperable) | Está en el 10 % más bajo de su grupo de edad |

### 4.3 Reglas

- **Hay que confirmarla.** Se necesitan al menos 2 observaciones que coincidan, o una observación dirigida (ver §7).
- **Pesa más si afecta varios núcleos.** En ese caso, sugerir **evaluar una derivación** a redes especializadas, como plantea el Referente.
- **Se cruza con la asistencia.** Si el niño faltó, no tener evidencia no es un rezago.

---

## 5. Ideas del grupo, ordenadas por módulo

| Módulo | Qué incluye | Quién lo propuso |
|---|---|---|
| A. Acceso y estructura | Inicio de sesión ligado a jardín → sala → niños. Roles: tía, asistente y directora. Las tías de la sala ven lo que suben las demás. Mover niños de sala o darlos de baja | Flo, Cris, Lucas |
| B. Captura | Botón grande para audio, foto, video o texto. Widget rápido que envía directo a la base de datos. Subir algo dentro de la ficha de un niño | Flo, Basti, Cris, Agustín |
| C. Procesamiento con IA | Leer post-its, audio, video e imagen. Separar observaciones y detectar qué niños aparecen. Decidir si es evaluación. Sugerir nivel con certeza, con botones para aceptar o reemplazar. Guardar quién registró y cuándo | Flo, Agustín, Lucas |
| D. Vista de sala | Todos los niños con colores. Tiempo desde la última evaluación. Avance de la sala. Resumen de lo que anotaron las otras tías | Flo, Basti, Cris, Agustín, Lucas |
| E. Ficha del niño | Resumen para refrescar la memoria. Anotaciones del año. Línea de tiempo por núcleo. Asistencia | Cris, Agustín, Lucas, Flo |
| F. Alertas | Niños sin retroalimentación hace tiempo. Bandeja de pendientes. Colores y notificaciones | Basti, Cris |
| G. Apoyo pedagógico | Recomendar área o experiencia según cada evaluación. Mostrar qué debería lograr el niño en su nivel | Lucas |
| H. Vista de directora | Vista general de las salas. Panel de las tías con quién registró | Basti, Lucas |
| Transversal | Simple, ágil, con colores. Web o app. Cuidar que no se vea a los niños | Flo |

---

## 6. Choques entre ideas y cómo resolverlos

1. **El color significa dos cosas.** Recomendación: **el color indica el estado** (🟢 al día · 🟡 sin evidencia · 🔴 posible rezago · ⚪ ingreso reciente o datos insuficientes) y **el nivel va como número** dentro de la tarjeta.
2. **Notificaciones durante la clase.** Van contra el objetivo de que la tía esté más presente en la sala. Mejor un **aviso al inicio de la jornada** (la misión del día). Solo un rezago grave confirmado debería notificar en el momento.
3. **Panel de tías.** Presentarlo como **cobertura de la sala** ("estos niños nadie los ha observado"), no como un ranking ni una herramienta de fiscalización.
4. **Asistencia.** El dataset no la trae. Dejarla en el modelo de datos como campo opcional, para conectarla después con el sistema que Integra ya tenga.
5. **Certeza.** El porcentaje de un LLM no es una probabilidad real. Mostrar **alta/media/baja** y siempre con la evidencia textual.

---

## 7. Ideas nuevas

1. **🎯 Misión del día.** Al empezar la jornada, la app sugiere 3 a 5 niños para observar hoy (sin evidencia o con posible rezago) y **qué conducta mirar** según la rúbrica del nivel siguiente. Ejemplo: *"Nayara · Lenguaje verbal: fíjate si ya combina dos palabras"*.
2. **🔍 Observación dirigida para confirmar un rezago.** La app propone una experiencia de juego concreta para comprobar la alerta (*"circuito motor: ¿sube y baja un escalón sin apoyo?"*). La tía graba un audio y la alerta se confirma o se descarta.
3. **🗺️ Mapa de cobertura.** Tabla de niños × núcleos, con cada celda pintada según qué tan reciente es la evidencia y el estado. En una pantalla se ven los vacíos y los rezagos.
4. **🎙️ Un audio, varios niños.** Separación automática, igual que en los cuadernos.
5. **🔒 Seudonimización y borrado automático.** Nombres reemplazados por IDs antes de ir al modelo, caras difuminadas si alguna foto se guarda, y borrado automático de audio y video. Conviene tener en cuenta la Ley 21.719 de datos personales, que entra en vigencia en diciembre de 2026.
6. **📴 Funciona sin conexión.** Una página web instalable en el celular (PWA) que graba sin internet y sincroniza después. Integra está en 320 comunas, incluidas zonas rurales.
7. **🗣️ Diccionario de la sala.** Apodos y modismos ("Rusi", "la Sofi") para identificar bien a los niños.
8. **📝 Borradores automáticos.** Resumen semanal para la reunión del equipo y borrador del **Informe al Hogar** de cada niño.
9. **📈 Aprender de las correcciones.** Medir el **% de acuerdo entre la IA y la tía** y usar las correcciones como ejemplos para mejorar las sugerencias.
10. **📊 Métricas de impacto.**
    - Minutos por observación.
    - % de niños con evidencia en todos los núcleos en los últimos 30 días.
    - Días desde la primera señal hasta que se confirma un rezago.
    - Horas de escritorio ahorradas.

---

## 8. Pantalla principal de la tía

```
┌──────────────────────────────────────────────┐
│ Sala Caracolitos · Tía Mercedes      [Hoy ▾] │
├──────────────────────────────────────────────┤
│  🎯 Misión de hoy: Nayara (LV) · Pedro (CM)  │
│                    · Sofía (sin evidencia)   │
├──────────────────────────────────────────────┤
│      [ 🎙️ AUDIO ]  [ 📷 FOTO ]  [ 🎬 VIDEO ]   │
│              [ ✏️ texto ]                     │
├──────────────────────────────────────────────┤
│ Por revisar (3)                               │
│  Nayara · Conv. y ciudadanía · Nivel 5 · alta │
│  "recogió los individuales y se los pasó"     │
│                       [✓ Aceptar] [✎ Cambiar] │
├──────────────────────────────────────────────┤
│ Mi sala   🟢🟢🟡🔴🟢⚪🟢🟡 …  (toca un niño)   │
└──────────────────────────────────────────────┘
```

- **Ficha del niño**: resumen, línea de tiempo por núcleo, anotaciones de todas las tías, asistencia y un botón para subir algo solo para ese niño.
- **Directora**: lo mismo, pero con todas las salas y la lista de rezagos confirmados.

---

## 9. Priorización para la hackatón

| Prioridad | Qué incluye |
|---|---|
| **Imprescindible (la demo)** | Captura de audio y foto → IA (separar, identificar, sugerir nivel con evidencia) → bandeja para aceptar o cambiar → vista de sala con semáforo → ficha con línea de tiempo por núcleo → las dos alertas → misión del día |
| **Si alcanza** | Vista de directora, mapa de cobertura, seudonimización, borrado automático de archivos |
| **Para el pitch** | Video, modo sin conexión, recomendador de experiencias, Informe al Hogar, asistencia, cambio de sala, aprender de las correcciones |

El dataset trae 500 niños, 2.950 observaciones, 20 jardines y 25 bajas reales. Hay que inventar dos cosas: **notas no evaluables** (como ejemplos negativos) y **audios de ejemplo**.

---

## 10. Preguntas abiertas para Integra

1. Compartir la **rúbrica real**: núcleos, 8 niveles y conductas observables.
2. ¿"Cambiar el enfoque" significa elegir otro núcleo o indicador, o algo más?
3. ¿Cuánto tiempo se guardan los videos y audios antes de borrarlos?
4. Permisos: ¿las asistentes pueden validar niveles o solo registrar?
5. ¿Después de cuántas semanas sin evidencia en un núcleo debería saltar la alerta?
6. ¿Hay un sistema de asistencia con el que se pueda conectar la app?

---

## 11. Resumen

- Integra evalúa **observando de forma cualitativa** en el juego y la rutina, y registra en post-its y cuadernos con la estructura `Niño: hizo tal cosa`, por núcleo e indicador. La sistematización es lo que hoy consume 4 horas semanales.
- La app recibe **audio (prioritario), foto y video**. La IA separa, identifica, filtra lo que no es evaluable y **sugiere** un nivel. La tía **decide**.
- Los rezagos se detectan con 4 señales: bajo lo esperado para la edad, estancamiento, retroceso y bajo sus pares. La alerta se confirma con más de una observación y se separa de "sin evidencia".
- Las ideas del grupo se ordenan en 8 módulos. Hay 5 choques resueltos; el más importante es que **el color muestre el estado y no el nivel**.
- Ideas nuevas clave: **misión del día**, **observación dirigida**, **mapa de cobertura** y **seudonimización con borrado automático**.
- **Lo siguiente es conseguir la rúbrica real** y construir la demo sobre el dataset.
