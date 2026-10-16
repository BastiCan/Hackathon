# Spec oficial del BFF (entregado por Lucas, 15-10-2026)

Este archivo lo entregó el usuario DESPUÉS de que se congelara `CONTRATOS.md`. **Manda sobre
`CONTRATOS.md`** en cualquier punto donde los dos difieran, y resuelve las cuatro referencias que
quedaron marcadas PENDIENTE DE CONFIRMAR (reglas, tablas propias e infraestructura). Si detectas una
diferencia con `CONTRATOS.md`, sigue este archivo y anótala en tu reporte.

## 1. Contratos de la API

Todas las respuestas son JSON en camelCase, con la forma exacta de los tipos de `tipos.ts`. Los
errores tienen la forma `{"error": {"codigo", "mensaje"}}` y **nunca exponen detalles de AWS**. Ya
están en código en `modelos.py`.

| Ruta | Éxito | Errores |
|---|---|---|
| `GET /api/salud` | 200 con `{"estado": "ok"}`, sin llamar a AWS | |
| `GET /api/contexto` | 200 con `{"jardin": Jardin, "salas": Sala[], "usuarias": Usuaria[]}` | |
| `GET /api/salas/{salaId}/ninos` | 200 con `Nino[]` | 404 si la sala no está en SALAS_DEMO |
| `GET /api/ninos/{id}` | 200 con un `Nino` | 404 |
| `GET /api/salas/{salaId}/registros` | 200 con `{"evidencias": Evidencia[], "sugerencias": Sugerencia[]}`, evidencias ordenadas por `creadaEn` ascendente | |
| `POST /api/capturas` | 201 con `{"evidencia": Evidencia}` en estado `procesando` | ver abajo |
| `POST /api/capturas/{id}/archivar` | 204 | |
| `PUT /api/decisiones` | 200 con `{"sugerencias": Sugerencia[]}`, ya actualizadas | 422 si falla la validación; 404 si la sugerencia no existe |

`POST /api/capturas`
- Cuerpo: `{salaId, autorId, formato: "texto"|"audio", texto?, audioBase64?, mimeType?, ninoIdSugerido?}`.
- Errores:
  - 404: la sala no está habilitada.
  - 422: foto u otro formato, tía inexistente, texto vacío o de más de 5000 caracteres, o base64 inválido.
  - 413 `audio_demasiado_grande`: audio de más de 4 MiB.
  - 429 `tope_diario`: se alcanzó el tope diario.
  - 502 o 503: falla de envío o transcriptor saturado.

`PUT /api/decisiones`
- Cuerpo: `{salaId, usuariaId, items: [{idSugerencia, estado: "aceptada"|"descartada"|"pendiente", cambios?: {ninoId, nucleo, nivel}}]}`, con un máximo de 50 ítems.

## 2. Tablas propias (PAY_PER_REQUEST)

**Capturas**
- Clave `id_captura`; índice `porSala` (`sala_key` + `creada_en`).
- Atributos:
  - Identificación y sala: `sala_key`, `creada_en`, `id_jardin`, `sala_grupo`, `autor_id`, `formato`.
  - Contenido: `nino_id_sugerido?`, `texto_extraido?`, `id_trabajo?`.
  - Estado: `estado_envio` (`enviada` o `error_envio`), `estado_final?` (`lista` o `error`), `archivada?`, `actualizado_en`.
- Contador diario: un ítem con `id_captura = "CONTADOR#AAAA-MM-DD"` y `total`. No tiene `sala_key`, así que no entra al índice.

**Decisiones**
- Clave `sala_key`; orden `id_sugerencia`.
- Atributos: `estado` (`aceptada`, `cambiada` o `descartada`), `nino_id?`, `nucleo?`, `nivel?`, `original?`, `validada_por`, `validada_en`.

## 3. Reglas de traducción (funciones puras en `mapeo.py`)

### Regla 1: Salas
Solo las de SALAS_DEMO (SG-A y SG-B), con `id = sala_grupo` y nombre "Sala A" o "Sala B". El nivel
educativo sale de la **mediana de edad** de sus niños a hoy (ver el ajuste de la regla 4: es
**mediana baja**):

