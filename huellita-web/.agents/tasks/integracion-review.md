# Integración de los carriles 5 a 9 del BFF de Huellita

El paso de integración cerró seis costuras entre carriles que se habían desarrollado en paralelo: escribió `datos/audio.py` (que dos módulos importaban sin que existiera), quitó la sincronización de audio duplicada de `datos/lectura.py`, movió el prefijo `/api` a `rutas/__init__.PREFIJO` para que las rutas se puedan leer de `app.routes` con FastAPI 0.137, reemplazó el cargador de routers con `importlib` por tres imports directos, unificó la firma `router` y declaró la variante con agenda en las pruebas de Fase 1 que leían `CONFIG` del ambiente. Revisé el contrato duro contra el código: cuerpos y orden de `meta.json`/`texto.json`, formato del ULID, los topes de texto y audio, el contador atómico del día, la tabla de traducción del transcriptor, la regla 6 con reloj inyectado, la idempotencia de `PUT /api/decisiones`, el IAM de la plantilla y el aislamiento de la clave de API. Todo eso calza, y las pruebas que lo respaldan afirman sobre comportamiento, no sobre sí mismas.

**Watch for:** el andamiaje de dobles por `find_spec` sigue vivo en `conftest.py` y `test_capturas.py` (confirmado) — es el mismo mecanismo que ya dejó pasar en verde un módulo ausente; el mensaje de `tope_diario` y la descripción de `MaxCapturasDia` le dicen a la tía "en esta sala" cuando el contador es global del día (confirmado); una entrada en frío a `/nino/{id}` sale sin la cabecera `X-Usuaria-Id` y recibe 403 (probable); y la confirmación masiva dispara N `PUT` concurrentes cuyas respuestas se pisan en el caché hasta el próximo sondeo (probable). Ninguno bloquea el flujo de las demos de las tareas 5 a 7.

**Verdict**: APPROVED

## High-level view

La entrega de una captura de texto está en el orden que manda el spec y con los cuerpos exactos: reservar cupo con un `UpdateItem` condicional, fila en `enviando`, `meta.json`, `texto.json`, fila en `enviada`, 201 con la evidencia en `procesando`. El cupo se reserva **antes** de las escrituras, así que un 502 de S3 consume un cupo del día; con un tope de 300 no tiene consecuencia práctica, pero es una asimetría real entre lo que se cobra y lo que se guarda.

El contador diario es global del día, sin partición por sala: `reservar_cupo_del_dia` recibe `sala_id` y lo descarta explícitamente, que es lo que pide SPEC-OFICIAL §2. Lo que no acompaña es la redacción: el mensaje que ve la tía y la descripción del parámetro en la plantilla hablan de un tope "en esta sala", de modo que la tía de SG-B puede quedar bloqueada por lo que gastó SG-A y leer que el límite es suyo.

El audio quedó con una sola ruta de sincronización, la de `datos/audio.py`, y eso cierra un consumo doble del transcriptor en cada sondeo de 5 s. La traducción de errores está completa y verificada en los seis estados (413 y 415 iguales, 429 y 503 a 503, 502 y 504 a 502), repartida en tres capas de pruebas. La concurrencia acotada se prueba de verdad: la prueba afirma el techo de 4 y además que el paralelismo ocurre. El aislamiento de la clave de API se prueba en el peor caso, con una excepción que lleva la clave en su mensaje y con `caplog.text`, que incluye trazas.

`PUT /api/decisiones` saca su idempotencia de leer siempre la sugerencia desde Observaciones en vez de desde la decisión guardada, así que repetir una corrección vuelve a calcular el mismo `original`. Valida la solicitud completa antes de escribir, de modo que un ítem inválido no deja la lista a medias.

El IAM de la plantilla es el del spec al detalle: lectura tabla por tabla con su `index/*`, `s3:PutObject` acotado a `capturas/*/meta.json` y `capturas/*/texto.json`, `apigateway:GET` a una sola clave por su ID. No hay secretos en el código ni en la plantilla; `IdClaveTranscriptor` es el ID y el valor se pide en caliente.

La deuda que queda es de andamiaje de pruebas. `conftest.py` y `test_capturas.py` todavía traen módulos de reemplazo que se instalan solos si el real falta. Hoy no se instala ninguno, así que la suite corre contra el código real, pero el gatillo que ya ocultó una falla de producción sigue armado.

