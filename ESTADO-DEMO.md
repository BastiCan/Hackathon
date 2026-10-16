# Estado de la demo Huellita — traspaso de turno

Última actualización: 16-10-2026 (madrugada). Autor del turno: Lucas (+ asistente).
Para: compañero/a que sigue el turno.

Este documento resume TODO lo que se logró en la sesión y qué queda pendiente, para que
puedas continuar sin contexto previo. Lee la sección "Lo primero que debes hacer" al final.

---

## 1. Resumen en una línea

El front Huellita (`huellita-formato-mejorado`) quedó conectado al backend real en AWS
(BFF `huellita-web`). **Texto, audio Y FOTO de post-it funcionan end-to-end y están
verificados en vivo contra AWS.** Todo está desplegado y pusheado a `origin/feature/huellita-aws`.

> ACTUALIZACIÓN (cierre del turno): la foto de post-it YA quedó desplegada y verificada
> (ver §5-bis). El stack `huellita-web` está en UPDATE_COMPLETE con los permisos IAM del OCR.
> Todo pusheado hasta el commit `123f411`.

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

- **Crear una nota de FOTO de post-it** → se sube la imagen, el OCR lee los post-its y la IA
  sugiere núcleo + nivel en **~24-27 s**. Verificado end-to-end con las dos fotos de WhatsApp:
  Foto A (~160 KB) dio 11 sugerencias en 9 recortes; Foto B dio 12 en 9 recortes.

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
- `origin/feature/huellita-aws` está en **`123f411`** (todo pusheado, incluida la foto).
- Commits de la foto, ya en origin:
  - `9d5e76f` BFF acepta formato foto (FEAT-001)
  - `3b26bac` front envía foto al BFF (FEAT-002)
  - `4490d0a` ESTADO-DEMO.md (este doc)
  - `912812a` deploy BFF + verificación e2e foto (FEAT-003)
  - `123f411` artefactos de review (APPROVED)
- `feature/huellita-aws` está sincronizada con origin (0/0). **Nada pendiente de pushear.**
- Ramas de respaldo (no borrar): `respaldo/huellita-aws-pre-merge`, `respaldo/huellita-aws-pre-merge2`.
- `main` NO se ha tocado. La integración a `main` va por PR (ya hay uno abierto para lo anterior).
- Pendiente de versionar a propósito: `huellita-web/.agents/` y los `.agents/tasks/task-foto-postit/`
  (artefactos de agente; decidir aparte si se commitean).

---

## 5. Foto de post-it: COMPLETADA (ya no queda pendiente)

El workflow terminó bien y el revisor aprobó (APPROVED). Resumen de lo hecho:
- `sam deploy` del BFF → stack `huellita-web` **UPDATE_COMPLETE** (no hizo falta el Plan B de
  CloudFront). La Lambda del BFF tiene `FUNCION_OCR=postits-ocr` y el rol trae los 2 permisos
  nuevos efectivos: `lambda:InvokeFunction` sobre `postits-ocr` y `s3:PutObject` sobre
  `capturas/*/original/*`. **No hubo bloqueo de IAM.**
- Front republicado contra el BFF.
- Verificación end-to-end con las dos fotos de WhatsApp de Lucas: ambas llegaron a sugerencias
  (Foto A 27 s / 11 sugerencias; Foto B 24 s / 12 sugerencias). Sin regresión en texto ni audio.
- Pruebas: pytest BFF 398, vitest front 208, build OK.
- **Ya pusheado** hasta `123f411` en `origin/feature/huellita-aws`.

### Salvedades de la foto para la demo (no bloqueantes)
1. **Una foto genera N recortes de post-it → N sugerencias** (id `{CAP}-p{recorte}-{indice}`). La
   pantalla Revisar las lista planas por evidencia, **no las agrupa visualmente por recorte**
   todavía (fix opcional post-demo). Para la demo: usa un post-it claro con **pocos recortes**.
2. **El OCR de manuscrito es ruidoso**: puede equivocar palabras y dejar niño/núcleo/nivel vacíos
   con certeza baja. Es esperado (la tía confirma a mano), pero para la demo **elige post-its
   legibles y con letra clara**.

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

Buenas noticias: **texto, audio y foto están los tres desplegados, verificados y pusheados.**
No queda trabajo bloqueante. Lo que conviene hacer:

1. **Sanidad rápida**: `git pull` en el worktree, y corre el smoke para confirmar que la demo
   sigue sana (texto, audio y foto):
   ```powershell
   cd c:\dev\hackaton\.worktrees\huellita-aws\huellita-web
   aws configure export-credentials --profile hackaton --format powershell | Out-String | Invoke-Expression
   .\.venv\Scripts\python.exe scripts\smoke.py https://d3hs1azrtjzcei.cloudfront.net
   .\.venv\Scripts\python.exe scripts\smoke.py https://d3hs1azrtjzcei.cloudfront.net --audio "C:\dev\hackaton\TEST TRANSCRIPTOR.m4a"
   .\.venv\Scripts\python.exe scripts\smoke.py https://d3hs1azrtjzcei.cloudfront.net --foto "C:\dev\hackaton\WhatsApp Image 2026-10-16 at 00.19.49.jpeg"
   ```
2. **Ensaya el guion** (§6) con un niño real de SG-A. Para foto, usa un post-it legible con pocos
   recortes (§5, salvedades).
3. **Opcional**: abrir un PR de `feature/huellita-aws` hacia `main` cuando el equipo decida integrar
   (hoy la rama está pusheada pero la integración a `main` va por PR revisado).
4. **Pendiente opcional post-demo** (no bloqueante): que la pantalla Revisar agrupe las sugerencias
   de una foto por recorte de post-it; hoy llegan planas por evidencia.
