# Plan de implementación: conectar la FOTO de post-it al flujo de Huellita (Opción A)

Fuente normativa: `c:\dev\hackaton\.agents\tasks\postits-ocr-conexion-investigacion.md` (Opción A). Este plan NO re-decide el diseño: lo aplica contra los archivos reales del worktree.

Worktree: `c:\dev\hackaton\.worktrees\huellita-aws`, rama `feature/huellita-aws`. NO tocar `main`. NO crear worktree nuevo.
- BFF: `c:\dev\hackaton\.worktrees\huellita-aws\huellita-web`
- Front: `c:\dev\hackaton\.worktrees\huellita-aws\huellita-formato-mejorado`

Entorno Windows/PowerShell: separador `;`, NUNCA `&&`. `npm` no está en PATH: usar el shim `c:\dev\hackaton\.worktrees\.herramientas\bin\npm.cmd`. SAM: `"C:\Program Files\Amazon\AWSSAMCLI\bin\sam.cmd"`. AWS: exportar credenciales en la MISMA línea antes de cada comando:
`aws configure export-credentials --profile hackaton --format powershell | Out-String | Invoke-Expression`

Comandos reales descubiertos:
- BFF tests: desde `huellita-web`, `.\.venv\Scripts\python.exe -m pytest` (pytest 9.1.1 ya instalado; `pyproject.toml` fija `pythonpath=["src"]`, `testpaths=["tests"]`).
- Front build: desde `huellita-formato-mejorado`, `& "c:\dev\hackaton\.worktrees\.herramientas\bin\npm.cmd" run build` (`tsc -b && vite build`).
- Front tests: `& "c:\dev\hackaton\.worktrees\.herramientas\bin\npm.cmd" run test` (`vitest run`).
- Deploy BFF: desde `huellita-web`, `& "C:\Program Files\Amazon\AWSSAMCLI\bin\sam.cmd" build` luego `... sam.cmd deploy --profile hackaton --region us-east-1` (`samconfig.toml` ya trae stack `huellita-web`, región y parámetros).

Contrato postits-ocr (NORMATIVO, verificado leyendo `postits-ocr/ocr.py`):
- Lambda `arn:aws:lambda:us-east-1:277702547089:function:postits-ocr`, cuenta 277702547089, us-east-1. Solo `lambda:InvokeFunction` (RequestResponse). Timeout 60 s.
- La foto debe estar en S3 bajo `capturas/{id}/original/foto.jpg` (o `.jpeg`/`.png`) ANTES de invocar. Acepta JPEG/PNG, RECHAZA HEIC/HEIF, máx 25 MiB.
- Evento JSON: `{"id_captura","id_educadora","sala_grupo","fecha_observacion","modo":"opencv","escribir_texto":true,"incluir_urls":false}`. Respeta `meta.json` si ya existe.
- Respuesta síncrona: éxito trae `n_postits`, `partes[]`, etc.; error trae `{"error": {"codigo","mensaje"}}` con códigos: `PETICION_INVALIDA`, `FORMATO_NO_SOPORTADO`, `IMAGEN_NO_ENCONTRADA`, `IMAGEN_DEMASIADO_GRANDE`, `IMAGEN_NO_DECODIFICABLE`, `LECTURA_NO_DISPONIBLE`, `ERROR_ALMACENAMIENTO`, `CONFIGURACION`, `ERROR_INTERNO`.
- Al escribir `meta.json`/`texto.json`, S3 dispara `ProcesarNota`, que llena los registros que la UI lee por `GET /api/salas/{sala}/registros`. La recogida NO necesita código nuevo.

---

## BACKEND (huellita-web)

- [ ] 1. Añadir código de error de imagen a `errores.py`.
      Agregar a `CODIGOS_HTTP` y `MENSAJES` los códigos del BFF para foto: `foto_invalida` (422), `foto_demasiado_grande` (413), `formato_foto_no_soportado` (415), `ocr_sin_lectura` (502), `ocr_caido` (502). Mensajes en palabras de la tía, sin nombrar AWS. Mantener el estilo de los existentes.
      Archivos: `c:\dev\hackaton\.worktrees\huellita-aws\huellita-web\src\huellita_api\errores.py`
      Verify: desde `huellita-web`, `.\.venv\Scripts\python.exe -m pytest tests\test_app.py` sigue en verde (los códigos nuevos no rompen el mapeo).