<details>
<summary>Issues (8) — ninguno BLOQUEANTE</summary>

Alcance verificado sin hallazgos bloqueantes: contrato HTTP de SPEC-OFICIAL §1 (las 8 rutas montadas, `archivar` 204, `GET /api/ninos/{id}`, 429/413/404/422), aislamiento de la clave del transcriptor, IAM y ausencia de secretos en `template.yaml`, forma `RespuestaError` en todos los caminos, costuras entre carriles (imports resueltos, 3 routers registrados, sin alias duplicados) y la tabla Capturas con su índice disperso.

1. **MENOR — Andamiaje de dobles por `find_spec`** (`tests/conftest.py:115-118`, `tests/test_capturas.py:80,221-230`): instala reemplazos de `errores`, `tiempo`, `dynamo`, `auth`, `datos.audio` y `datos.decisiones` si el módulo real falta. Hoy no se instala ninguno, pero es el mismo gatillo que ya dejó la suite verde sin `datos/audio.py`. Borrar el andamiaje para que un import ausente falle fuerte.
2. **MENOR — El tope diario se anuncia como "de esta sala"** (`src/huellita_api/errores.py:51`, `template.yaml:68`): el contador es `CONTADOR#AAAA-MM-DD` global del día, pero el mensaje a la tía y la descripción de `MaxCapturasDia` dicen "en esta sala". Cambiar ambos textos a "de hoy".
3. **MENOR — Entrada en frío a `/nino/{id}` sin cabecera** (`huellita-formato-mejorado/src/app/hooks.ts:317`, `src/services/http.ts:303`): `useFicha` llama `datos.nino(id)` antes de resolver `contexto()`, y `pedir` omite `X-Usuaria-Id` mientras la sesión esté vacía; el BFF responde 403 "Esta sala no es tuya". Resolver `contexto()` antes de la primera llamada con cabecera, o redirigir a la entrada sin sesión.
4. **MENOR — La confirmación masiva se pisa en el caché** (`huellita-formato-mejorado/src/pages/Revisar.tsx:107`): un `PUT` por nota con `Promise.all`, y cada respuesta reemplaza el arreglo completo de `sugerencias`; una respuesta rezagada puede devolver a pendiente lo ya confirmado hasta el próximo sondeo. Mandar un solo `PUT` con los N ítems, o fusionar en vez de reemplazar.
5. **MENOR — Plomería entre carriles sin retirar** (`src/huellita_api/rutas/lectura.py:101` vs `src/huellita_api/datos/lectura.py:45`): `_buscar_nino` busca `leer_nino` con `getattr` y la trata como opcional, pero `leer_nino` está anotada `-> Nino` y lanza `no_encontrado`, así que la rama de respaldo no se alcanza en producción; `datos/audio.py:78` recibe un `reloj` que descarta con `del`. Alinear firmas e importar directo.
6. **MENOR — Nada fija el "intenta de nuevo" del 503** (`src/huellita_api/errores.py:52`): el spec pide ese texto para 429 y 503 del transcriptor; está en el mensaje pero ninguna prueba lo afirma. Agregar la aserción del mensaje junto a la del código.
7. **MENOR — El cupo del día se gasta antes de escribir en S3** (`src/huellita_api/rutas/capturas.py:100`): una captura que termina en 502 con `error_envio` igual consumió cupo. Reservar después de la entrega, o devolverlo en el camino de falla.
8. **MENOR — `publicar_front.ps1` deja variables en la sesión** (`scripts/publicar_front.ps1:64`): fija `$env:VITE_DATOS` y `$env:VITE_AGENDA` y no las restaura en el `finally`; un build posterior en la misma consola hereda el modo `http`. Guardar y restaurar los valores previos.

</details>

<details>
<summary>Details</summary>

### Orden de entrega y los dos cuerpos de S3

`rutas/capturas._entregar` encierra las dos escrituras en el mismo bloque y cualquier falla deja la fila en `error_envio` antes de levantar 502, así que no hay un camino donde `texto.json` exista sin su `meta.json`. Los cuerpos salen de funciones puras en `s3.py`, lo que permite probarlos sin red:

```python
def cuerpo_meta(autor_id, sala_id, fecha):
    return {"id_educadora": autor_id, "sala_grupo": sala_id, "fecha_observacion": fecha}

def cuerpo_texto(id_captura, texto, fuente="manual"):
    return {"id_captura": id_captura, "fuente": fuente, "partes": [{"texto": texto}]}
```

