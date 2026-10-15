# Transcriptor de audio

Recibe un audio, lo transcribe con Amazon Transcribe por lotes y entrega un JSON con el texto, cada palabra con su confianza y el estado del trabajo. Es un servicio aparte: otra parte del backend lo llama por HTTP y procesa el JSON.

```
POST /api/transcripciones/audio  ->  Lambda API  ->  S3 audio/  ->  Amazon Transcribe
                                 <-  202 "transcribiendo"
Transcribe termina  ->  EventBridge  ->  Lambda eventos  ->  S3 resultados/{id_trabajo}.json
GET /api/transcripciones/{id_trabajo}  ->  Lambda API  ->  JSON actual
```

- No hay base de datos. El estado vive en Transcribe y el JSON final en S3.
- `id_captura` es la clave de idempotencia: repetir el POST no transcribe dos veces.
- Si se pierde el evento de EventBridge, el GET arma y guarda el resultado igual.

## Qué está desplegado (15 de octubre de 2026)

- Cuenta del hackathon `277702547089`, región `us-east-1`, stack `transcriptor-audio`.
- API: `https://289khkzbpd.execute-api.us-east-1.amazonaws.com/v1`. La clave no está en el repositorio: se obtiene con los comandos de la sección Despliegue.
- Funciones: `transcriptor-audio-FuncionApi-…` (POST y GET) y `transcriptor-audio-FuncionEventos-…` (aviso de Transcribe por EventBridge).
- Bucket propio: `transcriptor-audio-buckettranscripcion-unphdbe1iiqk`. La entrega va a `integra-capturas-277702547089`, que activa `ProcesarNota`.
- Pruebas de punta a punta: `CAP-01M50AKPA2BHDCXSJATACZ6N3W` (audio y texto) y `CAP-01M508E1WXXYXW3KAP0S99M9Z5` (solo texto, antes de que se copiara el audio). Se ven en `integra-capturas` y en las tablas Registros y Observaciones, consultando por `id_captura`.
- Para cambiar el código: `sam build` y `sam deploy --profile <perfil>`, que leen `samconfig.toml`. Es un solo stack para todo el equipo, así que avisen antes de desplegar.

## Contrato

JSON Schema en `contrato/resultado_transcripcion.schema.json` y ejemplos en `contrato/ejemplos/` (`transcribiendo`, `completado`, `fallido`). Sigue `TextoTranscrito` de `design.md` y agrega `id_captura`, `origen`, `estado` y `error`. Para regenerar los ejemplos: `python scripts/generar_ejemplos.py`.

- `texto_completo`: la transcripción entera con puntuación, sin el tope de 280 caracteres.
- `palabras`: texto, `inicio_segundos`, `fin_segundos`, `confianza` (0 a 1) y `dudosa` (confianza menor que 0,60). No incluye la puntuación.
- `confianza_agregada`: promedio de las palabras, o `null` si no hay voz.
- `id_trabajo`: `tr-` más `id_captura`. Es el ID que usa el GET.
- `error`: `{codigo, mensaje}` solo en `fallido`. Códigos: `transcripcion_fallida`, `resultado_no_disponible` y `resultado_invalido`.

## Entrega a ProcesarNota

Cuando un trabajo termina con texto, el transcriptor deja dos archivos en `integra-capturas-277702547089` (parámetro `BucketCapturas`): el audio en `capturas/{id_captura}/original/audio.<ext>` y `capturas/{id_captura}/texto.json`. Este último activa `ProcesarNota` del stack `integra-procesador`, que guarda el texto en `texto_literal` y la ruta del audio en `archivo_s3` de cada observación (tabla Observaciones):

```json
{"id_captura": "CAP-01M508E1WXXYXW3KAP0S99M9Z5", "fuente": "audio", "partes": [{"texto": "Hola, Agustín, hoy día levantó una torre.", "archivo": "original/audio.mp4"}]}
```

