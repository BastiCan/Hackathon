# Plan de consolidación y push ordenado

Objetivo: llevar a `origin` todo el trabajo local sin publicar de las dos ubicaciones, en commits
temáticos, sin perder nada y sin tocar `main`.

Repo: `c:\dev\hackaton` · remoto `origin` = https://github.com/BastiCan/Hackathon.git

---

## 0. Correcciones al estado del brief (verificado por ejecución)

El brief estaba desactualizado. Estos datos se re-verificaron con `git fetch origin --prune`:

| Dato | Brief | Verificado |
|---|---|---|
| `origin/main` | `1a04ea8` "Transcripción de audio" | **`e64d4a0`** "Merge pull request #6 from BastiCan/feature/postits-ocr" |
| `lucas/kiro-specs` detrás de `origin/main` | 41 | **49** |
| `feature/huellita-aws` detrás de `origin/main` | 7 | **15** |
| Conflicto esperado en Ubicación A | `design.md` | **No hay conflicto**: `origin/main` no tiene ningún árbol `.kiro/` |

Entraron a `origin/main` dos servicios nuevos (PR #6): `postits-ocr/` e `ingesta/`. Ninguno toca
archivos del trabajo local, pero sí amplían el rango a integrar en la Ubicación B de 7 a 15 commits.

`origin/feature/huellita-aws` **no existe** en el remoto: la rama nunca se publicó.
Ramas remotas actuales: `main`, `docs/informe-ux-huellita`, `feature/huellita-inicio-rubrica-e1`,
`feature/integra-backend`, `feature/postits-ocr`, `feature/transcriptor-audio`,
`frontend-huellita`, `gh-pages`.

---

## 1. Entorno y comandos reales de verificación

Windows + PowerShell. Separador `;`. Rutas absolutas o `git -C <ruta>`.

**`npm` no está en el PATH.** Hay un shim local: `c:\dev\hackaton\.worktrees\.herramientas\bin\npm.cmd`.
Lo más confiable es invocar los binarios con `node` directamente.

Front (`huellita-formato-mejorado`), desde `c:\dev\hackaton\.worktrees\huellita-aws\huellita-formato-mejorado`:

```powershell
node .\node_modules\typescript\bin\tsc -b --force   # verificado: exit 0, sin salida
node .\node_modules\vite\bin\vite.js build          # verificado: exit 0, "built in 3.05s"
```

BFF (`huellita-web`), desde `c:\dev\hackaton\.worktrees\huellita-aws\huellita-web`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q             # verificado: 353 passed
```

Generador de datos E-1, desde `huellita-formato-mejorado`:

```powershell
..\huellita-web\.venv\Scripts\python.exe -m pytest scripts\test_generar_datos_e1.py -q  # verificado: 13 passed
python scripts\generar_datos_e1.py                  # verificado: reproduce data/ byte a byte
```

### ⚠ Vitest del front está roto por el entorno, no por el código

`npm test` (`vitest run`) falla en **los 14 archivos** con `No test suite found in file`.
Se descartó que sea culpa del código: se ejecutó un test mínimo y correcto
(`describe('cordura', () => it('suma', ...))`) con esa misma instalación de vitest, en un directorio
aparte, y **también falla igual**. Las versiones instaladas son coherentes entre sí
(vitest / `@vitest/runner` / `@vitest/expect` 2.1.8, vite 5.4.11, jsdom 25.0.1), y el runtime es
Node **v22.22.2**, muy posterior a vitest 2.1.8.

Consecuencia operativa: **la puerta de verificación del front es `tsc -b` + `vite build`**, no vitest.
`tsconfig.app.json` tiene `"include": ["src"]`, así que los `*.test.ts(x)` **sí se typechequean**:
`tsc -b` cubre errores de tipos en los tests aunque no se puedan ejecutar.

**No se deben editar los tests para "arreglar" esto.** Es un desajuste de toolchain. Queda como
problema abierto a reportar (ver §7).

---

## 2. Hallazgos que cambian la estrategia

1. **`origin/main` no tiene `.kiro/`.** `git ls-tree -r origin/main -- .kiro` está vacío, y
   `design.md` fue **añadido** por `01a7410` (no existía en el punto de bifurcación `386ee58`).
   El rebase de la Ubicación A es **sin conflictos**.

2. **`.gitignore` no cambió en `origin/main`.** `git diff 386ee58 origin/main -- .gitignore` es vacío.
   El cambio local de `.gitignore` tampoco conflictúa.

3. **Los 28 archivos de `servicio_transcripcion/` son byte-idénticos a `origin/main`.** Re-confirmado
   comparando `git hash-object` de cada archivo contra `git rev-parse origin/main:<ruta>`:
   28 iguales, 0 distintos, 0 ausentes. No son trabajo nuevo. **No commitearlos.**

4. **Fusionar el estado *committeado* de la Ubicación B con `origin/main` no da conflictos.**
   `git merge-tree --write-tree feature/huellita-aws origin/main` → exit 0.
   Todo el riesgo está en los 35 archivos modificados **sin commitear**.

5. **Las dos migraciones a E-1 convergieron en los mismos identificadores.** Local y `origin/main`
   definen exactamente lo mismo en `tipos.ts`:
   `NucleoId = 'motor_grueso' | 'motor_fino' | 'lenguaje_comunicacion' | 'socioemocional' | 'cognitivo'`
   y `Nivel = 1..9`. El conflicto en `tipos.ts` es **textual, no semántico**.

6. **`data/semilla.json` y `data/rubrica_e1.json` son regenerables.** Se copiaron el script y sus
   entradas a un sandbox fuera del repo, se ejecutó `generar_datos_e1.py` y las salidas resultaron
   **byte-idénticas** a los archivos del worktree (`rubrica_e1.json` 2073783bd8, `semilla.json`
   bc0579a2ab). Sus 13 tests pasan. Las entradas están presentes y versionadas:
   `Dump/dataset_e1_publico/datos_publicos/*.csv`, `integra-backend/tests/fixtures/nomina_demo.json`,
   `huellita-web/src/huellita_api/datos/usuarias_demo.json`.
   **El conflicto más grande (~10k líneas) se resuelve regenerando, no fusionando a mano.**

7. **`origin/main` eliminó el concepto de ámbito.** No hay `ambitoDe`, `abreviatura`, `NOMBRE_AMBITO`
   ni `AmbitoId` en ningún archivo de `huellita-formato-mejorado/src` de `origin/main`. Local lo
   conserva y lo migró a los 5 dominios; lo consumen `ChipNivel.tsx`, `Miniatura.tsx`, `Agenda.tsx`,
   `FichaNino.tsx`, `MiSala.tsx`. → **decisión de producto** (§6).

8. **`huellita-web/.agents/tasks/` tiene artefactos de agente dentro del worktree** y
   `huellita-web/.gitignore` (que sólo ignora `.aws-sam/`, `.venv/`, `__pycache__/`, `.pytest_cache/`)
   **no los excluye**. `git add huellita-web` los commitearía. Hay que excluirlos explícitamente.

9. **`.worktrees/` hoy es invisible para git sólo por el cambio sin commitear de `.gitignore`.**
   Git lee `.gitignore` del árbol de trabajo, no del índice. Si ese cambio se descarta o se stashea,
   `.worktrees/` aparece como untracked y se puede commitear por accidente. → **commitear
   `.gitignore` primero** (razón verificada, no estética).

10. **`.kiro/steering/equipo.md` pesa 0 bytes.** → decisión abierta (§6).

11. **Fuga de datos: revisada y descartada.** `huellita-web/samconfig.toml` y `template.yaml` llevan
    el ID de cuenta AWS `277702547089`, el host `289khkzbpd.execute-api.us-east-1.amazonaws.com` y
    el ID de clave `14b8weklf1`. Se verificó que **los tres ya están committeados en `origin/main`**
    (`ingesta/ingesta.py`, `ingesta/template.yaml`, `postits-ocr/docs/contrato.md`,
    `servicio_transcripcion/README.md`). No hay exposición nueva. No es bloqueante.
    Nota menor: ninguno es una credencial (ID de cuenta e ID de clave, no el valor de la clave).

12. `core.autocrlf=true` y `.gitattributes` sólo fija `*.bat` a CRLF. Al hacer `git add` saldrán
    avisos `LF will be replaced by CRLF`: son benignos (normalización estándar), no indican daño.

13. `rerere` **no** está habilitado (`git config rerere.enabled` vacío).

---

## 3. Estrategia de integración (decidida)

**Ubicación A → `git rebase origin/main`.** La rama nunca se publicó, el rebase es sin conflictos
(§2.1, §2.2) y deja historia lineal. No hay razón para un merge.

**Ubicación B → `git merge origin/main`.** Razonamiento: la reconciliación son 25 archivos y es
**semántica** (dos migraciones E-1 paralelas + agenda vs Inicio). Un rebase replayearía 7 commits
temáticos sobre `origin/main` y obligaría a re-resolver `tipos.ts`, `rubrica.ts`, `ambitos.ts` y
`semilla.json` en varios de ellos; con `rerere` apagado eso multiplica el riesgo de resoluciones
inconsistentes entre commits y de dejar commits intermedios que no compilan. El merge resuelve cada
conflicto **una sola vez**, y registra honestamente que dos líneas de trabajo paralelas se
reconciliaron. La rama tampoco se publicó, así que el rebase sería *legal*; simplemente es peor aquí.

Nada se pushea a `main`. Cada ubicación se publica en su propia rama y la integración a `main` queda
para un PR revisado por el equipo.

---

## 4. Agrupamiento de commits

### Ubicación A — `c:\dev\hackaton`, rama `lucas/kiro-specs`

| # | Mensaje | Archivos |
|---|---|---|
| A1 | `chore: ignora la config local de MCP y el directorio de worktrees` | `.gitignore` |
| A2 | `chore(kiro): reglas de agente de AWS y config de la spec` | `.kiro/steering/aws-agent-rules.md`, `.kiro/specs/kindergarten-observation-platform/.config.kiro` |
| A3 | `docs(agentes): notas de investigación y planes de trabajo` | los 7 de `.agents/tasks/` |

A3 va **aislado y último** para que descartarlo sea `git reset --soft HEAD~1`.
`equipo.md` queda fuera de A2 (0 bytes, ver §6).

### Ubicación B — worktree `.worktrees\huellita-aws`, rama `feature/huellita-aws`

| # | Mensaje | Contenido |
|---|---|---|
| B1 | `feat(huellita-web): BFF de Huellita en AWS (capturas, decisiones, lectura y audio)` | `huellita-web/src/**`, `template.yaml`, `samconfig.toml`, `pyproject.toml`, `requirements-dev.txt`, `src/requirements.txt`, `.gitignore` |
| B2 | `test(huellita-web): cobertura del BFF con fixtures del dataset E-1` | `huellita-web/tests/**` (incl. `fixtures/`) |
| B3 | `docs(huellita-web): contratos de la API y spec oficial` | `huellita-web/CONTRATOS.md`, `SPEC-OFICIAL.md`, `scripts/volcar_muestras.py` |
| B4 | `feat(front): generador de la rúbrica y la semilla desde el dataset E-1` | `huellita-formato-mejorado/scripts/generar_datos_e1.py`, `scripts/test_generar_datos_e1.py`, `data/rubrica_e1.json`, `data/semilla.json` |
| B5 | `refactor(front): núcleos y niveles del dataset E-1 (5 dominios, 9 niveles)` | `src/lib/tipos.ts`, `src/lib/rubrica.ts`, `src/lib/vistas.ts`, `src/lib/agenda.ts`, `src/components/ambitos.ts`, `src/components/colores.ts` + tests `rubrica.test.ts`, `evaluacion.test.ts`, `vistas.test.ts`, `agenda.test.ts`, `App.test.tsx`, `accesibilidad.test.tsx`, `datos.test.ts`, `ia.test.ts` |
| B6 | `feat(front): capa HTTP y opciones de compilación para la versión AWS` | nuevos `src/services/http.ts`, `errores.ts`, `http.test.ts`, `captura.test.ts`, `src/app/config.ts`, `opciones.tsx`, `version-aws.test.tsx` + `src/vite-env.d.ts` |
| B7 | `feat(front): navegación sin agenda y captura contra el BFF` | `src/app/App.tsx`, `Layout.tsx`, `Dock.tsx`, `NavegacionLateral.tsx`, `BarraInferior.tsx`, `destinos.ts`, `servicios.tsx`, `captura.tsx`, `src/components/Captura.tsx`, `Miniatura.tsx`, `src/pages/Entrada.tsx`, `FichaNino.tsx`, `MiSala.tsx`, `Revisar.tsx`, `src/services/captura.ts`, `datos.ts` + tests `adaptable.test.tsx`, `demo.test.tsx`, `privacidad.test.ts` |

**Por qué B5 es grande y no se subdivide más:** la migración E-1 es atómica para el typecheck. Se
verificó qué archivos cargaban los códigos viejos en la rama (`'IA'…'PM'`, `SALA-MMA`, `Agustina`):
`data/semilla.json`, `App.test.tsx`, `accesibilidad.test.tsx`, `agenda.test.ts`, `evaluacion.test.ts`,
`rubrica.test.ts`, `tipos.ts`, `vistas.test.ts`, `datos.test.ts`, `ia.test.ts`; más `ambitos.ts` y
`agenda.ts`, que tienen `Record<NucleoId, …>` con las claves viejas sin comillas. Partir `tipos.ts`
de esos consumidores deja commits que no compilan. B4 va antes porque sólo agrega datos y scripts
(no cambia tipos).

---

## 5. Conflictos exactos de la Ubicación B

Lista **verificada por simulación**, no estimada: se construyó un commit desechable con el trabajo
sin commitear usando un índice temporal (`GIT_INDEX_FILE` en `C:\Windows\Temp`, sin tocar refs,
índice real ni archivos; HEAD siguió en `f76d4bb`, 35 modificados y 63 untracked intactos) y se
corrió `git merge-tree --write-tree <sim> origin/main`.

**25 rutas en conflicto.** De los 35 modificados, 24 conflictúan y **11 se fusionan limpios**:
`BarraInferior.tsx`, `accesibilidad.test.tsx`, `adaptable.test.tsx`, `destinos.ts`, `servicios.tsx`,
`Entrada.tsx`, `Revisar.tsx`, `services/captura.ts`, `services/datos.ts`, `privacidad.test.ts`,
`vite-env.d.ts`.

| Archivo | Tipo | Resolución |
|---|---|---|
| `data/rubrica_e1.json` | add/add | **Regenerar** con `generar_datos_e1.py` |
| `data/semilla.json` | content | **Regenerar** con `generar_datos_e1.py` |
| `src/lib/tipos.ts` | content | Tomar `origin/main` (es superset: añade `SugerenciaDemo`, `NucleoInfo.codigo`, etc.) y confirmar que `NucleoId`/`Nivel` quedan como §2.5 |
| `src/lib/agenda.ts` | modify/delete | **Aceptar el borrado de `origin/main`.** El cambio local era sólo el `Record<NucleoId,…>` de la migración; no aporta valor propio |
| `src/lib/agenda.test.ts` | modify/delete | **Aceptar el borrado** (ídem: sólo renombres de fixtures) |
| `src/components/ambitos.ts` | modify/delete | **DECISIÓN DE PRODUCTO** (§6.1) |
| `src/app/App.tsx` | content | **DECISIÓN DE PRODUCTO** (§6.2) |
| `src/components/colores.ts` | content | Trivial: local ajusta un comentario de 8→9 niveles; tomar `origin/main` y reaplicar el comentario si sigue aplicando |
| `src/lib/rubrica.ts` | content | Reconciliar: ambos migraron a E-1. Base `origin/main` (+112/-76 vs local +17/-8), reaplicar lo que falte |
| `src/lib/vistas.ts` | content | Trivial: local sólo cambia "los 8 núcleos" por "los núcleos" en un comentario |
| `src/pages/FichaNino.tsx` | content | Base `origin/main` (+117/-160, reescritura fuerte); el cambio local es +2/-1. Depende de §6.1 por `ambitoDe`/`COLOR_AMBITO` |
| `src/pages/MiSala.tsx` | content | Base `origin/main` (+21/-20); local +2/-2. Depende de §6.1 por `abreviatura`/`NOMBRE_AMBITO` |
| `src/components/Miniatura.tsx` | content | Base `origin/main` (+7/-9); local +2/-2. Depende de §6.1 |
| `src/components/Captura.tsx` | content | Reconciliar a mano: local +83/-17, origin +175/-35. Ambos lados trabajaron la captura |
| `src/app/captura.tsx` | content | Reconciliar: local +11/-2, origin +14/-7 |
| `src/app/Dock.tsx` | content | Base `origin/main` (+94/-28); local +10/-5. Depende de §6.2 |
| `src/app/Layout.tsx` | content | Reconciliar: ambos +9/-5 y +9/-4. Depende de §6.2 |
| `src/app/NavegacionLateral.tsx` | content | Base `origin/main`; local +4/-2. Depende de §6.2 |
| `src/lib/evaluacion.test.ts` | content | Reconciliar: local +117/-82, origin +121/-99 |
| `src/lib/rubrica.test.ts` | content | Base `origin/main` (+78/-20); reaplicar asserts locales |
| `src/lib/vistas.test.ts` | content | Reconciliar: local +61/-48, origin +54/-33 |
| `src/app/App.test.tsx` | content | Base `origin/main` (+184/-36); reaplicar asserts locales. Depende de §6.2 |
| `src/app/demo.test.tsx` | content | Reconciliar: local +21/-14, origin +15/-19 |
| `src/services/datos.test.ts` | content | Base `origin/main` (+65/-5); reaplicar asserts locales |
| `src/services/ia.test.ts` | content | Reconciliar: local +28/-22, origin +39/-14 |

Además, `origin/main` **agrega** archivos que local no tiene y que hay que adoptar:
`src/pages/Inicio.tsx`, `src/lib/inicio.ts`, `src/lib/audio.ts`, `src/lib/audio.test.ts`,
`data/nucleos_e1.json`; y **borra** `data/rubrica_8_niveles.json` y `src/pages/Agenda.tsx`.

Falso positivo a ignorar: `git diff feature/huellita-aws origin/main` lista como "borrados"
`huellita-web/DESPLIEGUE.md`, `huellita-web/scripts/publicar_front.ps1` y `smoke.py`. Son los
archivos que **agregó** el commit local `f76d4bb`; no existen en `origin/main` por dirección del
diff, no porque alguien los borrara.

### Bloqueo mecánico antes de fusionar

`data/rubrica_e1.json` está **untracked** en el worktree y `origin/main` lo **agrega**: git se
negará con "untracked working tree file would be overwritten". Queda resuelto solo si B4 se commitea
antes del merge (pasa a ser tracked y el conflicto se vuelve add/add, manejable). Es el único choque
untracked-vs-agregado de la Ubicación B (verificado contra los 55 archivos que `origin/main` agrega).

---

## 6. Decisiones de producto: PAUSAR y preguntar

Estas dos no se pueden resolver leyendo código. Hay que **parar y preguntar** al usuario.

### 6.1 Color por ámbito (local) vs color por nivel (`origin/main`)

`origin/main` borró `src/components/ambitos.ts` y eliminó el concepto completo: no queda `ambitoDe`,
`abreviatura`, `NOMBRE_AMBITO` ni `AmbitoId` en todo `src`. Su commit se llama "colores por nivel".
El trabajo local, en cambio, **conservó y migró** `ambitos.ts` a los 5 dominios y le agregó un mapa
`ABREVIATURA` (`MG`, `MF`, `LC`, `SE`, `CO`) alineado con los códigos de manifestación del dataset
(`MAN-L09-CO-02`). Lo consumen 5 archivos: `ChipNivel.tsx`, `Miniatura.tsx`, `Agenda.tsx`,
`FichaNino.tsx`, `MiSala.tsx`.

Opciones: (a) aceptar el borrado y adoptar colores por nivel, perdiendo las abreviaturas E-1;
(b) conservar `ambitos.ts` migrado y readaptar los consumidores que `origin/main` reescribió;
(c) quedarse con colores por nivel pero rescatar sólo el mapa `ABREVIATURA`.

### 6.2 Agenda opcional por flag (local) vs Inicio que la reemplaza (`origin/main`)

`origin/main` (`77ace0a` "Inicio reemplaza la Agenda") **borró** `src/pages/Agenda.tsx` y
`src/lib/agenda.ts`, y agregó `src/pages/Inicio.tsx` y `src/lib/inicio.ts`.

El trabajo local tomó otro camino para el mismo problema: dejó la Agenda **detrás de un flag de
compilación**. En `App.tsx`:
`<Route path="/" element={opciones.agenda ? <Agenda /> : <Navigate to="/sala" replace />} />`,
con `rutaInicio(opciones)` para el catch-all, `destinos(esDirectora, agenda)` filtrando el menú y
`VITE_AGENDA` declarado en `vite-env.d.ts`. O sea: en la versión AWS la agenda desaparece, pero el
código sigue ahí y se puede reactivar.

Las dos soluciones son incompatibles tal cual. Si se adopta Inicio, el flag `opciones.agenda` se
queda sin página que mostrar y hay que decidir si el flag pasa a alternar Inicio vs Mi sala o si se
elimina. Afecta qué ve la tía al abrir la app: **es visible para el usuario final**.

### 6.3 Menor: `.agents/` ¿se versiona?

Recomendación por defecto: **sí, commitearlo aislado y último** (A3), para que descartarlo sea
`git reset --soft HEAD~1`. Son ~250 KB de notas de investigación con valor para el equipo.
La alternativa es agregar `.agents/` al `.gitignore` en A1 y no publicarlas.

Si se versiona `.agents/` en la raíz, hay que decidir aparte sobre
`huellita-web/.agents/tasks/integracion-review.{json,md}` (§2.8): la recomendación es **excluirlos**
de todos modos, porque son de un agente y están anidados dentro de un servicio.

### 6.4 Menor: `equipo.md` vacío

`.kiro/steering/equipo.md` tiene 0 bytes. Commitear un archivo de steering vacío no aporta.
Recomendación: dejarlo fuera de A2 hasta que tenga contenido. Si el usuario lo quiere igual, entra en A2.

---

## 7. Verificar durante la implementación

- **Vitest roto (§1).** Confirmar que sigue fallando después del merge, y reportarlo como hallazgo.
  Diagnóstico probable: incompatibilidad vitest 2.1.8 con Node v22.22.2. Arreglo candidato (NO parte
  de este trabajo, requiere aprobación): subir vitest a 3.x. Hoy no hay otro Node instalado
  (`node` sólo existe en `C:\Users\lucas\AppData\Local\Kiro-Cli\node.exe`), así que no se puede
  probar con un runtime más viejo sin instalar uno.
- **¿B5 typechequea sin B7?** La expectativa es que sí: `Miniatura.tsx`, `FichaNino.tsx` y `MiSala.tsx`
  llaman `abreviatura(nucleo)` / `ambitoDe(nucleo)` sin cambio de firma. Correr `tsc -b` después de
  B5; si falla, mover a B5 el mínimo de archivos de B7 que haga falta y anotarlo.
- **`'SALA-MMA'` en `datos.test.ts:47`** sigue presente en disco, dentro de un JSON de `localStorage`.
  Parece un fixture deliberado de estado guardado viejo (y `tsc -b` pasa porque `salaId` es `string`),
  pero confirmar que no es un renombre olvidado.
- **Regenerar datos tras el merge.** Correr `generar_datos_e1.py` y comparar; si `origin/main` cambió
  `nomina_demo.json` o `usuarias_demo.json`, la salida será distinta de la de hoy y eso es lo correcto.
  `data/nucleos_e1.json` (que llega de `origin/main`) no lo produce el script: revisar si quedó huérfano.
- **`huellita-demo.html`.** `origin/main` lo regenera en `1978e87`. Local no lo toca, así que no
  conflictúa, pero queda desactualizado respecto del front fusionado. Preguntar si hay que regenerarlo.
- **Objetos sueltos de la simulación.** El commit desechable `43b450ff` quedó como objeto suelto sin
  referencia. Es inofensivo y `git gc` lo limpia solo. No hace falta acción.

---

## 8. Plan de ejecución

- [ ] 1. Punto de restauración y confirmación de las decisiones de §6.
      Antes de tocar nada: `git -C c:\dev\hackaton branch respaldo/kiro-specs-pre lucas/kiro-specs` y
      `git -C c:\dev\hackaton branch respaldo/huellita-aws-pre feature/huellita-aws`. Son refs, cuestan
      cero y permiten volver atrás. **Pausar y preguntar §6.1 y §6.2** antes de llegar al paso 8.
      Verificar: `git -C c:\dev\hackaton branch --list 'respaldo/*'` lista las dos.

- [ ] 2. Ubicación A — commit A1 (`.gitignore`).
      Primero por §2.9: mantiene `.worktrees/` fuera del radar de git durante el resto del trabajo.
      Archivos: `c:\dev\hackaton\.gitignore`
      Verificar: `git -C c:\dev\hackaton status --porcelain` ya no lista `.gitignore`, y
      `git -C c:\dev\hackaton check-ignore -v .worktrees` resuelve contra `.gitignore`.

- [ ] 3. Ubicación A — commit A2 (steering + `.config.kiro`).
      Archivos: `.kiro/steering/aws-agent-rules.md`, `.kiro/specs/kindergarten-observation-platform/.config.kiro`.
      `equipo.md` queda fuera salvo que el usuario diga lo contrario (§6.4).
      Verificar: `git -C c:\dev\hackaton show --stat HEAD` lista exactamente esos 2 archivos.

- [ ] 4. Ubicación A — commit A3 (`.agents/tasks/`), aislado y último.
      Archivos: los 7 `.md`/`.json` de `c:\dev\hackaton\.agents\tasks\` (incluido este plan si ya existe).
      Verificar: `git -C c:\dev\hackaton show --stat HEAD` sólo toca `.agents/`, y
      `git -C c:\dev\hackaton status --porcelain` deja únicamente los 28 de `servicio_transcripcion/`
      como untracked.

- [ ] 5. Ubicación A — apartar `servicio_transcripcion/` y rebasar sobre `origin/main`.
      Mover `c:\dev\hackaton\servicio_transcripcion` a
      `c:\dev\hackaton\.worktrees\respaldo-servicio-transcripcion` (los 28 archivos son idénticos a
      `origin/main`, §2.3, así que el rebase los repone exactos; el respaldo es seguro barato).
      Luego `git -C c:\dev\hackaton rebase origin/main`. No se esperan conflictos (§2.1, §2.2).
      Verificar: `git -C c:\dev\hackaton status` limpio y sin rebase en curso;
      `git -C c:\dev\hackaton rev-list --left-right --count lucas/kiro-specs...origin/main` da `3 0`;
      `git -C c:\dev\hackaton log --oneline -4` muestra los 3 commits nuevos sobre `e64d4a0`.

- [ ] 6. Ubicación A — confirmar que `servicio_transcripcion/` volvió idéntico y retirar el respaldo.
      Comparar cada archivo repuesto por el rebase contra `origin/main` con `git hash-object` /
      `git rev-parse origin/main:<ruta>`, igual que en §2.3.
      Verificar: 28 iguales, 0 distintos. Recién entonces borrar
      `c:\dev\hackaton\.worktrees\respaldo-servicio-transcripcion`.

- [ ] 7. Ubicación B — commits B1, B2 y B3 (`huellita-web`).
      Añadir por rutas explícitas; **nunca** `git add huellita-web` entero, por §2.8.
      Excluir siempre `huellita-web/.agents/`.
      Verificar, desde `...\huellita-aws\huellita-web`: `.\.venv\Scripts\python.exe -m pytest -q`
      sigue dando 353 passed, y `git -C <worktree> show --stat HEAD` no lista nada de `.agents/`.

- [ ] 8. Ubicación B — commits B4 a B7 del front.
      Orden obligatorio B4 → B5 → B6 → B7 (§4). B4 además desbloquea el merge (§5, bloqueo mecánico).
      Verificar después de **cada** commit, desde `...\huellita-aws\huellita-formato-mejorado`:
      `node .\node_modules\typescript\bin\tsc -b --force` exit 0 y
      `node .\node_modules\vite\bin\vite.js build` exit 0.
      Tras B4, además: `..\huellita-web\.venv\Scripts\python.exe -m pytest scripts\test_generar_datos_e1.py -q`
      da 13 passed.

- [ ] 9. Ubicación B — confirmar que no quedó trabajo suelto.
      Verificar: `git -C c:\dev\hackaton\.worktrees\huellita-aws status --porcelain` vacío salvo
      `huellita-web/.agents/tasks/*` (que se dejan untracked a propósito). Los 35 modificados y los
      62 untracked de trabajo real deben estar los 97 repartidos entre B1–B7.

- [ ] 10. Ubicación B — fusionar `origin/main` resolviendo los 25 conflictos de §5.
      `git -C c:\dev\hackaton\.worktrees\huellita-aws merge origin/main`. Resolver con la tabla de §5
      y las decisiones de §6. `semilla.json` y `rubrica_e1.json`: resolver **regenerando** con
      `python scripts\generar_datos_e1.py`, no editando a mano. Adoptar `Inicio.tsx`, `inicio.ts`,
      `audio.ts`, `audio.test.ts`, `nucleos_e1.json`; aceptar el borrado de `rubrica_8_niveles.json`.
      Verificar: `git -C <worktree> status` sin rutas en conflicto; `tsc -b` exit 0; `vite build` exit 0;
      `.\.venv\Scripts\python.exe -m pytest -q` en `huellita-web` sigue en 353 passed.

- [ ] 11. Revisión del diff fusionado contra `origin/main`.
      Leer `git -C <worktree> diff origin/main --stat` entero y confirmar que no se perdió trabajo
      local ni se revirtió trabajo de `origin/main`. Prestar atención a los archivos de §6.
      Verificar: el diff no borra `Inicio.tsx`/`inicio.ts` ni archivos nuevos de `postits-ocr/` o
      `ingesta/`; `git -C <worktree> log --oneline origin/main..HEAD` muestra B1–B7 + el merge.

- [ ] 12. Publicar ambas ramas. **Nunca a `main`.**
      `git -C c:\dev\hackaton push -u origin lucas/kiro-specs` y
      `git -C c:\dev\hackaton\.worktrees\huellita-aws push -u origin feature/huellita-aws`.
      Hacerlos **en serie, no en paralelo** (comparten object store y refs).
      Verificar: `git -C c:\dev\hackaton rev-list --left-right --count lucas/kiro-specs...origin/lucas/kiro-specs`
      da `0 0`, ídem para `feature/huellita-aws`. `git -C c:\dev\hackaton log --oneline -1 origin/main`
      sigue en `e64d4a0`.

- [ ] 13. Abrir los PR hacia `main` y reportar los hallazgos abiertos.
      Dos PR separados (`lucas/kiro-specs` → `main`, `feature/huellita-aws` → `main`) con `gh pr create`,
      título bajo 70 caracteres. En el cuerpo del PR del front, dejar constancia del vitest roto (§1)
      y de cómo se resolvió cada decisión de §6.
      Verificar: `gh pr list` muestra los dos contra `main`.

---

## 9. Qué NO hacer

- No commitear `c:\dev\hackaton\servicio_transcripcion\` (28 archivos idénticos a `origin/main`, §2.3).
- No commitear `huellita-web/.agents/` (artefactos de agente, §2.8).
- No pushear a `main` ni forzar nada contra el remoto.
- No editar los `*.test.ts(x)` del front para silenciar el fallo de vitest (§1).
- No correr git en las dos ubicaciones en paralelo: comparten object store y refs.
- No descartar el cambio de `.gitignore` antes de commitearlo (§2.9).
