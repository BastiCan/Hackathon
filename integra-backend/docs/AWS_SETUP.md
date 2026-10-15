# Montaje en AWS: lo que haces tú a mano

Recursos que se crean (nada más): **1 Lambda, 5 tablas DynamoDB, 2 buckets S3, 1 rol IAM**, más el uso de Bedrock.
La Lambda se dispara por **eventos S3** del bucket de capturas; también admite `sam remote invoke` para pruebas directas.
Comandos para PowerShell en Windows.

Recursos del stack:
- **Lambda** `ProcesarNota` (Python 3.13, 300 s, 1024 MB).
- **Tablas** `Jardines`, `Educadoras` (GSI `porJardin`), `Ninos` (GSI `porJardin`), `Registros` (GSI `porSala`),
  `Observaciones` (GSI `porNino` y `porSala`).
- **Buckets** `rubrica` (nombre autogenerado) y `capturas` (nombre fijo `integra-capturas-<AccountId>`).

## 0. Herramientas (una vez)
- **AWS CLI v2** → `aws --version`
- **AWS SAM CLI** → `sam --version`
- **Python 3.13** exacto → `py -3.13 --version`
- **Node.js LTS** (para el MCP `aws-docs` de Kiro) → `npx --version`
- Opcional: **Docker Desktop**, solo si `sam build` falla con librerías compiladas → `sam build --use-container`.

## 1. Credenciales (temporales, como variables de entorno)
Las credenciales del evento se pegan como variables de entorno **en cada terminal** donde se trabaje, incluida la terminal
integrada de Kiro (cada ventana de PowerShell empieza sin ellas):
```powershell
$Env:AWS_DEFAULT_REGION="us-east-1"; $Env:AWS_REGION="us-east-1"
$Env:AWS_ACCESS_KEY_ID="..."; $Env:AWS_SECRET_ACCESS_KEY="..."; $Env:AWS_SESSION_TOKEN="..."
aws sts get-caller-identity
```
- Tienen prioridad sobre el perfil `default` del computador (que sigue siendo el usuario de solo lectura de otra cuenta).
  En una terminal SIN estas variables, los comandos usarían esa otra cuenta: verifica siempre con `aws sts get-caller-identity`.
- Expiran: si aparece `ExpiredToken`, copia credenciales nuevas desde el portal del evento.
- Nunca las escribas en archivos del proyecto que se suban a git.

## 2. Bedrock: modelos e IDs
1. Consola → Amazon Bedrock → región **us-east-1** → *Model catalog*: confirma **Claude Haiku 4.5**, **Claude Sonnet 5**
   y **Titan Text Embeddings V2**. Pruébalos en el *Playground*. Si Anthropic pide el
   formulario de caso de uso, complétalo.
2. IDs:
```powershell
aws bedrock list-inference-profiles --region us-east-1 --query "inferenceProfileSummaries[].inferenceProfileId"
aws bedrock list-foundation-models --region us-east-1 --by-provider amazon --query "modelSummaries[?contains(modelId,'embed')].modelId"
```
Anota: Haiku 4.5 → `MODEL_ID_SEPARAR`; Sonnet 5 → `MODEL_ID_CONDUCTAS` y `MODEL_ID_EVALUAR`; Titan V2 → `MODEL_ID_EMBEDDINGS`.

## 3. Variables para correr en local (terminal de Kiro)
Para pruebas locales (sin AWS), con los fixtures de `tests/fixtures/`:
```powershell
$env:FUENTE_DATOS="local"
$env:MODEL_ID_SEPARAR="<id haiku 4.5>"; $env:MODEL_ID_CONDUCTAS="<id sonnet 5>"; $env:MODEL_ID_EVALUAR="<id sonnet 5>"
$env:MODEL_ID_EMBEDDINGS="<id titan v2>"; $env:N_CORRIDAS_EVALUAR="3"; $env:TOP_K="8"
```

## 4. Desplegar (tarea 9)
```powershell
sam validate --lint          # chequeo estático del template (opcional)
sam build
sam deploy --guided
```
En `--guided`: stack `integra-procesador`, región us-east-1, pega los IDs de modelo (`ModelIdSeparar`,
`ModelIdConductas`, `ModelIdEvaluar`; `ModelIdEmbeddings` ya trae default), acepta crear el rol IAM.
Copia los **Outputs**: `NombreFuncion`, `NombreBucketRubrica`, `NombreBucketCapturas`, y los nombres de las 5 tablas.