- [ ] 2. Añadir variable de entorno `FUNCION_OCR` a `config.py`.
      Agregar el campo `funcion_ocr: str` a la dataclass `Config` y leerlo en `cargar_config` con `entorno.get("FUNCION_OCR", "")`. Es el nombre o ARN de la Lambda OCR.
      Archivos: `c:\dev\hackaton\.worktrees\huellita-aws\huellita-web\src\huellita_api\config.py`
      Verify: `.\.venv\Scripts\python.exe -m pytest tests\test_rutas_capturas.py tests\test_capturas.py` en verde (los `cargar_config({...})` de prueba no exigen la clave nueva por tener defecto).

- [ ] 3. Añadir en `s3.py` la subida de BYTES de imagen.
      Nueva función `clave_foto(id_captura, ext="jpg") -> f"capturas/{id}/original/foto.{ext}"` y `subir_imagen(cfg, clave, datos: bytes, content_type: str) -> None` que haga `put_object` con `Body=datos` y `ContentType` (`image/jpeg` o `image/png`). Reusar `cliente()` y `AJUSTES` existentes.
      Archivos: `c:\dev\hackaton\.worktrees\huellita-aws\huellita-web\src\huellita_api\s3.py`
      Verify: ampliar/ejecutar `.\.venv\Scripts\python.exe -m pytest tests\test_s3.py` con un caso nuevo que verifique `Bucket`, `Key=capturas/{id}/original/foto.jpg`, `ContentType=image/jpeg` y `Body` en bytes.

- [ ] 4. Crear el adaptador aislado `ocr.py` (molde de `transcriptor.py`).
      Nuevo módulo con cliente boto3 `lambda` creado con `ConfigBotocore(connect_timeout=5, read_timeout=70, retries={"max_attempts": 1})` (read_timeout > 60 s de la Lambda, sin reintentos). Función `invocar(cfg, id_captura, id_educadora, sala_grupo, fecha) -> dict`: construye el evento del contrato, llama a `invoke(FunctionName=cfg.funcion_ocr, InvocationType="RequestResponse", Payload=...)`, parsea el `Payload`, y si trae `error.codigo` lo TRADUCE a un código del BFF con una tabla `_CODIGOS`: `FORMATO_NO_SOPORTADO→formato_foto_no_soportado`, `IMAGEN_DEMASIADO_GRANDE→foto_demasiado_grande`, `IMAGEN_NO_ENCONTRADA/IMAGEN_NO_DECODIFICABLE/PETICION_INVALIDA→foto_invalida`, `LECTURA_NO_DISPONIBLE→ocr_sin_lectura`, resto (`ERROR_ALMACENAMIENTO`,`CONFIGURACION`,`ERROR_INTERNO`, desconocido)→`ocr_caido`. Clase `ErrorOcr(Exception)` con `.codigo`. Caso especial ROBUSTEZ: si boto3 lanza `ReadTimeoutError`/`ConnectTimeoutError` o cualquier timeout de red, NO traducir a error: lanzar `OcrEnProceso` (excepción distinta) para que la ruta trate la captura como "procesando". Logs solo con ids y códigos, nunca el payload de imagen.
      Archivos: `c:\dev\hackaton\.worktrees\huellita-aws\huellita-web\src\huellita_api\ocr.py`
      Verify: nuevo `tests\test_ocr.py` con un `lambda` falso (monkeypatch de `boto3`) que ejercite: evento exacto enviado, traducción de cada código de error, y que un timeout levanta `OcrEnProceso`. `.\.venv\Scripts\python.exe -m pytest tests\test_ocr.py` en verde.

- [ ] 5. Crear `datos/foto.py` (molde de `datos/audio.py`).
      Función `enviar(cfg, id_captura, id_educadora, sala_grupo, fecha) -> None`: llama a `ocr.invocar(...)`; si `ErrorOcr`, marca la fila `error_envio` y re-lanza `errores.error(falla.codigo)`; si `OcrEnProceso`, NO falla: deja la fila `enviada` y retorna (ProcesarNota terminará). Decodificación/validación de la imagen base64 vive aquí: `decodificar(foto_base64) -> (bytes, content_type)` que valida base64 (`foto_invalida`), tamaño (tope del front, ver paso 7; rechazar > ~5.5 MiB para quedar bajo 6 MB de payload con `foto_demasiado_grande`) y detecta magic bytes JPEG (`FF D8 FF`) / PNG (`89 50 4E 47`); HEIC/HEIF (ftyp `heic`/`heif`/`mif1`) → `formato_foto_no_soportado`.
      Archivos: `c:\dev\hackaton\.worktrees\huellita-aws\huellita-web\src\huellita_api\datos\foto.py`
      Verify: nuevo `tests\test_foto.py` cubre: decodifica JPEG y PNG válidos; rechaza base64 roto, HEIC y sobre-tamaño; `enviar` marca `error_envio` ante `ErrorOcr` y NO ante `OcrEnProceso`. `.\.venv\Scripts\python.exe -m pytest tests\test_foto.py` en verde.