| Edad (meses) | Nivel educativo |
|---|---|
| Menos de 12 | Sala Cuna Menor |
| 12 a 23 | Sala Cuna Mayor |
| 24 a 35 | Medio Menor |
| 36 a 47 | Medio Mayor |
| 48 a 59 | Transición 1 |
| 60 o más | Transición 2 |

### Regla 2: Niños
- Solo los que tienen nombre, con `activo = true`.
- `apellidoInicial` queda vacío, salvo para distinguir homónimos (ver ajuste en disco más abajo).

### Regla 3: Tías
- Salen de `usuarias_demo.json`, con `rol: "tia"`, `jardinId` y una sala cada una.
- Sus ids se validan contra Educadoras. La directora queda pendiente.

### Regla 4: Historial (origen = dataset)
- Evidencia: `{id: id_obs, salaId, autorId: id_educadora, creadaEn: "{fecha}T12:00:00-03:00", formato: "texto", textoExtraido: texto_literal, estado: "lista"}`.
- Una sugerencia por cada dominio distinto entre sus manifestaciones:
  - Identidad: `id: "{id_obs}~{dominio}"`, `evidenciaId: id_obs`, `tipo: "evaluacion"`.
  - Contenido: `ninoId` y `nucleo`: dominio; `nivel`: el de la observación, o el mayor de sus
    manifestaciones; `conducta`: el primer `texto_observable` del dominio; `cita`: ver el ajuste en
    disco; `certeza: "alta"`.
  - Revisión: `estado: "aceptada"`, `validadaPor: id_educadora`, `validadaEn: creadaEn`.

### Regla 5: Sugerencias nuevas (origen = app)
Una por observación, con `id = id_obs`, `evidenciaId = id_captura` y `cita = texto_literal`.
- **PARTICULAR evaluable**: `tipo evaluacion`, con los datos de la manifestación de mayor certeza
  (alta, luego media, luego baja; ante empate, la primera): `nucleo` su dominio; `nivel` el de la
  observación o el de esa manifestación; `conducta` su `texto_observable`; `certeza` la de la
  observación.
- **GENERAL**: `tipo nota_sala`.
- **NO_IDENTIFICADO**: `tipo evaluacion`, sin `ninoId`, salvo que la captura tenga
  `nino_id_sugerido` (nota tomada desde la ficha); `nombreDetectado` es el nombre del primer
  candidato. (Ver DECISIÓN ABIERTA al final de este archivo.)
- **NO_EVALUABLE o con `error_evaluacion`**: `tipo evaluacion` sin `nucleo` ni `nivel`, con una
  `conducta` que explica el motivo, para que la tía corrija o descarte.
- Captura de la app que no está en Capturas (por ejemplo, creada con scripts): su Evidencia se arma
  desde la observación, con `formato audio` si `archivo_s3` apunta a `original/audio`, y estado
  `lista`.

### Regla 6: Estado de una evidencia propia
- `lista`: la tía la archivó, o Registros dice PROCESADO.
- `error`, en cualquiera de estos casos:
  - hubo error de envío;
  - Registros dice SIN_TEXTO o ERROR;
  - es audio y el transcriptor dice `fallido`;
  - lleva más de MINUTOS_MAX_PROCESANDO (20) sin estado final.
- `procesando`: en cualquier otro caso.
- El estado final se guarda en `estado_final` para no volver a consultarlo.
- `texto_extraido` es el texto escrito o la transcripción.

### Regla 7: Decisiones
- Se aplican sobre la sugerencia: `aceptada` o `descartada`; `cambiada`, con `original` y los campos
  corregidos; siempre con `validadaPor` y `validadaEn`.
- Una sugerencia sin decisión queda `pendiente`, y una decisión `pendiente` borra la que había.
- Al guardar con cambios: si son iguales a los de la IA, queda `aceptada`; si difieren, `cambiada`.
  Es la misma lógica de `DataServiceLocal.validar` en `datos.ts` (las líneas 364-377 que citaba el
  plan se movieron; búscala por nombre).
