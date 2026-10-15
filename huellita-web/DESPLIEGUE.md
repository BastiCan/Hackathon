# Despliegue y verificación de Huellita en AWS

Todo lo de este archivo lo corre **una persona**, no un agente: la cuenta `277702547089`
(región `us-east-1`) y los stacks son compartidos, así que **avisa al equipo antes de
desplegar o borrar**. Stack de este componente: `huellita-web`.

Orden normal: entorno (§0) → `sam deploy` (§1) → `publicar_front.ps1` (§2) → curl (§3) →
`smoke.py` (§4) → logs (§5). Los planes B están en §7 y §8; el borrado, en §9.

## 0. Entorno de este equipo (crítico: sin esto los comandos fallan)

- **SAM CLI no está en el PATH**: usa `C:\Program Files\Amazon\AWSSAMCLI\bin\sam.cmd`.
- **npm no está en el PATH**: está en `c:\dev\hackaton\.worktrees\.herramientas\bin`
  (`publicar_front.ps1` lo busca ahí solo; si no, pásalo con `-Npm`).
- El perfil `hackaton` usa `aws login`, y **boto3 y SAM fallan con él** hasta que exportes
  las credenciales a la sesión actual (no imprime ningún valor):

  ```powershell
  aws configure export-credentials --profile hackaton --format powershell | Out-String | Invoke-Expression
  ```

- **`cfn-lint` no está disponible** (choca con la versión de pydantic de
  `requirements-dev.txt`). Valida con `sam validate --lint`; si falla, repórtalo en vez de
  forzar la instalación.
- PowerShell: el separador de comandos es `;`, **nunca `&&`**. Y `curl` es un alias de
  `Invoke-WebRequest`, así que en §3 se usa `curl.exe`.

## 1. Desplegar el stack

```powershell
cd c:\dev\hackaton\.worktrees\huellita-aws\huellita-web
aws configure export-credentials --profile hackaton --format powershell | Out-String | Invoke-Expression
$sam = "C:\Program Files\Amazon\AWSSAMCLI\bin\sam.cmd"
& $sam validate --lint --template template.yaml --region us-east-1
& $sam build
& $sam deploy --profile hackaton --region us-east-1
```

`samconfig.toml` ya trae el nombre del stack, la región y los parámetros, así que `sam deploy`
no pregunta nada. Al terminar, las salidas:

```powershell
aws cloudformation describe-stacks --stack-name huellita-web --profile hackaton --region us-east-1 --query "Stacks[0].Outputs" --output table
```

| Salida | Para qué |
|---|---|
| `UrlApp` | la URL HTTPS de CloudFront que se abre en el celular |
| `UrlApiDirecta` | la HTTP API sin pasar por CloudFront, solo para depurar |
| `BucketWeb` | bucket privado donde vive el build (lo usa `publicar_front.ps1`) |
| `IdDistribucion` | distribución a invalidar después de publicar |

Si `sam deploy` falla con un `AccessDenied` de `cloudfront:*`, ve al plan B (§7).

## 2. Publicar el frontend

```powershell
cd c:\dev\hackaton\.worktrees\huellita-aws\huellita-web
.\scripts\publicar_front.ps1
```

Hace, en este orden: lee `UrlApp`, `BucketWeb` e `IdDistribucion` del stack; en
`huellita-formato-mejorado/` corre `npm ci` y `npm run build` con `VITE_DATOS=http` y
`VITE_AGENDA=false`; sube `dist` con `aws s3 sync --delete` en **dos pasadas** (primero
`assets/*` con `public,max-age=31536000,immutable`, después todo lo demás —incluidos
`index.html`, `sw.js`, `registerSW.js` y `manifest.webmanifest`— con `no-cache`, para que la
PWA se actualice); invalida `"/*"` en CloudFront e imprime la `UrlApp`.

Parámetros opcionales: `-Stack`, `-Perfil`, `-Region` y `-Npm`. La invalidación tarda uno o
dos minutos: si el celular sigue mostrando la versión anterior, espera y recarga.

## 3. Verificación con curl

```powershell
$app = "https://d111111abcdef8.cloudfront.net"   # la salida UrlApp
```

**`/` y `/sala` devuelven el mismo `index.html`** (la función SPA reescribe las rutas sin punto):

```powershell
curl.exe -s -o $env:TEMP\raiz.html -w "/ -> %{http_code} %{content_type}\n" "$app/"
curl.exe -s -o $env:TEMP\sala.html -w "/sala -> %{http_code} %{content_type}\n" "$app/sala"
(Get-FileHash $env:TEMP\raiz.html).Hash -eq (Get-FileHash $env:TEMP\sala.html).Hash
Select-String -Path $env:TEMP\raiz.html -Pattern "<title>"
```