- [ ] 6. Conectar la rama `foto` en `rutas/capturas.py`.
      Añadir `"foto"` a `FORMATOS`. Añadir campo `fotoBase64: str | None = None` a `CapturaEntrada` en `modelos.py`. En `crear_captura`, para `foto` validar con `foto.decodificar(entrada.fotoBase64)` (422/413/415 antes de tocar S3/Lambda). En `_entregar`: para `foto`, escribir `meta.json` PRIMERO (reusar `s3.cuerpo_meta`), luego subir la imagen con `s3.subir_imagen(cfg, s3.clave_foto(id, ext), datos, content_type)`, luego `foto.enviar(cfg, id, autorId, salaId, dia)`. Un fallo de escritura S3 deja `error_envio` + 502 (igual que hoy). La respuesta 201 deja la evidencia en `procesando`. NO escribir `texto.json` para foto (lo escribe postits-ocr).
      Archivos: `c:\dev\hackaton\.worktrees\huellita-aws\huellita-web\src\huellita_api\rutas\capturas.py`, `c:\dev\hackaton\.worktrees\huellita-aws\huellita-web\src\huellita_api\modelos.py`
      Verify: ampliar `tests\test_rutas_capturas.py` con casos foto: 201 con `meta.json` + `original/foto.jpg` escritos y OCR invocado; 413/415/422 ante foto mala; 502 ante fallo S3; `OcrEnProceso` deja 201 `procesando`. `.\.venv\Scripts\python.exe -m pytest` (toda la suite) en verde.

- [ ] 7. Permisos IAM y variable OCR en `template.yaml` + `samconfig.toml`.
      En `template.yaml`: nuevo `Parameter` `FuncionOcr` (Default `postits-ocr`, patrón de nombre o ARN de Lambda) y pasar `FUNCION_OCR: !Ref FuncionOcr` en `Environment.Variables` de `FuncionApi`. En `Policies` de `FuncionApi` añadir DOS statements: `lambda:InvokeFunction` sobre `arn:${AWS::Partition}:lambda:${AWS::Region}:${AWS::AccountId}:function:${FuncionOcr}` (si `FuncionOcr` es un ARN completo, usar un parámetro aparte o condicionar; para la demo asumir nombre simple `postits-ocr`), y ampliar `EscribirCapturaEnS3` (o un statement nuevo) con `s3:PutObject` sobre `arn:${AWS::Partition}:s3:::${BucketCapturas}/capturas/*/original/*`. En `samconfig.toml` añadir `FuncionOcr=\"postits-ocr\"` al `parameter_overrides`. Decisión: parametrizar por NOMBRE simple (`postits-ocr`) y construir el ARN en la plantilla, coherente con cómo ya se referencian otros recursos por nombre.
      Archivos: `c:\dev\hackaton\.worktrees\huellita-aws\huellita-web\template.yaml`, `c:\dev\hackaton\.worktrees\huellita-aws\huellita-web\samconfig.toml`
      Verify: `& "C:\Program Files\Amazon\AWSSAMCLI\bin\sam.cmd" validate --lint` (exportar credenciales antes) sin errores; `sam build` compila.

## FRONTEND (huellita-formato-mejorado)