- Solo se aceptan ids que empiezan con `CAP-`. La sugerencia se lee de Observaciones con
  `id_captura = id_obs[:rindex("-p")]`.
- Validaciones: `ninoId` de la sala, `nucleo` entre los 5 dominios y `nivel` de 1 a 9.

### Regla 8
`Ninos.ultimo_nivel` se ignora.

## 4. Infraestructura (`template.yaml`, stack `huellita-web`)

**Parámetros** (los valores reales ya están en `samconfig.toml`)
- Tablas compartidas: TablaJardines, TablaEducadoras, TablaNinos, TablaRegistros, TablaObservaciones.
- Integraciones: BucketCapturas (por defecto `integra-capturas-277702547089`), UrlTranscriptor, IdClaveTranscriptor.
- Demo: JardinDemo (JAR-0001), SalasDemo (SG-A,SG-B), MaxCapturasDia (300), MinutosMaxProcesando (20).

**Recursos del BFF**
- TablaCapturas y TablaDecisiones.
- LogsApi, con retención de 7 días.
- ApiHttp (`AWS::Serverless::HttpApi`): etapa `$default`; `DefaultRouteSettings` 10 solicitudes por
  segundo y ráfaga de 20; `RouteSettings` para `"POST /api/capturas"` 1 por segundo y ráfaga de 3.
- FuncionApi: python3.13, **arm64**, 512 MB, timeout de 25 s, handler `huellita_api.app.handler`;
  logs JSON hacia LogsApi; eventos `ANY /api/{proxy+}` y `POST /api/capturas`.
- Variables de entorno: tablas `TABLA_*` (las cinco compartidas), `TABLA_CAPTURAS`,
  `TABLA_DECISIONES`; integraciones `BUCKET_CAPTURAS`, `URL_TRANSCRIPTOR`, `ID_CLAVE_TRANSCRIPTOR`;
  demo `JARDIN_DEMO`, `SALAS_DEMO`, `MAX_CAPTURAS_DIA`, `MINUTOS_MAX_PROCESANDO`,
  `ZONA_HORARIA=America/Santiago`. Ya las lee `config.py`.

**Permisos mínimos**

| Acción | Recurso |
|---|---|
| `dynamodb:GetItem`, `Query`, `BatchGetItem` | Las 5 tablas compartidas y su `/index/*` |
| `s3:PutObject` | Solo `arn:aws:s3:::${BucketCapturas}/capturas/*/meta.json` y `.../capturas/*/texto.json` |
| `apigateway:GET` | Solo `arn:aws:apigateway:${AWS::Region}::/apikeys/${IdClaveTranscriptor}` |
| DynamoDBCrudPolicy | Las dos tablas propias |

**Hosting (tarea 8)**
- BucketWeb privado: PublicAccessBlock completo, BucketOwnerEnforced y SSE-S3; su política permite
  `s3:GetObject` a `cloudfront.amazonaws.com` con `AWS:SourceArn` de la distribución, y niega todo
  lo que no sea HTTPS.
- OacWeb (`AWS::CloudFront::OriginAccessControl`).
- FuncionSpa: CloudFront Function `cloudfront-js-2.0` en `viewer-request`. Si el último segmento de
  la URI no tiene punto, la reescribe a `index.html`.
- Distribucion:
  - Orígenes: S3 con OAC, y la API `${ApiHttp}.execute-api.${AWS::Region}.amazonaws.com` (solo
    HTTPS, TLSv1.2).
  - Comportamiento por defecto, hacia S3: `redirect-to-https`, CachingOptimized, Compress y la
    función SPA.
  - `/api/*`, hacia la API: todos los métodos, CachingDisabled y AllViewerExceptHostHeader.
  - General: `DefaultRootObject index.html`, PriceClass_100, http2and3 e IPv6.
  - **Sin respuestas de error personalizadas**, porque convertirían los 404 de la API en index.html.
  - IDs de las políticas administradas: CachingOptimized `658327ea-f89d-4fab-a63d-7e88639e58f6`;
    CachingDisabled `4135ea2d-6df8-44a3-9df3-4b5a84be39ad`; AllViewerExceptHostHeader
    `b689b0a8-53d0-40ab-baf2-68738e2966ac`.