La prueba de ruta compara `entorno.s3.claves` como lista ordenada contra `[meta.json, texto.json]` y los dos cuerpos por igualdad completa de diccionario, no por subconjunto: un campo de más rompería. La fecha se afirma dos veces, una contra un reloj fijo y otra contra `datetime.now(ZoneInfo("America/Santiago"))`, que es lo que pide la regla de la fecha de Chile.

Para audio, `_entregar` escribe `meta.json` y llama al transcriptor; el `texto.json` llega después, cuando `datos/audio._aplicar` recibe `completado`, y `texto_entregado` evita escribirlo dos veces. El orden se mantiene porque `meta.json` ya se escribió en el POST.

El cupo, en cambio, se reserva antes de todo esto:

```python
capturas.reservar_cupo_del_dia(CFG, entrada.salaId, dia)
id_captura = ulid.nuevo_id_captura()
capturas.crear_fila(...)
```

Una captura que muere en 502 por S3 ya gastó su unidad del día y no hay devolución. Con 300 por día es ruido, pero la cuenta que ve `contar_del_dia` no es la cantidad de notas guardadas.

### El contador atómico, y lo que se le dice a la tía

La reserva es un solo `UpdateItem` con `ADD` y la condición del spec, y la ausencia de atributos devuelve `None` en vez de lanzar:

```python
item = dynamo.actualizar(
    cfg.tabla_capturas, _clave(id_contador(dia)), "ADD total :uno",
    {":uno": {"N": "1"}, ":max": {"N": str(cfg.max_capturas_dia)}},
    condicion="attribute_not_exists(total) OR total < :max",
)
if item is None:
    raise errores.error("tope_diario")
```

`reservar_cupo_del_dia` y `contar_del_dia` reciben `sala_id` y lo descartan con un `del` comentado, que es la lectura correcta de SPEC-OFICIAL §2: el ítem `CONTADOR#AAAA-MM-DD` no lleva `sala_key` justamente para quedar fuera del índice `porSala`. Lo que no se actualizó es la redacción alrededor. El mensaje al usuario afirma un alcance por sala, y la descripción del parámetro en la plantilla lo repite; con dos salas compartiendo un tope, la tía de SG-B puede verse bloqueada por SG-A y leer que el límite es de su sala. Es texto, pero es el único texto que la tía ve cuando el flujo se corta.

La prueba del 429 no es tautológica: el `Almacen` en memoria evalúa la condición de verdad, a través de una tabla explícita de las dos únicas condiciones que escribe el módulo.

```python
CONDICIONES = {
    "attribute_not_exists(total) OR total < :max": lambda item, valores: (
        "total" not in item or int(item["total"]["N"]) < int(valores[":max"]["N"])
    ),
    ...
}
```

Con `MAX_CAPTURAS_DIA="2"` la prueba afirma `[201, 201]` y después 429, y además que quedaron exactamente 4 objetos en S3 (dos por captura aceptada), lo que descarta que la tercera haya escrito algo antes de rebotar. El `KeyError` que produciría una condición nueva es un buen seguro contra la deriva silenciosa.

### Traducción del transcriptor y aislamiento de la clave

La tabla del spec se verifica en tres niveles y ninguno repite el trabajo del otro. `test_transcriptor.py` parametriza los seis estados HTTP contra el código estable; `test_audio.py` parametriza los cuatro códigos estables contra el HTTP del BFF y afirma que la fila queda en `error_envio` antes de levantar; `test_rutas_capturas.py` cierra el extremo HTTP de la ruta. La composición cubre 413 y 415 iguales, 429 y 503 a 503, y 502 y 504 a 502. Lo único que ninguna prueba fija es el texto "intenta de nuevo" que el spec pide explícitamente para el 503, aunque esté en `errores.MENSAJES`.

El aislamiento de la clave se prueba en el peor caso imaginable, no en el feliz:

```python
def consultar(_cfg, _id_trabajo: str) -> dict:
    raise RuntimeError(f"403 Forbidden con x-api-key={CLAVE}")
...
assert CLAVE not in caplog.text
assert "RuntimeError" in caplog.text, "el tipo de la falla sí queda, para poder depurar"
```