Esperado: `200 text/html` en las dos, `True` (es el mismo archivo) y el `<title>` de Huellita.

**`/api/salud` responde JSON:**

```powershell
curl.exe -s -w "\n%{http_code} %{content_type}\n" "$app/api/salud"
```

Esperado: `{"estado":"ok"}` con `200 application/json`.

**`/api/no-existe` responde 404 en JSON** (no `index.html`: la distribución no tiene respuestas
de error personalizadas):

```powershell
curl.exe -s -w "\n%{http_code} %{content_type}\n" "$app/api/no-existe"
```

Esperado: `{"error":{"codigo":"no_encontrado","mensaje":"..."}}` con `404 application/json`.

**Un archivo de `assets/` llega con caché inmutable:**

```powershell
$asset = (Select-String -Path $env:TEMP\raiz.html -Pattern "/assets/[-A-Za-z0-9_.]+" -AllMatches).Matches[0].Value
curl.exe -sI "$app$asset" | Select-String -Pattern "HTTP/|^cache-control|^content-type"
```

Esperado: `200` y `cache-control: public,max-age=31536000,immutable`.

**`index.html` llega con `no-cache`:**

```powershell
curl.exe -sI "$app/" | Select-String -Pattern "HTTP/|^cache-control|^content-type"
Remove-Item $env:TEMP\raiz.html, $env:TEMP\sala.html
```

Esperado: `200`, `cache-control: no-cache` y `content-type: text/html`.

## 4. Prueba de humo

```powershell
cd c:\dev\hackaton\.worktrees\huellita-aws\huellita-web
.\.venv\Scripts\python.exe scripts\smoke.py $app
.\.venv\Scripts\python.exe scripts\smoke.py $app --audio "C:\ruta\nota.m4a"    # flujo de voz
```

Solo usa la biblioteca estándar y no necesita credenciales de AWS: habla con el BFF por HTTPS
con la cabecera `X-Usuaria-Id: EDU-0001`. Recorre salud, contexto, los niños de `SG-A`, crea
una nota de texto con el nombre del primer niño de la sala, espera hasta 5 minutos a que quede
`lista`, confirma una de sus sugerencias, comprueba releyendo que quedó `aceptada` y la
devuelve a `pendiente`. Sale con `0` si todo pasó y con `1` describiendo el primer paso que
falló. `--help` explica las opciones.

La nota y la decisión quedan en la cuenta: es una captura real de `SG-A` del día. Si no quieres
que aparezca en la demo, archívala desde Revisar.

## 5. Los logs no pueden traer texto de notas ni audio

```powershell
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/huellita-web --query "logGroups[].logGroupName" --output table --profile hackaton --region us-east-1
$grupo = "/aws/lambda/huellita-web-api"
aws logs tail $grupo --since 1h --format short --profile hackaton --region us-east-1 > $env:TEMP\huellita-logs.txt
Select-String -Path $env:TEMP\huellita-logs.txt -Pattern "audio_base64","audioBase64","apil","cubos","torre","texto_extraido","textoExtraido","x-api-key","Bearer"
Remove-Item $env:TEMP\huellita-logs.txt
```

Esperado: `Select-String` **no imprime nada**. Cualquier coincidencia es contenido de una nota,
audio o la clave del transcriptor en los logs, y hay que quitar ese `log` antes de la demo.

Se usa `aws logs tail` más `Select-String` porque `--filter-pattern` necesita comillas dobles
que PowerShell se come. El grupo es el `LogsApi` de la plantilla
(`/aws/lambda/<stack>-api`, retención de 7 días); el `describe-log-groups` de la primera línea
confirma el nombre real.

## 6. Límite de costo: alerta de AWS Budgets (recomendación, **no creada**)

No se creó ningún presupuesto: lo decide quien administra la cuenta del hackathon. La
recomendación es un presupuesto de costo **mensual de USD 20** para toda la cuenta, con avisos
por correo al 50 %, 80 % y 100 % del gasto real y al 100 % del pronóstico. Lo que puede
moverse: Amazon Transcribe (por minuto de audio), CloudFront, Lambda y DynamoDB bajo demanda.
Recuerda que Budgets **solo avisa**, no corta el gasto, y los avisos pueden tardar horas; los
topes duros del sistema son los límites de la HTTP API, el tope diario de capturas y los 4 MiB
de audio.

Para crearlo, con dos archivos JSON (`presupuesto.json` con `BudgetName`, `BudgetLimit`,
`TimeUnit: MONTHLY` y `BudgetType: COST`; `avisos.json` con la lista de
`Notification` + `Subscribers` de correo):

