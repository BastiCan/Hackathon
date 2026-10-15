# DEMO.md · Huellita en 3 minutos

Recorrido para mostrar la Fase 1 (datos de prueba, Huellita simulada, sin AWS).

## Antes de empezar

```powershell
npm install        # solo la primera vez
npm run dev        # http://localhost:5173
```

Para la presentación conviene `npm run build` + `npm run preview`: es la misma app
pero con el service worker activo, así se puede mostrar que funciona sin red.

- Celular o ventana angosta (**390 px**). En el inspector de Chrome: iPhone 14.
- Si quedó algo de un ensayo anterior: menú de la tía (círculo "TA" arriba a la
  derecha) → **Reiniciar demo**. Vuelve la semilla tal cual y aparece la pantalla
  de entrada.
- La fecha de la demo es fija (**jueves 15 de octubre de 2026**), así los
  semáforos y los días siempre salen igual.

## Guion (6 pasos, ~3 minutos)

### 1. Entrar como tía Ana · Mi sala (25 s)

Elegir **"Tía Ana · Medio Menor A"**.

Qué mostrar:
- la **pila de post-its**: "3 notas por revisar · Huellita ya las ordenó";
- la grilla de 18 niños/as con **iniciales, nunca fotos**;
- el **aro de frescura**: verde, amarillo y rojo. Toca el **"?"**: el aro dice
  hace cuánto no se registra algo, **no** cómo le va al niño o niña;
- **Josefa**, con la **bandera ámbar** de "revisar avance" (2 registros seguidos
  bajo lo esperado para su edad, en Lenguaje Verbal);
- abajo: "Observados en 30 días: **16 de 18** · Menos registrado: …" (el mismo número que ve la directora).

Frase: *la tía abre la app y en 2 segundos sabe a quién le falta observar.*

### 2. Foto del post-it (30 s)

Toca **Foto** (círculo izquierdo del dock) y saca una foto a cualquier cosa, o
usa la foto de `data/demo/postits_presentacion.png`.

- Aparece el aviso **"Listo, lo verás en Revisar"** y la pantalla **no se
  bloquea**: Huellita lee mientras la tía sigue en la sala.
- El globo rojo de **Revisar** pasa de 3 a 4.

Toca **Revisar**: la primera nota es el post-it de **Josefa**
("…se agacha y recoge los individuales, los ordena y se los pasa a la tía"),
con la cita en letra manuscrita y, pegada debajo, lo que Huellita leyó:
Josefa · **Segura** · nivel **4 Afianzando** · Convivencia y Ciudadanía · la
conducta observable de la rúbrica.

### 3. Aceptar y ver la ficha (25 s)

Toca **Guardar** (verde) → aviso con **Deshacer** por 5 segundos.

Vuelve a **Mi sala** y entra a **Josefa**:
- el resumen en 2 líneas;
- la tarjeta lima **"Para observar esta semana"**;
- **"Cómo va"**: cada núcleo como una escalera de 8 escalones pintada hasta su
  nivel; Lenguaje Verbal con su bandera;
- en **Registros**, arriba, el registro que acabamos de aceptar.

Frase: *la IA sugiere, la tía decide, y la ficha se ordena sola.*

### 4. Audio y "Cambiar" (40 s)

Toca **Audio** (botón grande azul del centro), di cualquier cosa 2 o 3 segundos
y toca **"Listo, enviar"** (se corta solo a los 60 s).

En **Revisar** aparece el guion de **Emilio**
("clasificó las hojas del otoño por tres colores…"), Pensamiento Matemático,
nivel 4, certeza **Revisar**.

Toca **Cambiar**: se abre la hoja con niño/a, núcleo y los **8 niveles con su
descriptor**. Elige **5 Integrando** y **Guardar cambio**.

Frase: *nunca se guarda una evaluación sin que la tía la confirme, y queda
registrado que ella la cambió.*

### 5. Una nota que no evalúa a nadie (20 s)

Toca **Texto** y escribe:

> Hoy bajó la asistencia, los niños comenzaron a resfriarse y han estado con mucha tos.

En **Revisar** esa nota llega como **"Nota de la sala"**, sin niño ni nivel, con
los botones **"Guardar en la sala"** o descartar. Guárdala.

Si quedan notas, toca **"Aceptar las seguras (N)"** para mostrar el atajo, y
luego **Deshacer**. Cuando no queda nada: **"¡Todo al día!"**.

### 6. Entrar como directora (20 s)

Menú de la tía → **Cambiar de usuaria** → **"Directora Carmen"**. Entra directo
al resumen de todas las salas (destino **Directora** en la barra inferior).

- Una tarjeta por sala: **observados en los últimos 30 días**, cuántos están por
  **revisar avance** y el **núcleo menos registrado**.
- Toca **Medio Menor A**: se abre su Mi sala en **modo lectura**, y al tocar un
  niño/a se puede **Ver su ficha**, **Mover de sala** o **Dar de baja** (las dos
  últimas piden confirmación y solo cambian los datos de la demo).

## Cierre (15 s)

- Hoy: **4 horas a la semana** pasando notas en limpio.
- Con Huellita: 3 toques por evidencia y la tía solo confirma.
- Privacidad: **sin reconocimiento facial**, avatares con iniciales, las fotos y
  audios **no salen del teléfono** en esta fase y en las URLs solo viajan IDs.

## Si algo se cae en vivo

| Problema | Qué hacer |
|---|---|
| No hay permiso de micrófono | La app ofrece **"Escribir la nota"**: sigue con el paso 5. |
| La cámara no abre (escritorio) | El botón **Foto** abre el selector de archivos; usa `data/demo/postits_presentacion.png`. |
| Se desordenó la demo | Menú de la tía → **Reiniciar demo**. |
| Se acabaron los guiones de foto y audio | Vuelven a empezar solos; también sirve escribir una nota con un nombre de la sala ("Martina armó una torre de 6 bloques y contó hasta 5"). |

El recorrido completo está cubierto por una prueba automática
(`src/app/demo.test.tsx`): corre los 6 pasos después de "Reiniciar demo", así que
si algún cambio lo rompe, `npm test` avisa.