Afirmar sobre `caplog.text` (que arrastra las trazas) y además exigir que el tipo de la excepción sí sobreviva es lo que convierte esto en una prueba útil: cualquier `exc_info` que filtre el mensaje la rompe. `transcriptor.py` colabora logueando solo ids, estados y tamaños, y `ErrorTranscriptor` nunca lleva más que un código. El `@functools.cache` sobre `valor_clave_api` funciona porque `Config` es un dataclass congelado con `salas` como tupla; si alguien cambiara ese campo a lista, la lectura de la clave empezaría a fallar con `TypeError: unhashable`.

La concurrencia acotada se mide con un contador bajo candado:

```python
assert estado["tope"] <= audio.MAX_CONSULTAS_PARALELAS == 4
assert estado["tope"] > 1, "las consultas tienen que ir en paralelo"
```

La segunda aserción es la que importa: sin ella, una implementación secuencial pasaría igual.

### Una sola sincronización de audio

La duplicación que resolvió la integración era real y de costo: `datos/lectura._sincronizar_audios` llamaba a `transcriptor.consultar` dentro de `leer_registros`, y `rutas/lectura.py` llamaba además a `datos.audio.sincronizar`. Con el módulo en disco, cada sondeo de 5 s habría consultado el transcriptor dos veces por nota. Ahora `datos/lectura.py` solo lee DynamoDB y la sincronización vive donde el contrato la pone.

```
GET /api/salas/{id}/registros
  └─ rutas/lectura._sincronizar_audio ─> datos/audio.sincronizar
       ├─ _pendientes        (Capturas: formato=audio, id_trabajo, sin estado_final)
       ├─ _consultar_y_guardar  (ThreadPool de 4 -> transcriptor.consultar)
       └─ _aplicar          fallido   -> marcar_final(error)
                            completado -> guardar_texto + texto.json + texto_entregado
  └─ datos/lectura.leer_registros  (solo DynamoDB)
```

El efecto lateral que trajo el cambio es a favor: aparece el reintento de `texto.json` vía `texto_entregado`, un atributo que `datos/capturas.marcar_envio` ya soportaba sin que nadie lo usara, y el estado final queda en manos de Registros en vez de escribirse a mano. `sincronizar` atrapa todo y solo registra el tipo de la falla, así que una caída del transcriptor no voltea la pantalla.

`rutas/decisiones.py` llama `lectura.leer_registros` directo, sin sincronizar, que es lo correcto: la respuesta del `PUT` no tiene por qué sondear el transcriptor.

### Idempotencia de las decisiones

La propiedad sale de dónde se lee la referencia, no de una condición de escritura: `_planificar` toma la sugerencia de **Observaciones** (`datos_decisiones.leer_sugerencia`), nunca de la decisión guardada. Repetir una corrección vuelve a comparar contra los valores de la IA y vuelve a calcular el mismo `original`; `guardar` es un `PutItem` que pisa y `borrar` un `DeleteItem` que no se queja de lo ausente. Las cinco transiciones están en `decidir` y cada una tiene su prueba, incluida la que convierte en `aceptada` una corrección cuyos valores igualan a los de la IA.

La validación completa ocurre antes de cualquier escritura: `planes = [_planificar(...) for item in entrada.items]` se materializa entero y recién después se recorre escribiendo, de modo que un niño de otra sala en el ítem 7 no deja los seis primeros guardados. Hay una prueba que lo fija (`test_no_escribe_nada_si_un_item_de_la_lista_falla`).

`_sugerencias_de_la_sala` vuelve a aplicar lo recién decidido sobre lo leído en vez de confiar en que el `Query` ya lo vea, lo que es la decisión correcta contra la consistencia eventual de DynamoDB. Esa misma mitigación es la que no existe en el frontend cuando se disparan varios `PUT` a la vez: cada respuesta reemplaza el arreglo completo de `sugerencias` y solo reaplica *sus* planes, así que una respuesta rezagada de la confirmación masiva puede devolver a pendiente lo que otra llamada ya confirmó. Se corrige en el siguiente sondeo, pero entre medio la pantalla contradice lo que la tía acaba de hacer.

### Cabecera de usuaria y entrada en frío

`DataServiceHttp.pedir` agrega `X-Usuaria-Id` solo si hay `usuariaId` en la sesión local:

```ts
if (this.sesionLocal.usuariaId) cabeceras[CABECERA_USUARIA] = this.sesionLocal.usuariaId;
```