```powershell
# NO se ha ejecutado. Lo corre quien administra la cuenta, con su correo en avisos.json.
aws budgets create-budget --account-id 277702547089 --budget file://presupuesto.json --notifications-with-subscribers file://avisos.json --profile hackaton --region us-east-1
```

Los nombres de los parámetros salen del
[ejemplo de CreateBudget en la CLI](https://docs.aws.amazon.com/code-library/latest/ug/budgets_example_budgets_CreateBudget_section.html)
(contenido reformulado por las restricciones de licencia).

## 7. Plan B: si la cuenta no permite crear CloudFront

Síntoma: `sam deploy` falla con `AccessDenied` o `not authorized` en
`cloudfront:CreateDistribution` o `cloudfront:CreateOriginAccessControl`, o el stack queda en
`ROLLBACK_COMPLETE` por esos recursos. **Hay que avisarlo en el reporte de la tarea 8**, porque
cambia la URL de la demo.

La Lambda del BFF sirve también el build, en el mismo dominio de la API (está documentado al
final de `template.yaml`):

1. Comentar `BucketWeb`, `PoliticaBucketWeb`, `OacWeb`, `FuncionSpa` y `Distribucion`, y dejar
   `UrlApp = UrlApiDirecta` en los Outputs.
2. Agregar a `FuncionApi` el evento raíz (`Path: /{proxy+}`, `Method: ANY`) para que las rutas
   de la SPA lleguen a la función.
3. Copiar `huellita-formato-mejorado\dist` a `huellita-web\src\web\` **antes** de `sam build`;
   `app.py` monta esos archivos en `/` (`StaticFiles` con `html=True`) y deja `/api/*` igual.
   En este plan **no se usa `publicar_front.ps1`** (no hay bucket ni distribución que
   invalidar): el build viaja dentro del paquete de la función, así que publicar es
   `npm run build` con `VITE_DATOS=http` y `VITE_AGENDA=false`, copiar `dist` y volver a
   `sam deploy`. El script, si el stack no trae `BucketWeb` e `IdDistribucion`, corta con un
   mensaje que apunta a esta sección.
4. Consecuencias: el frontend sigue en el mismo origen que `/api` (no hay CORS nuevo), pero se
   pierde la caché de borde y cada GET de la SPA cuesta una invocación de Lambda. Las
   comprobaciones de §3 siguen valiendo cambiando `$app` por `UrlApiDirecta`, con una
   diferencia: los `cache-control` los pone la función, no el `s3 sync`.

## 8. Plan B: clave del transcriptor

Lo normal es que `FuncionApi` lea la clave al arrancar con
`apigateway:GET` acotado a `/apikeys/${IdClaveTranscriptor}` y la guarde **solo en memoria**.
Si ese permiso no alcanza o la clave rota, el plan B es un secreto en Secrets Manager que
**crea Lucas**, sin mostrar su valor a nadie ni pegarlo en un chat, un log o un archivo del
repositorio:

- La plantilla lo referencia con
  `{{resolve:secretsmanager:huellita/transcriptor:SecretString:api_key}}`, así el valor se
  resuelve en el despliegue y nunca pasa por la terminal.
- Alternativa: la función lo lee al arrancar con `secretsmanager:GetSecretValue` **acotado al
  ARN del secreto**, igual que hoy con la clave de API.
- No se corre `get-secret-value` a mano ni se imprime el valor con `--query`: si hay que
  comprobar que existe, basta `aws secretsmanager describe-secret --secret-id huellita/transcriptor`,
  que no devuelve el contenido.

## 9. Borrar el stack

CloudFormation no puede borrar un bucket con archivos, así que primero se vacía `BucketWeb`:

```powershell
aws configure export-credentials --profile hackaton --format powershell | Out-String | Invoke-Expression
$bucket = aws cloudformation describe-stacks --stack-name huellita-web --profile hackaton --region us-east-1 --query "Stacks[0].Outputs[?OutputKey=='BucketWeb'].OutputValue" --output text
aws s3 rm "s3://$bucket" --recursive --profile hackaton --region us-east-1
& "C:\Program Files\Amazon\AWSSAMCLI\bin\sam.cmd" delete --stack-name huellita-web --profile hackaton --region us-east-1
```

Se van con el stack las tablas propias `Capturas` y `Decisiones` (se pierden las capturas y las
decisiones de la demo), la distribución, el bucket web y los logs. **No** se toca nada de
`integra-procesador`, ni el bucket `integra-capturas-277702547089`, ni el stack
`transcriptor-audio`: son de otros componentes y los comparte el equipo.
