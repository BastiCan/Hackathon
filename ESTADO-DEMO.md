# Estado de la demo Huellita — traspaso de turno

Última actualización: 16-10-2026 (madrugada). Autor del turno: Lucas (+ asistente).
Para: compañero/a que sigue el turno.

Este documento resume TODO lo que se logró en la sesión y qué queda pendiente, para que
puedas continuar sin contexto previo. Lee la sección "Lo primero que debes hacer" al final.

---

## 1. Resumen en una línea

El front Huellita (`huellita-formato-mejorado`) quedó conectado al backend real en AWS
(BFF `huellita-web`). **Texto y audio funcionan end-to-end y están verificados en vivo.**
La captura de **foto de post-it** está implementada y commiteada, pero **todavía NO
desplegada ni verificada contra AWS** (es el único paso que falta: FEAT-003).

**URL de la demo:** https://d3hs1azrtjzcei.cloudfront.net

---

## 2. Qué puede y qué no puede hacer la demo AHORA MISMO (en la URL)

> "Ahora mismo" = lo que está desplegado en AWS en este momento. La foto todavía no lo está.

### ✅ Funciona y está verificado en vivo contra AWS
- **Abrir la app**: arranca en **Inicio** (ya no existe la Agenda). Salas **SG-A** y **SG-B**.
- **Ver la sala y sus niños**: lista los 13 niños reales de SG-A desde DynamoDB.
- **Ver la ficha de un niño** y su historial.
- **Crear una nota de TEXTO** → la IA sugiere núcleo + nivel en **~13 s**. Verificado.
- **Crear una nota de AUDIO** → se transcribe y sugiere en **~13-20 s**. Verificado con
  `TEST TRANSCRIPTOR.m4a`.
- **Revisar y confirmar/corregir** una sugerencia (aceptar o devolver a pendiente). Verificado.
- **Archivar** una captura.

### ⚠️ Implementado pero NO desplegado todavía (pendiente FEAT-003)
- **Foto de post-it**: el código del BFF y del front ya está (commits `9d5e76f` y `3b26bac`),
  pero **no se ha hecho `sam deploy` ni se ha republicado el front**, así que en la URL
  todavía NO funciona. No la muestres hasta que FEAT-003 termine y se verifique (ver §5).

### ❌ No funciona / no mostrar
- **Editar una nota de sala**: el BFF no tiene ese endpoint; responde "no disponible".
  No lo pongas en el guion.
- **Vista de directora / cobertura**: no verificada con datos reales en este deploy. Trátala
  como no confirmada.

---

## 3. Lo que se logró esta sesión (orden cronológico)

1. **Merge de `origin/main` dos veces** en `feature/huellita-aws` (commits `e939785` y `4af4b15`),
   resolviendo conflictos semánticos hacia el **mundo de datos SG-A** del backend. Decisiones de
   producto aplicadas: **Inicio reemplaza Agenda** (se eliminó el flag `VITE_AGENDA`) y
   **color por nivel** (se eliminó `ambitos.ts`).
2. **Limpieza** de referencias obsoletas a `VITE_AGENDA` en docs del BFF (`200f853`).
3. **Deploy del backend** a AWS (`sam deploy`, stack `huellita-web`) y **publicación del front**
   a CloudFront con `VITE_DATOS=http`.
4. **Bug encontrado y arreglado**: `POST /api/capturas` daba 500 porque el BFF usaba el atributo
   `total` en una condición de DynamoDB, y `total` es palabra reservada. Se arregló con alias
   `#total` (commit `e658b0f`). El mock de los tests no lo detectaba; solo fallaba contra AWS real.
   Verificado con la prueba de humo end-to-end.
5. **Audio verificado** end-to-end: la transcripción funciona muy bien. (Ver §6 para el detalle
   de por qué los audios de prueba no daban buena sugerencia.)