La sesión se puebla en `asegurarSesion`, que corre dentro del `then` de `contexto()`. Las pantallas que pasan por `sesion()` o `salaActual()` resuelven el contexto primero y quedan bien. `useFicha` no: su primera línea efectiva es `await datos.nino(ninoId)`. Con `localStorage` vacío —primera visita, o la PWA restaurando esa ruta— la llamada sale sin cabecera y `auth.usuaria_o_error(None)` responde 403 `sin_acceso`, cuyo mensaje ("Esta sala no es tuya. Elige la tuya y vuelve a intentar") no describe lo que pasó. `FuncionSpa` reescribe cualquier ruta sin punto a `index.html`, así que `/nino/NIN-0003` es una entrada válida y alcanzable.

Vale notar que el 403 por cabecera ausente no está en la tabla de errores de SPEC-OFICIAL §1 para ninguna ruta; es una decisión del código, consistente con el alcance por sala y probada, pero no una exigencia del spec.

### Plantilla, permisos y lo que no se pudo verificar

Los permisos son exactamente los de SPEC-OFICIAL §4: lectura (`GetItem`, `Query`, `BatchGetItem`) enumerada tabla por tabla con su `index/*` y sin ningún verbo de escritura sobre el dataset ajeno; `DynamoDBCrudPolicy` solo sobre las dos tablas propias; `s3:PutObject` restringido a los dos objetos que el BFF escribe, sin `GetObject`, `DeleteObject` ni `ListBucket`; y `apigateway:GET` sobre un único ARN de clave. No hay secretos en la plantilla ni en el código: `IdClaveTranscriptor` es el ID y el valor se resuelve en caliente y vive en memoria.

El índice `porSala` es deliberadamente disperso para que el ítem contador no aparezca en las consultas de sala, y tanto `datos/capturas.leer_de_sala` como `datos/lectura._filas_propias` filtran además por `creada_en`, lo que deja el comportamiento correcto incluso si alguien le pusiera `sala_key` al contador.

La política del bucket y la distribución usan el patrón OAC sin ciclo (`Distribucion` depende de `BucketWeb`; `PoliticaBucketWeb` depende de los dos), la función SPA está asociada solo al comportamiento por defecto, y no hay `CustomErrorResponses`, que es lo que mantiene los 404 de la API como JSON en vez de convertirlos en `index.html`.

Lo que queda sin verificar, y es correcto que quede así dado que desplegar está prohibido: sin credenciales no se pudo confirmar que las cinco tablas compartidas y el ID de la clave del transcriptor existan en la cuenta, ni correr el `curl` de la tarea 8 contra una URL publicada. El `/api/contexto` que respondió 500 en el humo local es exactamente eso (`NoCredentialsError`), y lo relevante es que conservó la forma `RespuestaError` sin filtrar el nombre de la tabla ni la traza.

### Andamiaje de pruebas que sobrevivió

El hallazgo que abrió la integración fue que `datos/audio.py` no existía y la suite pasaba porque las pruebas inyectaban un módulo falso en `sys.modules`. El mecanismo que lo permitió sigue en pie en dos archivos. En `conftest.py`:

```python
if _falta("huellita_api.auth"):
    _registrar("huellita_api.auth", _relleno_auth())
if _falta("huellita_api.datos.decisiones"):
    _registrar("huellita_api.datos.decisiones", _relleno_decisiones())
```

Y en `test_capturas.py`, unas 120 líneas de `_doble_errores`, `_doble_tiempo`, `_doble_dynamo`, `_doble_auth` y `_doble_audio`, todas con la misma guarda `find_spec`. Verifiqué que los cinco módulos reales están en disco, así que hoy ningún doble se instala y la suite corre contra el código real: `instalar_dobles_de_rutas()` es un no-op. Pero el gatillo sigue armado, y lo que dispara no es un fallo ruidoso sino una suite verde sobre una implementación de mentira. Mientras el andamiaje exista, el verde de pytest no distingue "el código funciona" de "el código no está".

Hay una diferencia de criterio entre los dos dobles de DynamoDB que conviene no perder: el `Almacen` de `test_capturas.py` implementa `ADD` y evalúa las condiciones, mientras el `ClienteFalso` de `conftest.py` solo entiende `SET` e ignora `ConditionExpression`. Está bien, porque cada uno sirve a pruebas distintas, pero significa que nada que use `ClienteFalso` puede afirmar sobre atomicidad.