- `meta.json` lo escribe otra parte del sistema y tiene que existir antes que `texto.json`; si no, ProcesarNota marca la captura en ERROR. Si todavía no existe, el transcriptor espera: Lambda reintenta el evento dos veces en unos 3 minutos y cada GET vuelve a intentar.
- Solo se entrega si `id_captura` tiene el formato `CAP-<ULID>` que exige ProcesarNota, el trabajo terminó en `completado` y hay texto.
- El audio se copia antes de escribir `texto.json`. Si ya no está (por ejemplo, venció a 1 día), se entrega solo el texto.
- `texto.json` se escribe una sola vez (escritura condicional de S3), así ProcesarNota no procesa dos veces la misma captura.
- Probado de punta a punta el 2026-10-15: audio en `original/`, `texto.json` en 20 s, registro `PROCESADO` y observación con `texto_literal` y `archivo_s3`. La extensión sigue al formato recibido: la Grabadora de Windows y Safari generan `mp4`, Chrome genera `webm`.
## API

En AWS todas las rutas exigen la cabecera `x-api-key`.

`POST /api/transcripciones/audio`

```json
{"id_captura": "CAP-000012", "audio_base64": "<audio en base64>", "idioma": "es-US"}
```

- `idioma` es opcional: `es-US`, `es-MX` o `es-ES`.
- Formatos: webm, ogg, mp4/m4a, mp3, wav, flac y amr. Se detecta por los bytes del archivo, no por el tipo MIME.
- Máximo 4 MiB de audio. Con MediaRecorder, `audioBitsPerSecond: 48000` deja 300 s en unos 1,8 MB.
- Responde 202 con el JSON en `transcribiendo`, o 200 si ese `id_captura` ya tenía resultado final.

`GET /api/transcripciones/{id_trabajo}` responde 200 con el JSON actual o 404. Consulte cada 5 s. En la prueba real, notas de 10 a 20 s tardaron unos 15 a 30 s.

`GET /api/salud` responde `{"estado": "ok", "modo": "aws"}` (o `"mock"`).

Los errores del servicio tienen la forma `{"error": {"codigo", "mensaje"}}`. Los 403 y 429 los responde API Gateway con `{"message": ...}`.

| HTTP | Código | Qué hacer |
|---|---|---|
| 400 | `base64_invalido`, `audio_vacio` | Corregir el cuerpo |
| 403 | (API Gateway) | Falta la clave o es inválida |
| 404 | `trabajo_no_encontrado` | Revisar `id_trabajo` |
| 409 | `id_en_uso` | Otro trabajo de la cuenta tiene ese nombre: usar otro `id_captura` |
| 413 | `audio_demasiado_grande` | Bajar el bitrate o la duración |
| 415 | `formato_no_soportado` | Usar un formato de la lista |
| 422 | `solicitud_invalida` | Ver el mensaje |
| 429 | (API Gateway) | Límite del plan de uso: esperar |
| 502 | `error_proveedor` | Reintentar una vez |
| 503 | `servicio_saturado` | Reintentar después de `Retry-After` |
| 504 | `tiempo_agotado` | Reintentar |

## Local (Windows, PowerShell)

```powershell
cd servicio_transcripcion
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\cfn-lint.exe template.yaml
$env:MODO_MOCK = "1"
.\.venv\Scripts\python.exe -m uvicorn transcriptor.app:app --app-dir src --port 8000
```

En otra terminal: `.\.venv\Scripts\python.exe scripts\probar_audio.py nota.m4a`. El modo mock no llama a AWS. Un `id_captura` que contenga `fallido` o `transcribiendo` simula ese estado. La documentación interactiva queda en http://127.0.0.1:8000/docs.

## Despliegue

Requisitos: AWS CLI v2, AWS SAM CLI y Python 3.13 en el PATH (`sam build` descarga las dependencias para Lambda arm64; no hace falta Docker). Compruebe las credenciales con `aws sts get-caller-identity`.

```powershell
cd servicio_transcripcion
sam validate --lint
sam build
sam deploy --guided --stack-name transcriptor-audio --capabilities CAPABILITY_IAM
```

Elija una región con Transcribe, por ejemplo `us-east-1`. Después del primer despliegue, `samconfig.toml` guarda la configuración y basta con `sam build` y `sam deploy`. Para obtener la URL y la clave:

