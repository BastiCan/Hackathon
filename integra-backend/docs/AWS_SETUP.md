# Montaje en AWS: lo que haces tú a mano

Recursos que se crean (nada más): **1 Lambda, 3 tablas DynamoDB, 1 bucket S3, 1 rol IAM**, más el uso de Bedrock.
Comandos para PowerShell en Windows.

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
```powershell
$env:FUENTE_DATOS="local"
$env:MODEL_ID_SEPARAR="<id haiku 4.5>"; $env:MODEL_ID_CONDUCTAS="<id sonnet 5>"; $env:MODEL_ID_EVALUAR="<id sonnet 5>"
$env:MODEL_ID_EMBEDDINGS="<id titan v2>"; $env:N_CORRIDAS_EVALUAR="3"; $env:TOP_K="8"
```

## 4. Desplegar (tarea 9)
```powershell
sam build
sam deploy --guided
```
En `--guided`: stack `integra-procesador`, región us-east-1, pega los IDs de modelo, acepta crear el rol IAM.
Copia los **Outputs** (función, bucket, tablas).

## 5. Cargar datos
```powershell
py -3.13 scripts/cargar_aws.py
```
Verifica en la consola: tablas `Educadoras` (80) y `Ninos` (500); en S3, `rubrica/` y `raw/`.

## 6. Probar
```powershell
sam remote invoke ProcesarNotaFunction --stack-name integra-procesador --event-file events/nota_ejemplo.json
```
O en la consola de Lambda → *Test* con el contenido de `events/nota_ejemplo.json`. Revisa la tabla `Observaciones`.

## 7. Borrar todo
```powershell
sam delete --stack-name integra-procesador
```
(Si el bucket tiene archivos, vacíalo antes desde la consola).

## Problemas típicos
| Síntoma | Causa probable |
|---|---|
| `AccessDeniedException` al invocar el modelo | Modelo no habilitado en la región, o el rol no tiene permiso sobre el inference profile Y los modelos fundacionales de sus regiones |
| `ThrottlingException` | Cuota de tokens/minuto; el backoff lo absorbe. Si persiste, bajar `N_CORRIDAS_EVALUAR` |
| `Task timed out` | Nota muy larga: subir el timeout o bajar corridas |
| `Runtime.ImportModuleError` | Librería compilada empaquetada para Windows → `sam build --use-container` |
| `ExpiredToken` | Claves temporales vencidas → paso 1 |