6. **Investigación de `postits-ocr`**: resultó que esa Lambda **ya está desplegada** y escribe en
   el mismo bucket/contrato que dispara el pipeline de sugerencias. Informe completo en
   `.agents/tasks/postits-ocr-conexion-investigacion.md`.
7. **Implementación de la foto de post-it** (FEAT-001 backend + FEAT-002 frontend, commiteados).
   Falta desplegar y verificar (FEAT-003, en curso).

---

## 4. Estado de git (exacto, verificado)

- Rama de trabajo: **`feature/huellita-aws`**, dentro del worktree
  `c:\dev\hackaton\.worktrees\huellita-aws`.
- `origin/feature/huellita-aws` está en **`e658b0f`** (el fix de DynamoDB, ya pusheado).
- **Local está 2 commits adelante de origin, SIN pushear todavía:**
  - `9d5e76f` feat: BFF acepta formato foto (FEAT-001)
  - `3b26bac` feat: enviar foto de post-it al BFF real (FEAT-002)
- Hay un workflow en curso que añadirá un 3º commit (FEAT-003: deploy + verificación) y el commit
  de cierre. **No se ha pusheado la foto porque todavía no está verificada contra AWS.**
- Ramas de respaldo (no borrar): `respaldo/huellita-aws-pre-merge`, `respaldo/huellita-aws-pre-merge2`.
- `main` NO se ha tocado. La integración a `main` va por PR (ya hay uno abierto para lo anterior).
- Pendiente de versionar a propósito: `huellita-web/.agents/` y los `.agents/tasks/task-foto-postit/`
  (artefactos de agente; decidir aparte si se commitean).

---

## 5. Lo ÚNICO que falta: desplegar y verificar la foto (FEAT-003)

Hay un workflow corriendo que debería hacer esto automáticamente. Si lo terminó, verifica que:
1. Se hizo `sam deploy` del BFF (añade 2 permisos IAM nuevos: `lambda:InvokeFunction` sobre
   `postits-ocr` y `s3:PutObject` sobre `original/*`). **Riesgo**: si la cuenta del hackathon no
   permite esos permisos IAM, el deploy falla y hay que escalarlo. Es el único bloqueo serio posible.
2. Se republicó el front (`scripts\publicar_front.ps1` desde `huellita-web`, o las dos pasadas de
   `aws s3 sync` + invalidación de CloudFront como en `DESPLIEGUE.md`).
3. Se verificó la foto end-to-end con las imágenes de prueba que dejó Lucas:
   - `C:\dev\hackaton\WhatsApp Image 2026-10-16 at 00.19.49.jpeg`
   - `C:\dev\hackaton\WhatsApp Image 2026-10-16 at 00.19.50.jpeg`

Si el workflow NO terminó o falló, el estado y los hallazgos quedan en:
`.agents/tasks/task-foto-postit/` y el reporte `foto-postit-conexion-ejecucion.md`.

**Después de verificar la foto, hay que pushear la rama:**
```powershell
git -C c:\dev\hackaton\.worktrees\huellita-aws push -u origin feature/huellita-aws
```

---

## 6. Guion de demo recomendado + 3 audios para grabar en vivo

### Niños reales de SG-A (úsalos para que la IA detecte al niño)
Benjamín, Emilio, Esperanza, Josefa, Martina, Nayara, Pascal, Pedro, Rusi, Sofía, Tomás, Vicente.
(Son bebés/sala menor, ~20 meses: las acciones deben ser realistas para esa edad.)

### Núcleos de la rúbrica
Motor grueso · Motor fino · Lenguaje y comunicación · Cognitivo · Socioemocional.

### Por qué los audios de prueba NO daban buena sugerencia
La transcripción salía perfecta, pero los audios mencionaban nombres que **no son de SG-A**
(Cristóbal, Agustín, Florencia), así que la IA no podía asociar la observación a un niño del
roster ni mapear un núcleo con confianza. **La clave es nombrar a un niño real de SG-A y describir
una acción evaluable.**