```powershell
$salida = { param($k) aws cloudformation describe-stacks --stack-name transcriptor-audio --query "Stacks[0].Outputs[?OutputKey=='$k'].OutputValue" --output text }
$env:TRANSCRIPTOR_URL = & $salida UrlApi
$env:TRANSCRIPTOR_API_KEY = aws apigateway get-api-key --api-key (& $salida IdClaveApi) --include-value --query value --output text
.\.venv\Scripts\python.exe scripts\probar_audio.py nota.m4a
```

La Grabadora de sonido de Windows guarda `.m4a`, así sirve para la prueba. Guarde la clave como secreto del otro backend, nunca en el repositorio. `ModoMock=1` despliega una versión que no llama a Transcribe, para integrar sin costo.

Para borrar todo (CloudFormation no borra un bucket con objetos):

```powershell
aws s3 rm "s3://$(& $salida Bucket)" --recursive
sam delete --stack-name transcriptor-audio
```

## Configuración

| Parámetro SAM | Variable | Defecto |
|---|---|---|
| `Idioma` | `TRANSCRIBE_IDIOMA` | `es-US` |
| `UmbralPalabraDudosa` | `UMBRAL_PALABRA_DUDOSA` | `0.60` |
| `PrefijoTrabajo` | `PREFIJO_TRABAJO` | `tr-` |
| `LimiteDiario` | (plan de uso) | 2000 solicitudes al día |
| `ModoMock` | `MODO_MOCK` | `0` |
| `BucketCapturas` | `BUCKET_CAPTURAS` | `integra-capturas-277702547089` |
| (lo crea la plantilla) | `BUCKET` | |
| (fijo) | `MAX_BYTES_AUDIO` | 4194304 |

## Costos

Transcribe cobra unos US$0,024 por minuto de audio, por segundo (primer tramo, según fuentes de 2026; verificar en https://aws.amazon.com/transcribe/pricing/). 100 notas de 1 minuto cuestan unos US$2,40. Lambda, API Gateway, S3 y EventBridge cuestan centavos con uso de hackathon. Cree una alerta de AWS Budgets antes de compartir la URL.

## Seguridad y privacidad

- La clave de API identifica al cliente y limita el uso (5 por segundo, 2000 al día), pero no autentica usuarios. Úsela solo desde el backend, nunca en el navegador. En producción conviene autorización IAM entre servicios.
- El bucket es privado, cifrado y solo acepta HTTPS. En el bucket del transcriptor, el audio se borra cuando termina el trabajo. La copia en `integra-capturas` no vence, porque ese bucket no tiene regla de ciclo de vida: hay que borrarla a mano o agregar una regla. La salida cruda y el JSON final se borran al día siguiente (S3 lo hace a medianoche UTC y puede tardar hasta un día más), así que el otro backend debe copiar el JSON a su base de datos.
- Los logs guardan solo IDs, tamaños y estados, nunca audio ni texto. Se retienen 7 días.
- Amazon Transcribe guarda y usa el audio para mejorar el servicio por defecto. Solo se desactiva con una política de AWS Organizations (https://docs.aws.amazon.com/transcribe/latest/dg/opt-out.html), que quizás no se pueda crear en la cuenta del hackathon. Para la demo use voces del equipo y contenido ficticio.

## Pendiente

- `design.md` pide FastAPI con PostgreSQL y un trabajador, sin Lambda. Este servicio usa Lambda y SAM por decisión del equipo; el trabajador del diseño puede llamarlo por HTTP.
- El audio viaja en base64 dentro del JSON (máximo 4 MiB). Para audios más grandes, el paso siguiente es subirlos a S3 con una URL prefirmada.
- Falta elegir el idioma con voces chilenas: comparar `es-US`, `es-MX` y `es-ES`.
- Probado en la cuenta del hackathon (us-east-1, stack `transcriptor-audio`) con dos notas de voz reales: transcripción, idempotencia y guardado por EventBridge funcionan. Falta medir la precisión con más voces y con ruido de sala.