El bucket de capturas tiene **nombre fijo** `integra-capturas-<AccountId>` (por eso no choca con la notificación S3 que
dispara la Lambda). Las notificaciones ya quedan configuradas por el template (prefijo `capturas/`, sufijos `meta.json`
y `texto.json`); no hay que crearlas a mano.

## 5. Variables de entorno para los scripts (después del deploy)
Los scripts (`cargar_aws.py`, `subir_captura_prueba.py`) leen el entorno. Pega los Outputs del stack:
```powershell
$env:FUENTE_DATOS="aws"
$env:TABLA_JARDINES="<out>"; $env:TABLA_EDUCADORAS="<out>"; $env:TABLA_NINOS="<out>"
$env:TABLA_REGISTROS="<out>"; $env:TABLA_OBSERVACIONES="<out>"
$env:BUCKET="<NombreBucketRubrica>"; $env:BUCKET_CAPTURAS="<NombreBucketCapturas>"
```
(La Lambda NO necesita esto: sus variables las define el template en el deploy.)

## 6. Cargar datos
```powershell
py -3.13 scripts/cargar_aws.py
```
Carga `Jardines` (20, con `salas[]`), `Educadoras` (80), el historial en `Observaciones`
(`origen=dataset`, ~2950) y `Ninos` (500, con `ultima_obs_fecha`/`ultimo_nivel` donde haya historial);
sube `rubrica/` a S3 (ya **no** se sube `raw/`). Verifica los conteos que imprime y revisa las tablas en la consola.

## 7. Probar
### 7a. Disparo por S3 (flujo real, sin OCR)
```powershell
py -3.13 scripts/subir_captura_prueba.py
```
Sube `capturas/<CAP-...>/meta.json` y `.../texto.json` al bucket de capturas y dispara la Lambda. Verifica:
- Tabla `Registros`: el `id_captura` pasó de `RECIBIDO` (al llegar `meta.json`) a `PROCESADO` (al terminar `texto.json`).
- Tabla `Observaciones`: aparecen las observaciones de esa captura (`origen=app`).
- CloudWatch Logs del grupo de la función: línea `captura ... procesada: N observaciones`.

### 7b. Invocación directa (sin S3)
```powershell
sam remote invoke ProcesarNotaFunction --stack-name integra-procesador --event-file events/nota_ejemplo.json
```
O en la consola de Lambda → *Test* con `events/nota_ejemplo.json` (evento directo) o `events/s3_texto.json`
(simula el record S3; requiere que `meta.json`/`texto.json` existan en el bucket).

## 8. Borrar todo
```powershell
sam delete --stack-name integra-procesador
```
Los dos buckets deben estar **vacíos** antes de borrar el stack (vacíalos desde la consola o con
`aws s3 rm s3://<bucket> --recursive`). El bucket de capturas tiene nombre fijo: si quedara sin borrar, un
redeploy fallaría por nombre en uso.

## Problemas típicos
| Síntoma | Causa probable |
|---|---|
| `AccessDeniedException` al invocar el modelo | Modelo no habilitado en la región, o el rol no tiene permiso sobre el inference profile Y los modelos fundacionales de sus regiones |
| `ThrottlingException` | Cuota de tokens/minuto; el backoff lo absorbe. Si persiste, bajar `N_CORRIDAS_EVALUAR` |
| `Task timed out` | Nota muy larga: subir el timeout o bajar corridas |
| `Runtime.ImportModuleError` | Librería compilada empaquetada para Windows → `sam build --use-container` |
| `ExpiredToken` | Claves temporales vencidas → paso 1 |
| La captura queda en `RECIBIDO` y no avanza | Llegó `meta.json` pero no `texto.json` (o la notificación de `texto.json` no disparó): revisa que el objeto termine en `texto.json` bajo `capturas/` |
| `Registros` en `ERROR` con `META_INVALIDA` | `meta.json` ausente o mal formado cuando llegó `texto.json` |
| `BucketAlreadyExists` en el deploy | Quedó el bucket de capturas de un stack anterior (nombre fijo): vacíalo y bórralo |