### 3 audios para grabar en vivo (dan núcleo + nivel)
1. **Motor grueso — Benjamín:** "Hoy en el patio Benjamín pateó la pelota hacia adelante sin que
   nadie lo sostuviera, y después corrió un trecho corto siguiendo a los otros niños."
2. **Lenguaje — Sofía:** "Sofía me trajo el cuento y combinó dos palabras, dijo 'más agua' cuando
   quería tomar, y repitió el nombre de su compañera cuando la vio llegar."
3. **Motor fino / Cognitivo — Emilio:** "Emilio estuvo un buen rato encajando las piezas, juntó las
   de color rojo en un montón y apiló tres cubos uno sobre otro antes de que se le cayeran."

### Consejos para la demo en vivo
- **Captura de calentamiento**: haz una nota de texto cualquiera 2 min antes de empezar, para que
  Lambda esté "tibia" y los tiempos sean los buenos (~15 s), sin arranque en frío.
- **Graba en silencio y vocaliza claro** (el ruido de sala ensucia los nombres).
- Las notas creadas en vivo quedan guardadas en SG-A; si no quieres que aparezcan después,
  archívalas desde Revisar.
- Tiempos de referencia medidos: texto ~13 s, audio ~13-20 s.

---

## 7. Datos técnicos útiles (entorno)

- Cuenta AWS: **277702547089**, región **us-east-1**, perfil CLI **hackaton**.
- Antes de cualquier comando AWS, exporta credenciales EN LA MISMA LÍNEA:
  ```powershell
  aws configure export-credentials --profile hackaton --format powershell | Out-String | Invoke-Expression
  ```
  (La sesión caduca; si da error, `aws login --profile hackaton` primero.)
- **npm NO está en PATH**: shim en `c:\dev\hackaton\.worktrees\.herramientas\bin\npm.cmd`, o usa
  `node` directo (p.ej. `node .\node_modules\vite\bin\vite.js build`).
- **SAM**: `C:\Program Files\Amazon\AWSSAMCLI\bin\sam.cmd`.
- **PowerShell**: separador de comandos `;` (nunca `&&`).
- Prueba de humo (desde `huellita-web`), el verificador end-to-end:
  ```powershell
  .\.venv\Scripts\python.exe scripts\smoke.py https://d3hs1azrtjzcei.cloudfront.net
  .\.venv\Scripts\python.exe scripts\smoke.py https://d3hs1azrtjzcei.cloudfront.net --audio "C:\dev\hackaton\TEST TRANSCRIPTOR.m4a"
  ```
- Salidas del stack (URL, bucket, distribución):
  ```powershell
  aws cloudformation describe-stacks --stack-name huellita-web --region us-east-1 --query "Stacks[0].Outputs" --output table
  ```

### Dónde está qué
- BFF (backend): `c:\dev\hackaton\.worktrees\huellita-aws\huellita-web`
- Front: `c:\dev\hackaton\.worktrees\huellita-aws\huellita-formato-mejorado`
- OCR de post-its (Lambda, ya desplegada, NO se modifica): `postits-ocr/`
- Informes de la sesión: `.agents/tasks/` (postits-ocr-conexion-investigacion.md,
  merge-origin-main-ejecucion*.md, fix-dynamo-total-reservada.md, foto-postit-plan.md)

---

## 8. Lo primero que debes hacer al tomar el turno

1. **Comprueba si la foto quedó desplegada.** Corre el smoke de texto y audio para confirmar que
   la demo sigue sana (deben dar "Todo paso."). Si el workflow de foto terminó, verifica la foto
   con las dos imágenes de WhatsApp (§5).
2. **Si la foto está verificada → pushea la rama** (§5) para no perder el trabajo.
3. **Si el deploy de la foto falló por IAM**, ese es el bloqueo a resolver con quien administre la
   cuenta del hackathon. La demo de texto+audio sigue en pie mientras tanto.
4. **Ensaya el guion** (§6) con un niño real de SG-A antes de la demo en vivo.