### Pruebas del frontend

Los 7 casos que fallaban con `VITE_AGENDA=false` se arreglaron declarando la variante con `ProveedorOpciones agenda` en vez de depender del ambiente, el mismo patrón que ya usaba `version-aws.test.tsx`. Es la corrección correcta: la prueba ahora dice qué versión monta.

Revisé los cambios de aserción de `demo.test.tsx` y `adaptable.test.tsx` buscando debilitamiento y no lo encontré: son re-apuntes al dataset regenerado (`EDU-0001` por `USR-ANA`, `NINO-00008`, 13 filas en vez de 18, "Sala A" por "Medio Menor A", `Socioemocional` por "Convivencia y Ciudadanía", nivel 8 sobre original 9 por 5 sobre 4). Las aserciones siguen comprobando lo mismo con los valores nuevos; el guion de la demo conserva sus seis pasos.

Las dos pruebas que pedía el spec están y afirman lo que deben: `captura.test.ts` cubre que `capturar()` en modo servidor no llama a `ia.procesar` y que en modo local sí sigue procesando en el dispositivo (el par importa, sin la segunda la primera podría pasar con una IA rota), y `http.test.ts` cubre el sondeo de 5 s con temporizadores simulados en dos direcciones: que se detiene cuando no queda nada procesando y que una captura nueva lo vuelve a encender.

</details>

<details>
<summary>Mapa de archivos</summary>

Backend nuevo (`huellita-web/`, sin seguimiento en git):

- `src/huellita_api/app.py` — montaje plano de los tres routers, cuatro manejadores de error con forma `RespuestaError`, handler de Mangum.
- `src/huellita_api/rutas/__init__.py` — `PREFIJO = "/api"`, movido desde `app.py`.
- `src/huellita_api/rutas/capturas.py` — `POST /api/capturas` y `archivar`; orden de entrega y traducción a 502.
- `src/huellita_api/rutas/decisiones.py` — `PUT /api/decisiones`: validar todo, después escribir.
- `src/huellita_api/rutas/lectura.py` — salud, contexto, niños y registros; sincroniza audio antes de leer.
- `src/huellita_api/datos/audio.py` — escrito en la integración: `decodificar`, `enviar`, `sincronizar` con pool de 4.
- `src/huellita_api/datos/lectura.py` — sin la sincronización de audio duplicada.
- `src/huellita_api/datos/capturas.py` — contador atómico del día, filas y archivado.
- `src/huellita_api/datos/decisiones.py` — regla 7 pura (`decidir`, `aplicar`) más la tabla Decisiones.
- `src/huellita_api/transcriptor.py` — cliente con la clave solo en memoria y errores ya traducidos.
- `src/huellita_api/{s3,ulid,errores,modelos,config,tiempo,auth,mapeo}.py` — cuerpos exactos, ULID de Crockford, tabla de códigos, modelos `extra=forbid`, regla 6.
- `template.yaml` — dos tablas propias, HTTP API con `RouteSettings`, IAM de mínimo privilegio, hosting CloudFront.
- `scripts/{smoke.py,publicar_front.ps1,volcar_muestras.py}` — humo de punta a punta, publicación en dos pasadas de caché.
- `tests/` — 353 casos; `test_audio.py` nuevo con 27.

Frontend (`huellita-formato-mejorado/`, 35 archivos modificados y 9 nuevos):

- `src/services/http.ts` — nuevo: `DataServiceHttp`, base64 por bloques, sondeo de 5 s, actualización optimista con vuelta atrás.
- `src/services/captura.ts` — corte temprano cuando `procesaEnServidor`.
- `src/services/datos.ts` — `procesaEnServidor` y `admiteFoto` en la interfaz.
- `src/app/{config.ts,opciones.tsx}` — nuevos: variantes de compilación declarables.
- `src/pages/Revisar.tsx` — manejo de falla en las cinco acciones.
- `data/semilla.json` — regenerada con el dataset real; de ahí vienen los re-apuntes de las pruebas.
- `src/app/{App,adaptable,demo}.test.tsx` — declaran su variante con `ProveedorOpciones`.

Diff completo: `git diff` en `c:\dev\hackaton\.worktrees\huellita-aws` para el frontend; `huellita-web/` está sin seguimiento y se revisa leyendo los archivos.

</details>