- [ ] 8. Habilitar foto en `services/http.ts`.
      Poner `readonly admiteFoto = true`. En `guardarEvidencia`, quitar el `throw` de `formato === 'foto'` y añadir rama foto: exigir `archivo`; reducir SIEMPRE con `reducirFoto(archivo)` de `lib/fotos.ts` (lado mayor 1000 px, JPEG 0.72) → data URL `data:image/jpeg;base64,...`; extraer solo la parte base64 (quitar el prefijo `data:...;base64,`); si `reducirFoto` devuelve `undefined`, lanzar `ErrorParaTia('No pudimos preparar la foto. Intenta con otra.', 'foto_invalida')` (nunca enviar el original crudo/HEIC); verificar que el base64 pese < ~5.5 MB antes de enviar; poner `entrada.fotoBase64 = base64` y `entrada.mimeType = 'image/jpeg'`. El POST a `/capturas` y la actualización optimista a `procesando` ya existen y se reusan.
      Archivos: `c:\dev\hackaton\.worktrees\huellita-aws\huellita-formato-mejorado\src\services\http.ts`
      Verify: ampliar `src\services\http.test.ts` con un caso foto: envía `fotoBase64` y `mimeType=image/jpeg`, NO envía el blob crudo, y aparece `procesando` en el caché. `& "...npm.cmd" run test`.

- [ ] 9. Verificar el cableado de UI (Dock + Captura + captura.ts).
      Al pasar `admiteFoto=true`, `Dock.tsx` ya muestra "Subir foto" (filtra solo cuando `admiteFoto === false`). `app/captura.tsx` ya conecta `HojaFoto.onEnviar → enviarFoto → capturar('foto', archivo)` y `services/captura.ts` ya pasa `archivo` a `guardarEvidencia` y, en modo servidor, no llama a la IA local. No se requiere cambio salvo que la verificación muestre lo contrario; si `services/datos.ts` necesita documentar `admiteFoto`, es un ajuste de comentario, no de lógica.
      Archivos (solo si hace falta): `c:\dev\hackaton\.worktrees\huellita-aws\huellita-formato-mejorado\src\app\captura.tsx`, `src\services\captura.ts`, `src\services\datos.ts`
      Verify: `& "...npm.cmd" run test` (incluye `app/version-aws.test.tsx` y `services/captura.test.ts`) y `& "...npm.cmd" run build` sin errores de tipos.

## INFRA + VERIFICACIÓN END-TO-END

- [ ] 10. Desplegar el BFF a AWS.
      Desde `huellita-web`, exportar credenciales y `sam build` + `sam deploy --profile hackaton --region us-east-1`. Si `sam deploy` falla con `AccessDenied` de `cloudfront:*`, aplicar el Plan B documentado en `template.yaml`/`DESPLIEGUE.md §7` (no es parte del cambio de foto; documentarlo si ocurre).
      Verify: `sam deploy` termina `CREATE_COMPLETE`/`UPDATE_COMPLETE`; `aws lambda get-function-configuration --function-name huellita-web-... ` muestra `FUNCION_OCR` en el entorno (o revisar el changeset).

- [ ] 11. Verificación end-to-end foto contra AWS (robustez demo).
      Con los audios y fotos de prueba del directorio de hackaton, ejercitar `POST /api/capturas` con `formato:"foto"` y `fotoBase64` contra la URL real (CloudFront o `UrlApiDirecta`), y confirmar por `GET /api/salas/{sala}/registros` que aparece la evidencia `foto` y luego las sugerencias generadas por ProcesarNota. Medir latencia foto→sugerencia para la demo en vivo. Verificar que texto y audio siguen funcionando (no regresión). Documentar: una foto → N post-its → N sugerencias agrupadas por `archivo_s3`; si la pantalla Revisar no agrupa por recorte, dejarlo como salvedad NO bloqueante.
      Archivos: ninguno (verificación); registrar hallazgos en el reporte final.
      Verify: una captura foto real llega a `lista`/con sugerencias vía `/registros`; texto y audio sin regresión.

## RIESGOS (reflejados en el plan)
- Límite 6 MB de payload Lambda: mitigado reduciendo SIEMPRE a JPEG en el front (paso 8) y rechazando > ~5.5 MB en front y BFF.
- HEIC de iPhone: `reducirFoto` produce JPEG en el front; el BFF además rechaza HEIC/HEIF por magic bytes antes de la Lambda (pasos 5 y 8).
- Latencia/timeout: `ocr.py` usa `read_timeout` > 60 s y, ante timeout, `OcrEnProceso` deja la captura `procesando` sin caerla (pasos 4-6).
- N post-its → N sugerencias agrupadas por `archivo_s3`: mejora de UX opcional; si Revisar no agrupa, se documenta como salvedad NO bloqueante (paso 11).
- IAM: dos permisos nuevos requieren `sam deploy` (paso 7 y 10).