- Outputs: `UrlApp`, `UrlApiDirecta`, `BucketWeb`, `IdDistribucion`.

## 5. Seguridad y costos (lo que citan las tareas 5 y 7)

- No hay control de acceso; es un riesgo aceptado por Lucas.
- Mitigaciones: los límites de la HTTP API; el plan de uso del transcriptor; audio de hasta 4 MiB y
  texto de hasta 5000 caracteres; logs sin contenido de las notas; el tope diario de capturas, con
  un contador atómico: `UpdateItem` con `ADD` y la condición
  `attribute_not_exists(total) OR total < :max`.
- Clave del transcriptor: se obtiene con `get_api_key(apiKey=ID, includeValue=True)` y queda solo en
  memoria; nunca va a logs, respuestas, archivos ni al navegador. Plan B: un secreto en Secrets
  Manager que crea Lucas, sin mostrar su valor.
- Clientes boto3: `connect_timeout` de 3 s, `read_timeout` de 8 s, reintentos `standard`, igual que
  el transcriptor.

## 6. Ajustes ya en disco que mandan sobre el plan

- **Regla 2**: en DynamoDB, los homónimos vienen como "Martina M." y "Martina R.". El generador los
  separa en `nombre: "Martina"` y `apellidoInicial: "M."` (función `separar_nombre` en
  `huellita-formato-mejorado/scripts/generar_datos_e1.py`). El BFF debe hacer lo mismo.
- **Regla 4**: el generador usa como `cita` los `texto_observable` de ese dominio unidos con
  espacios, no el `texto_literal` completo (función `sugerencias_historial`). La **regla 1** usa la
  mediana baja (`mediana_baja`). Para que el modo local y el de AWS coincidan, el BFF debe usar
  ambos criterios. Una prueba útil compara su salida con
  `huellita-formato-mejorado/data/semilla.json`.

## 7. Otras diferencias y notas

- **Contradicción del plan**: la tarea 5 usa `estado_envio = "enviando"`, pero la tabla Capturas solo
  lista `enviada` y `error_envio`. Tratar `enviando` como un tercer valor, transitorio.
- **Datos reales**: SG-A ya tiene 4 capturas del equipo (6 observaciones) sin fila en Capturas.
  Entran por el último punto de la regla 5 y aparecerán como pendientes en Revisar.
- **DECISIÓN ABIERTA** (sugerencia, no regla): en la regla 5, el primer candidato de NO_IDENTIFICADO
  puede no tener nada que ver con el nombre escrito. Ejemplo real: "Agustín" quedó con candidato
  "Martina R." (puntaje 77). Está pendiente confirmar si se usa como `nombreDetectado`.
  Implementación mientras se decide: seguir la regla (primer candidato como `nombreDetectado`), pero
  aislarlo en **una sola función** con el umbral de puntaje como constante con nombre, para que
  cambiar el criterio sea una línea. Dejarlo anotado en el reporte.

## 8. Entorno (crítico: sin esto, los comandos de verificación fallan)

- **SAM CLI no está en el PATH**: usar `C:\Program Files\Amazon\AWSSAMCLI\bin\sam.cmd`.
- **npm no está en el PATH**: está en `c:\dev\hackaton\.worktrees\.herramientas\bin`.
- El perfil `hackaton` usa `aws login` y el boto3 del venv **falla** con él. Antes de correr boto3 o
  SAM: `aws configure export-credentials --profile hackaton --format powershell | Out-String | Invoke-Expression`
  (las credenciales no se muestran en la salida).
- **`cfn-lint` no está disponible** (conflicto de versiones de pydantic con `requirements-dev.txt`).
  Usar `sam validate --lint`. No está probado en este equipo, así que si falla, reportarlo en vez de
  forzar la instalación.
