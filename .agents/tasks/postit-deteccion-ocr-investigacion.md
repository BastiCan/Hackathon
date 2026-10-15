# Detección y lectura de post-its manuscritos: investigación y recomendación (AWS primero)

Fecha de la investigación: octubre de 2026. Investigación de solo lectura: no se llamó a ningún servicio de pago ni se envió información del proyecto a terceros. Solo se leyó documentación y páginas de precios, y se consultaron APIs públicas de listas de precios y de versiones de paquetes.

**Leyenda de evidencia.** `[V]` verificado en la fuente citada. `[L]` verificado por mí ejecutando código en esta máquina (Windows, Python 3.13.14), sin llamar a ningún servicio en la nube. `[I]` inferencia mía. `[NV]` no pude verificarlo.

**Requisitos vigentes aplicados (actualización del usuario).** Ya no se trabaja con asignación automática a niños/as: el servicio solo transcribe el texto de cada post-it y la educadora asigna cada post-it a un niño/a a mano en la app. Se prioriza AWS (Amazon Bedrock con la Converse API, luego Amazon Textract como comparación). Google y Azure quedan como comparación breve. Despliegue previsto: AWS Lambda + API Gateway REST API con AWS SAM y Mangum. Se mantienen los requisitos previos: manuscrito en español de Chile, varios post-its por foto, demo en la nube, permitido enviar la imagen a un servicio externo, sin fotos reales (se asume texto oscuro sobre amarillo o verde).

---

## 1. Resumen ejecutivo

1. **Primera opción:** Amazon Bedrock, Converse API, modelo **Claude Haiku 5.5** (`us.anthropic.claude-haiku-5-5`). Una sola llamada por foto detecta cada post-it (caja) y transcribe su texto manuscrito. Precio en el perfil US: 0,11 USD / 0,55 USD por millón de tokens de entrada / salida `[V]`; costo estimado por foto menor a 0,001 USD `[I]`.
2. **Respaldo dentro de AWS (cambio de una variable de entorno):** Claude Sonnet 5.5 si se necesita más precisión (unas 20 veces más caro `[V]`), o **Amazon Nova 2 Lite** (modelo de Amazon, cajas 0–1000 documentadas `[V]`, el más seguro si los créditos del hackathon no cubren modelos de terceros `[NV]`).
3. **Textract no sirve para este caso:** la documentación vigente dice que el reconocimiento de manuscrito solo funciona en inglés `[V]`. El anuncio que usted encontró (2020/2021) sigue siendo lo último; las páginas actuales de límites y de preguntas frecuentes lo confirman. Úselo solo como comparación de 5 minutos en la consola.
4. **Despliegue:** REST API + Lambda (python3.13) + Mangum es correcto y no hay razón fuerte para cambiarlo. Cuatro ajustes: endpoint **REGIONAL**, cuerpo máximo de **3,5 MB** ya decodificado (por el límite de 6 MB de Lambda y de 3,75 MB por imagen de Converse), cabeceras **CORS devueltas por la propia función**, y recordar que la **API key identifica y limita, no autentica**.
5. **Arquitectura:** una llamada de "detectar y leer" a la foto completa (más simple y barata) en vez de detectar → recortar → OCR por recorte. El recorte con OpenCV queda como mejora de fase 2 (privacidad y localización más precisa).
6. **Verificado localmente `[L]`:** la API completa (FastAPI + Mangum con un evento de API Gateway REST simulado, Bedrock simulado con `botocore.Stubber`, que valida los parámetros contra el modelo de servicio real), la plantilla SAM (`cfn-lint` sin errores), el empaquetado de dependencias Linux desde Windows (58,8 MB), el generador sintético y el evaluador.
7. **No verificado `[NV]`:** precisión real de Haiku 5.5 y Nova 2 Lite con manuscrito en español, latencia real, cuotas de Bedrock de su cuenta y si los créditos del hackathon cubren Claude. Esto se resuelve con el plan de pruebas sintético (sección 7) y una prueba de humo de 10 minutos.

---

## 2. Detección de varios post-its en una foto

| Opción | Cómo funciona | Evidencia | Fortalezas | Debilidades | Veredicto |
|---|---|---|---|---|---|
| **A. Modelo multimodal en Bedrock devuelve las cajas** (Claude Haiku 5.5, Sonnet 5.5, Nova 2 Lite) | Se le pide, en la misma llamada que la lectura, una caja y un texto por post-it | Nova: cajas en escala [0, 1000) documentadas `[V]`, ejemplo oficial con Nova 2 Lite y formato `[x_min, y_min, x_max, y_max]` `[V]`. Claude: devuelve coordenadas en píxeles de la imagen que ve, pero Anthropic advierte que son aproximadas y que hay que verificarlas `[V]` | No necesita umbrales ni fotos de calibración; tolera fondos amarillos o verdes, sombras y reflejos mejor que un umbral de color `[I]`; una sola llamada | Cajas aproximadas; puede omitir o inventar una nota; sin polígono ni rotación | **Primera opción** |
| **B. OpenCV clásico** (umbral HSV + contornos + `minAreaRect` + `warpPerspective`) | Local, sin costo | Experimento propio con unas 600 notas sintéticas `[L]` (abajo) | Gratis, determinista, polígono y rotación exactos, permite enviar solo el recorte | Hay que calibrar con fotos reales (no existen); frágil con fondos amarillos/crema; notas pegadas o superpuestas necesitan heurísticas | **Respaldo / fase 2** (en Lambda sumaría unos 90 MB y arranque más lento `[I]`) |
| **C. Textract / Rekognition** | OCR de texto en escena | Textract devuelve líneas y palabras con caja y confianza, pero no detecta "post-its" como objeto `[V]`. Rekognition `DetectText`: hasta 100 palabras por imagen `[V]` | Cajas por palabra | Habría que agrupar palabras en notas por cuenta propia; manuscrito solo en inglés (Textract) | Descartada para detectar |
| **D. Detectores genéricos en la nube** (Google Vision Object Localization, Azure Object Detection) | Etiquetas de objetos generales | Google cobra 2,25 USD por 1.000 imágenes tras 1.000 gratis `[V]`; no encontré un nombre de clase "post-it" `[NV]` | Cajas normalizadas | Probablemente no reconocen la clase "post-it" `[I]` | Descartada |
| **E. Roboflow / SAM / modelos entrenados** | Modelo especializado | Hay conjuntos públicos de "sticky notes" en Roboflow Universe; la licencia cambia por conjunto `[V]` | Potencialmente muy preciso | Requiere entrenar, desplegar (SageMaker o contenedor) y calibrar; excede las horas disponibles | Descartada por tiempo |

### Experimento local de la opción B `[L]`
Generé 12 fotos sintéticas de 1600×1200 por condición y fondo (60 notas cada una; unas 600 notas en total entre todas las corridas): notas amarillas y verdes con letra tipo manuscrito (fuente Ink Free de Windows), rotación ±25°, sombras, gradiente de luz con tinte cálido, ruido, desenfoque y perspectiva suave. Detector HSV + contornos (código en el anexo C).

| Condición | Recall con IoU ≥ 0,5 | Recall con IoU ≥ 0,75 | Falsos positivos |
|---|---|---|---|
| Notas separadas sobre madera, blanco o crema | 1,00 | 1,00 | 0 |
| Dos notas pegadas lado a lado (heurística de partir por la mitad) | 1,00 | 1,00 | 0 (las 24 notas partidas quedan marcadas "revisar") |
| Tres notas en contacto (racimo) | 0,75–0,83 | 0,75–0,80 | 3–5 (marcadas "revisar") |
| Fondo crema con umbral de saturación laxo (S ≥ 70) | 0,00 | 0,00 | 12: el fondo completo se detecta como nota |

Lecciones, todas `[L]`: (1) la saturación mínima del amarillo decide si funciona; con S ≥ 110 los fondos crema o madera no se confunden. (2) Las notas pegadas o superpuestas son el punto débil clásico: la distancia + watershed (OpenCV lo documenta `[V]`) no separa dos cuadrados que comparten un borde completo. (3) En OpenCV 4.13 `minAreaRect` devolvió ángulos negativos; no conviene depender del ángulo, sino usar `cv2.boxPoints`. (4) Mis fotos sintéticas son fáciles; en fotos reales con celular el resultado será peor. Solo cuesta 0,35 s por imagen en esta máquina, incluida la generación de la escena.

### Cómo se manejan los casos difíciles
- **Notas que se tocan o se superponen:** en la opción A basta con pedir "una entrada por nota aunque se toquen", y eliminar duplicados con una supresión simple (dos cajas con IoU > 0,6 se funden). En la opción B, las notas que no encajan en un rectángulo (relleno < 0,8) o con proporción distinta de 1 (> 1,5) se marcan "revisar" en vez de adivinar.
- **Reflejos y sombras:** el modelo los ignora mejor que un umbral `[I]`; en OpenCV, el `CLOSE` morfológico (17×17) rellena brillos y letras y el `OPEN` (9×9) quita manchas.
- **Fondos amarillos/verdes que confunden el umbral:** subir S mínima (110 para amarillo), exigir área mínima (0,4 % de la imagen) y proporción cercana a 1; con modelo multimodal el problema desaparece en gran parte `[I]`.
- **Sin ningún post-it o texto ilegible:** el servicio responde 200 con `postits: []` y `advertencias: ["no_se_detecto_postit"]`; las notas dudosas se marcan `legible: false` (sección 4).

**Recomendación:** primero A (Haiku 5.5). Si en el plan de pruebas el recall con IoU ≥ 0,5 queda bajo 0,90, o si prefiere enviar solo recortes, pase a B + lectura por recorte (fase 2).

---

## 3. Lectura (OCR) de manuscrito en español: comparación

Precios en USD. Costos por foto = mi estimación `[I]` para una foto de 2048×1365 px con 5 notas, unos 400 tokens de salida y la fórmula de tokens de imagen de Anthropic (⌈ancho/28⌉×⌈alto/28⌉ ≈ 3.600 tokens `[V]`; se supone igual en Bedrock `[I]`).

| Servicio | Manuscrito y español | Cajas | Precio | Capa gratuita | Credenciales rápidas | Límites | SDK Python / base64 | Costo por foto `[I]` |
|---|---|---|---|---|---|---|---|---|
| **Bedrock · Claude Haiku 5.5** | Es multimodal; no encontré una prueba en español manuscrito `[NV]`. Pruebas generales muestran que los modelos multimodales leen manuscrito mejor que el OCR clásico, pero fueron en inglés y con otros modelos `[V]` | Sí, aproximadas (píxeles) | Perfil global 0,10 / 0,50 por M tokens; perfil US 0,11 / 0,55 `[V lista de precios de AWS]` | No hay `[I]` (pago por uso; posibles créditos de cuenta nueva `[V]`, aplicación a Marketplace `[NV]`) | Consola de Bedrock → Playground → modelo → formulario de primer uso de Anthropic; clave de API de Bedrock o rol IAM `[V]` | Imagen ≤ 3,75 MB, ≤ 8000 px, ≤ 20 imágenes por mensaje `[V]`; contexto 1 M tokens; sin salida estructurada garantizada en la tarjeta del modelo `[V, lectura ambigua]` | `boto3` `converse`; bytes de imagen (no base64: el SDK lo codifica) | ≈ 0,0007 |
| **Bedrock · Claude Sonnet 5.5** | Igual que arriba, más preciso `[I]` | Sí, aproximadas | Global 2,00 / 10,00; US 2,20 / 11,00 `[V]` | No | Igual | Igual | Igual | ≈ 0,013 |
| **Bedrock · Nova 2 Lite** | Documentado para documentos, imágenes y detección de objetos; español manuscrito `[NV]` | Sí, escala 0–1000 `[V]` | Global 0,30 / 2,50; regional 0,33 / 2,75 `[V]` | No | Igual (sin Marketplace) | Contexto 1 M; fecha de retiro "no antes del 2 de diciembre de 2026" `[V]` | Igual | ≈ 0,002 |
| **Amazon Textract `DetectDocumentText`** | Español impreso sí; **manuscrito solo en inglés** `[V]` | Sí, por línea y palabra, con confianza 0–100 `[V]` | 0,0015 por página (primer millón; ejemplo en Oregón) `[V]` | 3 meses con 1.000 páginas/mes de `DetectDocumentText` `[V]` | Rol IAM | Síncrono: JPEG/PNG ≤ 10 MB; texto ≥ 15 px de alto; 25 TPS en us-east-1 `[V]` | `boto3` `detect_document_text(Document={"Bytes":...})` | 0,0015 (si funcionara) |
| **Amazon Rekognition `DetectText`** | Hasta 100 palabras por imagen `[V]`; manuscrito no documentado `[I]` | Sí | 0,001 por imagen (primer millón) `[V]` | 1.000 imágenes/mes durante 12 meses `[V]` | Rol IAM | — | `boto3` | 0,001 |
| *Comparación breve:* **Google Cloud Vision `DOCUMENT_TEXT_DETECTION`** | Español en la lista de idiomas con soporte prioritario `[V]`; manuscrito se obtiene con esta misma función `[V]`; calidad en español `[NV]` | Sí (página, bloque, párrafo, palabra) | 1,50 por 1.000 tras 1.000 gratis al mes `[V]` | 1.000 unidades/mes `[V]` | Proyecto con facturación habilitada `[V]` + clave de API | JSON ≤ 10 MB, imagen ≤ 20 MB, 16 imágenes por solicitud, 1.800 solicitudes/min `[V]` | REST con clave o `google-cloud-vision` | 0,0015 por imagen (por recorte si se recorta) |
| *Comparación breve:* **Azure Vision Read / Document Intelligence Read** | La lista de idiomas incluye español para manuscrito `[V]`, pero la nota de transparencia dice que el manuscrito solo está soportado en inglés `[V]` (fuentes en conflicto) | Sí, con polígono y confianza | 1,50 por 1.000 (Image Analysis grupo 2 y Read de Document Intelligence; API pública de precios de Azure) `[V]` | Vision F0: 5.000 transacciones/mes, 20/min; Document Intelligence F0: 500 páginas/mes `[V]` | Recurso en el portal de Azure | — | SDK `azure-ai-*` | 0,0015 |

**Calidad esperada (para no confiar a ciegas):** un blog de un proveedor de OCR de manuscrito reporta 8–23 % de error por palabra en las APIs de OCR en la nube con manuscrito, y un benchmark independiente en inglés puso a un modelo multimodal de Google en primer lugar con 100 % en letra cursiva, frente a Azure, Google Vision y Textract más abajo `[V]`. Ninguno de los dos usa Haiku 5.5 ni Nova 2 Lite ni español. Por eso la decisión final debe salir del plan de pruebas (sección 7).

**Recomendación:** primera opción Claude Haiku 5.5 en Bedrock; respaldo Claude Sonnet 5.5 (precisión) o Nova 2 Lite (créditos y costo). Textract queda como comparación porque no soporta manuscrito en español.

### Detalles específicos de Bedrock que importan al implementar
- **Perfil de inferencia:** el identificador `us.anthropic.claude-haiku-5-5` enruta solo dentro de EE. UU. (us-east-1, us-east-2, us-west-2); `global.…` enruta a cualquier región comercial y es 10 % más barato `[V]`. Recomiendo `us.` por tratarse de datos de menores (sección 6). Ningún perfil queda en Chile: no hay región chilena `[I]`.
- **Salida estructurada:** Converse tiene `outputConfig.textFormat` con esquema JSON, pero la primera vez que se usa un esquema puede tardar hasta unos minutos en compilarse `[V]`, y las tarjetas de Haiku 5.5 y Sonnet 5.5 parecen listar "Structured outputs" como no soportado `[V, lectura ambigua del HTML]`. Por eso el código pide JSON en el prompt, lo extrae con tolerancia (`raw_decode`) y falla con 502 si no puede interpretarlo. Una primera compilación de minutos rompería el límite de 29 s de API Gateway.
- **Razonamiento adaptativo:** Haiku 5.5 piensa por defecto (gasta tokens de salida y tiempo). Se desactiva con `additionalModelRequestFields={"thinking": {"type": "disabled"}}` `[V]`. En Sonnet 5.5 (y Opus 5.5) no es posible desactivarlo según fuentes secundarias `[NV]`: para ese modelo use `BEDROCK_EXTRA='{"output_config": {"effort": "low"}}'` (sintaxis de la guía de AWS para Converse `[V]`, efecto en Sonnet 5.5 `[NV]`).
- **Parámetros de muestreo:** la página de Claude Haiku 5.5 pide omitir `temperature`, `top_p` y `top_k` (hay valores que devuelven 400) `[V]`; el código no los envía.
- **Acceso al modelo:** el acceso es automático con permisos de AWS Marketplace; para Anthropic hay que completar una vez el formulario de primer uso y tener un medio de pago válido. La suscripción tarda hasta 15 minutos `[V]`. Haga la primera invocación desde la consola (Playground) antes de desplegar.
- **Créditos:** los créditos promocionales de AWS suelen aplicar solo a servicios de AWS y los cargos de Marketplace se cobran al medio de pago (respuesta de re:Post de 2024) `[V, fuente secundaria]`; los créditos de AWS Activate sí se aceptan para modelos de terceros en Bedrock `[V]`. Pregunte a los organizadores del hackathon qué créditos tiene y si cubren Claude `[NV]`. Nova es de Amazon y no pasa por Marketplace `[V]`.

---

## 4. Arquitectura recomendada y contrato del endpoint

### Decisión: ¿detectar → recortar → leer, o leer la foto completa?
| Criterio | Foto completa en una llamada (elegida) | Detectar → recortar → leer por recorte |
|---|---|---|
| Costo | 1 llamada por foto | N llamadas (o una con N imágenes) más infraestructura de detección |
| Precisión | El contexto ayuda; cajas aproximadas | Menos alucinación por recorte; cajas exactas si se usa OpenCV |
| Simplicidad | La más simple (sin OpenCV en Lambda) | Más piezas y calibración con fotos reales que no existen |
| Privacidad | Se envía la foto completa (puede incluir niños o fondo) | Solo el recorte del post-it |

Se elige la foto completa para hoy y se deja el recorte como fase 2 si falla el recall o si se quiere más privacidad.

### Flujo
```
Navegador (SPA) --reduce a ≤2048 px, JPEG--> API Gateway REST (clave x-api-key, plan de uso)
   --> Lambda python3.13 (FastAPI + Mangum) --> Bedrock Converse (Haiku 5.5, perfil us.)
   <-- JSON { postits[], advertencias[], proveedor, modelo, duracion_ms }
La educadora ve cada post-it, corrige el texto si hace falta y asigna cada uno a un niño/a a mano.
```

### Límites vigentes que condicionan el diseño `[V]`
| Límite | Valor | Consecuencia |
|---|---|---|
| Carga útil síncrona de Lambda | 6 MB en la solicitud y 6 MB en la respuesta | Con base64 (+33 %) el JSON no debería superar unos 5 MB |
| Carga útil de API Gateway REST | 10 MB, no se puede aumentar | Lambda es el cuello de botella, no API Gateway |
| Imagen en Converse | ≤ 3,75 MB, ≤ 8000 px | La API rechaza con 413 sobre 3,5 MB ya decodificados |
| Tiempo de integración de API Gateway REST | 50 ms a 29 s por defecto; en APIs **regionales** se puede pedir más a costa de cuota de límite de tasa; en las optimizadas para borde no | Use `REGIONAL`. Lambda con `Timeout: 25` |
| Tiempo máximo de Lambda | 900 s | No es el límite aquí |
| Paquete de Lambda | 50 MB comprimido / 250 MB descomprimido | El paquete sin OpenCV pesa 58,8 MB descomprimido `[L]` |
| Runtimes | `python3.13` y `python3.14` disponibles | Coincide con su Python 3.13.14 local |

**¿Hay una razón fuerte para cambiar algo del plan?** No para el tipo de API ni Mangum: las claves de API y el límite por cliente existen solo en REST API (confirmado) `[V]`, y Mangum 0.22.0 (agosto de 2026) está mantenido y funcionó con Starlette 1.8.0 en mis pruebas `[L]`. Los ajustes recomendados son:
1. **Endpoint `REGIONAL`** (el tipo por defecto de SAM puede ser optimizado para borde, que tiene el tope de 29 s fijo `[V]`).
2. **El cliente debe reducir la foto antes de enviarla** (≤ 2048 px de lado largo, JPEG calidad ~85, unos 100–400 KB). Una foto de celular de 12 MP en base64 supera el límite de 6 MB. Si el front no puede, la alternativa sin cambiar el contrato es que el cliente suba directo a S3 con URL prefirmada, pero cambiaría el contrato `imagen_base64`; no es necesario hoy.
3. **CORS en la función:** con proxy de Lambda, API Gateway no agrega las cabeceras CORS a la respuesta real; las agrega la aplicación (`CORSMiddleware` en el código). La configuración `Cors` de SAM cubre la solicitud previa (OPTIONS) `[I]`.
4. **La API key no es autenticación.** AWS lo dice expresamente: sirve para identificar clientes y limitar tasa y cuota, y los límites son "mejor esfuerzo", no un control de gasto `[V]`. Una clave dentro de una SPA queda visible para cualquiera. Para la demo: plan de uso (2 req/s, ráfaga 5, 500 por día, ya en la plantilla), alarma de AWS Budgets y, si el servicio se expone más allá de la demo, un autorizador de Cognito o Lambda o llamarlo solo desde el backend principal.
5. **Documentación OpenAPI desactivada** en el código (`docs_url=None`) para no publicar `/docs` en el entorno.

### Contrato (el del plan, sin cambios)
`POST /api/postits/leer` con cabecera `x-api-key` y cuerpo JSON:
```json
{ "imagen_base64": "<JPEG/PNG/WebP en base64, hasta 3,5 MB decodificados; acepta prefijo data:image/...;base64,>" }
```
Respuesta 200:
```json
{
  "postits": [
    { "id": "pi-1", "texto": "Pintó con témpera\nverde", "posicion": { "x": 0.05, "y": 0.07, "ancho": 0.29, "alto": 0.37 },
      "confianza": 0.93, "legible": true },
    { "id": "pi-2", "texto": "Ñandú [ilegible] amigo", "posicion": { "x": 0.44, "y": 0.07, "ancho": 0.29, "alto": 0.37 },
      "confianza": 0.41, "legible": false }
  ],
  "advertencias": ["revisar_pi-2"],
  "proveedor": "bedrock",
  "modelo": "us.anthropic.claude-haiku-5-5",
  "duracion_ms": 4210
}
```
Notas de interpretación (conviene documentarlas en el README):
- `posicion` es una caja alineada a los ejes, normalizada 0..1 con origen arriba a la izquierda, relativa a la imagen **ya orientada** (la función corrige el giro EXIF antes de enviar).
- `confianza` es la **legibilidad autoinformada por el modelo** (0..1), no una probabilidad calibrada. Textract y Google entregan confianza por palabra; Bedrock no. Úsela solo como señal.
- `legible` = hay texto, no contiene `[ilegible]` y `confianza ≥ 0,50` (el mismo corte de certeza baja del diseño).
- `advertencias`: `revisar_pi-N` (nota dudosa) y `no_se_detecto_postit`.

Errores (cuerpo `{"detail": "..."}` de FastAPI; los 403 y 429 de API Gateway llegan como `{"message": ...}` `[I]`):
| Código | Cuándo | Qué hace la app |
|---|---|---|
| 400 | `imagen_base64` no es base64 | Corregir y reenviar |
| 403 | Falta o es inválida la API key (lo responde API Gateway) | — |
| 413 | Más de 3,5 MB decodificados | El cliente reduce la imagen |
| 422 | No es una imagen válida o falta el campo | Pedir otra foto |
| 429 | Plan de uso agotado (API Gateway) | Esperar |
| 503 (+ `Retry-After: 3`) | Bedrock responde `ThrottlingException` | Reintentar con espera |
| 502 | Error del proveedor o respuesta no interpretable | Reintentar una vez; si persiste, ingreso manual |
| 504 | Tiempo agotado | Reintentar una vez; si persiste, ingreso manual |

Tiempos y reintentos `[L]`: el cliente de `boto3` usa `connect_timeout=3`, `read_timeout=10` y 2 intentos (1 reintento automático en modo estándar), lo que da un peor caso de unos 20–23 s, por debajo de los 25 s de Lambda y los 29 s de API Gateway. Las pruebas locales cubrieron 400, 413, 422, 502, 503 y 504, más el caso sin post-its y el de baja legibilidad. En una prueba apareció un error real que ya está corregido: las excepciones de tiempo agotado de `botocore` heredan de `OSError`, así que la cláusula que captura errores de imagen las atrapaba antes y devolvía 422; ahora se valida la imagen antes de llamar al modelo y se capturan los tiempos agotados primero.

**La IA solo propone.** Si no hay post-its (`postits: []`) o el texto es dudoso (`legible: false`), la app muestra la nota para que la educadora escriba o corrija el texto y siempre confirma ella. Nada se guarda sin confirmación, igual que en el diseño.

### Cómo encaja con `ProveedorIA.transcribir` y `POST /api/capturas` del diseño
- `transcribir(media, formato): TextoTranscrito OR NULL` devuelve un solo texto. Una foto con varios post-its no cabe ahí. Propuesta: agregar a la interfaz un método `leerPostits(media): Lista<PostItLeido>` y dejar `transcribir(foto_postit)` como la unión de los textos separados por un salto de línea, para no romper al resto.
- Flujo: `POST /api/capturas` (202) guarda la captura → el procesamiento asíncrono llama al servicio (`/api/postits/leer` o directamente el módulo) con un tiempo máximo de **15 s**, que es el umbral del diseño para pasar a `revision_manual` (hoja de errores del diseño, línea 1042) → cada post-it leído queda como un ítem pendiente de asignar → estado `pendiente_asignacion`. Ese estado ya existe en el diseño ("no se identificó ningún niño"); aquí es el estado normal. La educadora toca el niño/a de cada ítem, ve el texto y confirma.
- Para el formato `formato_captura` del dataset (solo `video`, `audio`, `texto` o `foto`): una foto de post-its se guarda como `foto`; si hace falta distinguirla, agregar una columna propia de la app (por ejemplo `captura.subtipo = 'postit'`) sin tocar el dataset.
- Tabla nueva sugerida: `captura_postit(id_captura, indice, texto, x, y, ancho, alto, confianza, legible, id_nino NULL)`.
- **Cambios que hay que registrar en el diseño** (`design.md`): D6 (línea 43) dice que la demo debe funcionar sin red ni claves: ahora la demo **usa la nube** para post-its (el proveedor `local_lexico` sigue siendo local para el resto). La sección "Proveedor de IA externo" (línea 1086) dice que solo texto puede salir del equipo: ahora **sale la imagen del post-it** a Amazon Bedrock, con aviso a la usuaria. La tabla de la pila (línea 1136) y el diagrama de la arquitectura deben incluir Lambda + API Gateway + Bedrock. El contrato OpenAPI debe incluir el nuevo endpoint.

### Limpieza de texto (nota corta)
Antes de mostrar o guardar el texto de cada post-it (`limpiar_texto` en `main.py`): normalización Unicode **NFC** (una `ú` compuesta de dos caracteres pasa a uno), unificar saltos de línea (`\r\n` y `\r` → `\n`), colapsar espacios y tabulaciones repetidos, quitar espacios alrededor de los saltos y reducir líneas en blanco consecutivas a una sola. Si el texto se usa como `nota_breve`: aplanar a una línea y cortar a **280 caracteres**, en el límite de palabra cuando se puede. Probado `[L]`: un texto de 479 caracteres queda en 279; un texto con `u` + tilde combinada queda en 4 caracteres.

---

## 5. Privacidad (datos de menores)

El usuario ya autorizó enviar la imagen. Aun así, mitigaciones baratas y qué pasa con la opción recomendada:

| # | Mitigación | ¿Cumple con la recomendación (Bedrock + Haiku 5.5, perfil US)? |
|---|---|---|
| 1 | No guardar la imagen original sin necesidad | **Cumple.** La Lambda no escribe en S3 ni en disco y el código no registra el cuerpo. Revisar que API Gateway no tenga activado el registro completo de solicitudes y respuestas, y no registrar `imagen_base64` en la aplicación `[I]` |
| 2 | Retención cero y sin entrenamiento con los datos del proveedor | **Cumple.** Bedrock no almacena entradas ni salidas por defecto y no las comparte con los proveedores de modelos `[V]`; el registro de invocaciones viene desactivado `[V]`; AWS y los proveedores no usan las entradas para entrenar `[V]`. Excepciones documentadas: algunos modelos retienen 30 días para detección de abuso (Claude Fable 5 y 5.1; algunos de OpenAI), no Haiku 5.5, Sonnet 5.5 ni Nova `[V]`; y la detección de material de abuso infantil puede bloquear una solicitud con 400 y guardar la entrada flagged para revisión `[V]` (una foto normal de post-its no debería activarla, pero la app debe tolerar el 400 como 502) |
| 3 | Enviar solo el post-it, no rostros ni fondo | **No cumple por defecto** (se envía la foto completa). Mitigación barata: pedir en la interfaz "fotografíe solo los post-its, sin personas en el encuadre" y recortar en el cliente. Cumple del todo con la variante de fase 2 (OpenCV recorta y se envía solo el recorte) |
| 4 | Quitar metadatos (EXIF, ubicación GPS, fecha, modelo del teléfono) | **Cumple.** La función reencoda a JPEG con Pillow; verifiqué que EXIF y GPS desaparecen `[L]` |
| 5 | Acotar la región de procesamiento | **Cumple parcialmente.** El perfil `us.` limita el procesamiento a us-east-1, us-east-2 y us-west-2 (10 % más caro que `global.`) `[V]`; los datos no quedan en Chile. La política IAM de la plantilla solo permite esos modelos y perfiles |

Notas adicionales: (a) la educadora podría escribir en el post-it datos que identifican a un niño (un nombre real); el servicio no puede impedirlo, por lo que se debe pedir escribir solo lo que el diseño permite y avisar que el texto se procesa en un servicio externo `[I]`. (b) La Ley 21.719 de protección de datos personales de Chile: las fuentes que encontré difieren sobre la fecha de vigencia (1 de diciembre de 2026 según la mayoría; una fuente la da corrida a diciembre de 2027) `[NV]`. Esto no es asesoría legal; conviene consultarlo antes de un uso real.

---

## 6. Plan de pruebas sin fotos reales

### Cómo generar el set sintético
Use `generar_sinteticos.py` (anexo D, probado `[L]`): fondos madera, blanco y crema; 2 a 5 post-its amarillos o verdes de 250–330 px; 12 frases en español con tildes y ñ ("Compartió la pelota con un compañero", "Abrazó a la muñeca", "Recogió castañas"); fuentes manuscritas de Windows (Ink Free, Segoe Print, Lucida Handwriting, Bradley Hand, Segoe Script); rotación ±25°, sombra, gradiente de luz con tinte cálido, ruido, perspectiva suave, desenfoque y compresión JPEG. Escribe `gt.json` con el texto y la caja normalizada de cada nota (calculada con la misma transformación que la imagen; comprobé que las 23 cajas de una muestra caen sobre color de nota `[L]`). Defecto conocido: el borde negro que deja la transformación de perspectiva; irrelevante para la prueba.

`python generar_sinteticos.py sint 40` y `python evaluar.py sint https://<id>.execute-api.us-east-1.amazonaws.com/Prod/api/postits/leer <clave>`. Ejecutado contra un servicio simulado funciona `[L]`; contra el servicio real queda pendiente.

**Limitación honesta:** las fuentes manuscritas son más limpias que la letra real de una persona. Los resultados sintéticos son un **techo optimista**. Cuando existan 10–20 fotos reales (aunque sean tomadas el día del hackathon), repita la prueba y use los umbrales de la columna "con fotos reales".

Fuentes de imágenes públicas con licencia clara, sin descargar nada pesado: Wikimedia Commons muestra la licencia en cada archivo (por ejemplo, "Sticky's", licencia CC BY 2.0 `[V]`; buscar "post-it" o "sticky notes"); Pixabay y Roboflow Universe publican conjuntos de "sticky notes" con licencia indicada por conjunto (revisar cada una antes de usar, `[NV]`). Sirven para probar solo la detección, no el español manuscrito.

### Métricas y umbrales mínimos de aceptación
| Métrica | Cómo se mide | Umbral sobre sintético | Con fotos reales |
|---|---|---|---|
| Recall de detección | Fracción de notas reales emparejadas con una detección de IoU ≥ 0,5 (y ≥ 0,75 informativo) | ≥ 0,95 con IoU ≥ 0,5 | ≥ 0,90 |
| Precisión de detección | Detecciones sin nota real asociada | ≤ 5 % | ≤ 10 % |
| CER (error por carácter) | `jiwer.cer` entre texto real y leído, sobre notas emparejadas; se reportan **con** y **sin** tildes | ≤ 5 % con tildes | ≤ 15 % |
| WER (error por palabra) | `jiwer.wer`, mismo emparejamiento | ≤ 15 % | ≤ 30 % |
| Falsa legibilidad | Notas marcadas `legible: true` con CER > 30 % | ≤ 10 % de las legibles | ≤ 10 % |
| Latencia | Percentil 50 y 95 medido por el cliente (incluye red y arranque en frío) | p95 ≤ 12 s | p95 ≤ 15 s (umbral del diseño) |
| Errores HTTP | Respuestas no 200 tras reintentos | ≤ 2 % | ≤ 2 % |
| Costo | Costo por foto con tokens reales (pestaña de uso de Bedrock) | ≤ 0,01 USD | ≤ 0,01 USD |

Los umbrales son puntos de partida míos `[I]`; ajústelos con la primera corrida. Regla de decisión: si Haiku 5.5 no cumple CER o recall, repita con `BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-5-5` (con `BEDROCK_EXTRA` de esfuerzo bajo) y con `us.amazon.nova-2-lite-v1:0`, y elija el más barato que cumpla. Compare también Textract en la consola con 3 imágenes (5 minutos) para dejar documentado que no sirve para manuscrito.

---

## 7. Pasos para dejar el prototipo funcionando hoy (Windows + PowerShell)

Estado de su máquina `[L]`: Python 3.13.14 está instalado; **AWS CLI, SAM CLI y Docker no están instalados**; tiene `opencv-python`, `numpy` y `pillow` globales, por eso use un entorno virtual. El proyecto está bajo OneDrive: si puede, cree la carpeta fuera de OneDrive o excluya `.venv` y `build` de la sincronización `[I]`.

1. **Instalar herramientas** (instaladores MSI de AWS; la guía oficial de SAM CLI está en las fuentes): AWS CLI v2 y AWS SAM CLI. Docker no es necesario con el método de empaquetado de abajo.
2. **Credenciales:** si el hackathon entrega una cuenta con credenciales temporales, pegue las variables `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` y `AWS_SESSION_TOKEN` en la terminal; si es su cuenta, use `aws configure sso` o `aws configure`. Compruebe con `aws sts get-caller-identity`.
3. **Habilitar el modelo (10–15 min, hágalo primero):** consola de AWS → Amazon Bedrock → región **us-east-1** → Playground → elegir Claude Haiku 5.5 → completar el formulario de primer uso de Anthropic → enviar un mensaje con una foto cualquiera. Requiere un medio de pago válido `[V]`.
4. **Carpeta del proyecto** (por ejemplo `postits-api`) con los archivos del anexo: `leer_postits.py`, `main.py`, `template.yaml`, `requirements.txt` (versiones fijas verificadas con `pip check` en este equipo `[L]`):
```
fastapi==0.143.1
mangum==0.22.0
pydantic==2.14.1
pillow==12.3.0
boto3==1.43.114
```
   Para desarrollo local y pruebas agregue `uvicorn==0.54.0`, `httpx==0.28.1`, `numpy==2.5.4` y `jiwer==4.0.0` en un `requirements-dev.txt`. No instale `tenacity` aparte; no se usa.
5. **Entorno local y prueba de la llamada principal:**
```powershell
cd C:\ruta\a\postits-api
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
$env:PYTHONUTF8 = "1"; $env:AWS_DEFAULT_REGION = "us-east-1"
.\.venv\Scripts\python.exe leer_postits.py foto.jpg
```
   Si `Activate.ps1` está bloqueado por la política de ejecución, no lo necesita: use siempre la ruta `.\.venv\Scripts\python.exe`.
6. **Empaquetar para Lambda desde Windows sin Docker** (probado `[L]`; Pillow 12.3.0 solo publica ruedas `manylinux_2_28` y por eso se pasan dos plataformas):
```powershell
Remove-Item build -Recurse -Force -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m pip install --platform manylinux_2_28_x86_64 --platform manylinux2014_x86_64 --implementation cp --python-version 3.13 --only-binary=:all: --target build -r requirements.txt
Copy-Item main.py, leer_postits.py build\
```
   Resultado: 58,8 MB descomprimidos, con archivos `.so` de Linux `cp313` `[L]`. `sam deploy` sube a S3 la carpeta `CodeUri` tal cual `[V]`, así que no hace falta `sam build`. (Alternativa con Docker Desktop: `sam build --use-container`.)
7. **Validar y desplegar:**
```powershell
sam validate --lint
sam deploy --guided --stack-name postits-api --region us-east-1 --capabilities CAPABILITY_IAM
```
   (`cfn-lint` ya aprobó la plantilla del anexo `[L]`; `sam validate` y `sam deploy` no se ejecutaron porque SAM CLI no está instalado `[NV]`.) Anote las salidas `Url` y `ClaveApi`.
8. **Obtener el valor de la API key:**
```powershell
aws apigateway get-api-key --api-key <ID_de_ClaveApi> --include-value --query value --output text
```
9. **Probar el endpoint:**
```powershell
$b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("foto.jpg"))
$cuerpo = @{ imagen_base64 = $b64 } | ConvertTo-Json -Compress
Invoke-RestMethod -Method Post -Uri $url -Headers @{ "x-api-key" = $clave } -ContentType "application/json" -Body $cuerpo
```
   (Primero reduzca la foto a ≤ 2048 px: el endpoint rechaza más de 3,5 MB.) Compruebe también la solicitud previa de CORS con `curl.exe -X OPTIONS` `[I]`.
10. **Medir:** `generar_sinteticos.py` y `evaluar.py` (anexo D) y registre en una tabla los resultados contra los umbrales de la sección 6. Revise en la consola de Bedrock el uso de tokens para calcular el costo real.
11. **Control de gasto antes de compartir la URL:** cree una alarma de AWS Budgets (por ejemplo 5 USD) y desactive o rote la API key al terminar la demo.

### Script de la llamada principal (59 líneas, `leer_postits.py`)
Usa solo `boto3`, `Pillow` y la biblioteca estándar. Probado `[L]` con Bedrock simulado (parámetros validados por el modelo de servicio de `botocore`); no se ejecutó contra Bedrock real.

```python
"""Lee varios post-its manuscritos de una foto con Amazon Bedrock (Converse API), en una sola llamada."""
import io, json, os, sys

import boto3
from botocore.config import Config
from PIL import Image, ImageOps

MODELO = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-haiku-5-5")
LADO_MAX = int(os.getenv("LADO_MAX", "2048"))
CAJA_0_1000 = "nova" in MODELO  # Nova entrega cajas 0-1000; Claude las entrega en píxeles de la imagen enviada
EXTRA = {"thinking": {"type": "disabled"}} if "haiku-5-5" in MODELO else {}  # Haiku 5.5 piensa por defecto
EXTRA = json.loads(os.environ["BEDROCK_EXTRA"]) if "BEDROCK_EXTRA" in os.environ else EXTRA  # otros modelos
PROMPT = ("Esta foto tiene uno o más post-its manuscritos (español de Chile). Para CADA post-it devuelve su caja "
          "[x_min, y_min, x_max, y_max] {unidad} y transcribe el texto tal como está escrito, con tildes y ñ, "
          "sin corregir ni inventar; si una palabra no se entiende escribe [ilegible]. Ignora todo lo que no sea un "
          'post-it. Responde SOLO este JSON: {{"postits": [{{"caja": [0, 0, 0, 0], "texto": "...", '
          '"legibilidad": 0.0}}]}} con legibilidad de 0 a 1. Si no hay post-its responde {{"postits": []}}.')
_cliente = None


def cliente():
    global _cliente
    if _cliente is None:  # se reutiliza entre invocaciones calientes de Lambda
        _cliente = boto3.client("bedrock-runtime", config=Config(
            connect_timeout=3, read_timeout=10, retries={"max_attempts": 2, "mode": "standard"}))
    return _cliente


def preparar(origen):
    """Corrige el giro EXIF, reduce el tamaño y recodifica a JPEG (esto elimina EXIF y GPS)."""
    img = ImageOps.exif_transpose(Image.open(origen)).convert("RGB")
    img.thumbnail((LADO_MAX, LADO_MAX))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    return buf.getvalue(), img.size


def leer_postits(origen) -> list[dict]:
    jpeg, (w, h) = preparar(origen)
    unidad = "normalizada de 0 a 1000" if CAJA_0_1000 else f"en píxeles (la imagen mide {w}x{h})"
    args = dict(modelId=MODELO, inferenceConfig={"maxTokens": 2000}, messages=[{"role": "user", "content": [
        {"image": {"format": "jpeg", "source": {"bytes": jpeg}}}, {"text": PROMPT.format(unidad=unidad)}]}])
    if EXTRA:
        args["additionalModelRequestFields"] = EXTRA
    r = cliente().converse(**args)
    texto = "".join(b.get("text", "") for b in r["output"]["message"]["content"])
    datos, _ = json.JSONDecoder().raw_decode(texto[texto.index("{"):])  # tolera ```json ... ```
    ex, ey = (1000, 1000) if CAJA_0_1000 else (w, h)
    salida = []
    for p in datos["postits"]:
        x0, y0, x1, y1 = p["caja"]
        x0, x1, y0, y1 = (min(max(v, 0.0), 1.0) for v in (x0 / ex, x1 / ex, y0 / ey, y1 / ey))
        salida.append({"texto": p["texto"], "confianza": float(p.get("legibilidad", 0)),
                       "posicion": {"x": x0, "y": y0, "ancho": x1 - x0, "alto": y1 - y0}})
    return salida


if __name__ == "__main__":
    print(json.dumps(leer_postits(sys.argv[1]), ensure_ascii=False, indent=2))
```
(La versión probada tiene las mismas líneas sin las líneas en blanco entre funciones y con los caracteres acentuados escritos como `\u00f1` y similares; el comportamiento es idéntico.)

---

## 8. Riesgos y supuestos que no pude verificar

1. **Precisión real** de Claude Haiku 5.5 y Nova 2 Lite con manuscrito en español de Chile `[NV]`. No hay prueba publicada que yo haya encontrado; los benchmarks que vi son en inglés y con otros modelos. Es el riesgo principal.
2. **Cajas aproximadas del modelo.** Anthropic advierte que las coordenadas de Claude son aproximadas `[V]`; si el recall con IoU ≥ 0,5 es bajo, pasar a OpenCV + lectura por recorte.
3. **Latencia real** (sin medir): estimo 2–6 s para Haiku 5.5 con la razón desactivada, 4–10 s para Sonnet 5.5, 2–6 s para Nova 2 Lite, más 1–3 s si hay arranque en frío de Lambda `[I]`. El primer uso de un esquema estructurado puede tardar minutos `[V]`; el código no lo usa.
4. **Cuotas de Bedrock** de su cuenta (solicitudes y tokens por minuto) pueden ser bajas en cuentas nuevas `[NV]`. Revíselas en Service Quotas antes de la demo.
5. **Créditos del hackathon** y si cubren Claude (cobrado vía Marketplace) `[NV]`. Plan B: Nova 2 Lite.
6. **Lectura ambigua de las tarjetas de modelo** sobre "Structured outputs" y "tool use" en Haiku 5.5 `[NV]`; el código evita ambas funciones.
7. **Nova 2 Lite** tiene fecha de retiro "no antes del 2 de diciembre de 2026" `[V]`: sirve para la demo, pero no la fije en producción.
8. **Sonnet 5.5 y el razonamiento** (no se puede desactivar según fuentes secundarias) y el efecto de `effort: low` `[NV]`.
9. **No ejecuté** `sam build/validate/deploy`, `aws apigateway`, ni ninguna llamada a Bedrock, Textract, Google o Azure. Tampoco probé en AWS el comportamiento de CORS con `OPTIONS`, ni el 403 y 429 de API Gateway, ni que `sam deploy` acepte `CodeUri: build/` sin `sam build` (la documentación lo respalda, pero no lo ejecuté) `[NV]`.
10. **Fotos reales:** mis cifras de OpenCV y del generador son sintéticas; en fotos de celular con sombras duras, reflejos y manos serán peores.
11. **Precio por foto** y **tokens de imagen** de Bedrock son estimaciones mías con la fórmula de Anthropic; revise el uso real `[I]`.
12. **Azure:** hay contradicción documental sobre el manuscrito en español; no se probó. **Google:** la calidad en español manuscrito tampoco se probó.
13. **Ley 21.719:** fechas en conflicto entre fuentes y no es asesoría legal `[NV]`.
14. **Windows:** las rutas de fuentes del generador (`C:\Windows\Fonts\...`) existen en esta máquina `[L]`; en otra, edite la lista `FUENTES`.

---

## 9. Fuentes

**Diseño del proyecto (lectura de contexto):** `c:\Users\lucas\OneDrive\Escritorio\Hackaton\.kiro\specs\kindergarten-observation-platform\design.md` (Componente 4, D6 línea 43, tabla de errores línea 1042, seguridad línea 1086, pila línea 1136).

**Amazon Bedrock**
- Modelos con Converse: https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference-supported-models-features.html
- Tarjeta Claude Haiku 5.5: https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-5-5.html
- Tarjeta Claude Sonnet 5.5: https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-sonnet-5-5.html
- Tarjeta Nova 2 Lite: https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-amazon-nova-2-lite.html
- Lista de precios pública de AWS (Bedrock, us-east-1): https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonBedrockFoundationModels/current/us-east-1/index.json y https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonBedrock/current/us-east-1/index.json
- Límites de imágenes en Converse (objeto Message): https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Message.html
- Salidas estructuradas: https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html
- Razonamiento adaptativo y esfuerzo (Converse): https://docs.aws.amazon.com/bedrock/latest/userguide/claude-messages-adaptive-thinking.html
- Acceso a modelos: https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html
- Detección de abuso y retención: https://docs.aws.amazon.com/bedrock/latest/userguide/abuse-detection.html
- Uso de datos de entrada y salida: https://repost.aws/knowledge-center/amazon-bedrock-model-data-use
- Registro de invocaciones (desactivado por defecto): https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html
- Perfiles de inferencia y permisos IAM: https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-prereq.html
- Nova, detección de cajas (escala 0–1000): https://docs.aws.amazon.com/nova/latest/userguide/modalities-image.html
- Blog "Object detection with Amazon Nova 2 Lite": https://aws.amazon.com/blogs/machine-learning/object-detection-with-amazon-nova-2-lite/
- Créditos y Bedrock (re:Post): https://repost.aws/questions/QULMmXNMRwRvGSYm6OGt6e3Q/aws-credits-for-bedrock y AWS Activate: https://aws.amazon.com/startups/credits

**Amazon Textract y Rekognition**
- Límites, idiomas y manuscrito solo en inglés: https://docs.aws.amazon.com/textract/latest/dg/limits-document.html
- Preguntas frecuentes: https://aws.amazon.com/textract/faqs/
- Precios: https://aws.amazon.com/textract/pricing/ — prueba gratuita: https://aws.amazon.com/pm/textract/
- Transacciones por segundo: https://docs.aws.amazon.com/general/latest/gr/textract.html
- Anuncio del manuscrito (en inglés solamente): https://aws.amazon.com/es/blogs/aws-spanish/amazon-textract-reconoce-la-escritura-a-mano-y-anade-cinco-nuevos-idiomas/
- Rekognition precios y capa gratuita: https://aws.amazon.com/rekognition/pricing — DetectText: https://docs.aws.amazon.com/rekognition/latest/dg/text-detection.html

**Lambda, API Gateway, SAM, Mangum**
- Cuotas de Lambda: https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html
- Runtimes de Lambda: https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html
- Cuotas de REST API: https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-execution-service-limits-table.html
- REST vs HTTP API: https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-vs-rest.html
- Planes de uso y claves de API (no usarlas como autenticación): https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-usage-plans.html
- SAM: carga de archivos locales al desplegar: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/deploy-upload-local-files.html — instalación: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html
- Mangum 0.22.0: https://pypi.org/project/mangum/0.22.0/
- Versiones de paquetes (API JSON de PyPI): https://pypi.org/pypi/fastapi/json, https://pypi.org/pypi/mangum/json, https://pypi.org/pypi/boto3/json, https://pypi.org/pypi/pillow/json, https://pypi.org/pypi/pydantic/json, https://pypi.org/pypi/uvicorn/json, https://pypi.org/pypi/jiwer/json, https://pypi.org/pypi/aws-sam-cli/json

**Anthropic (modelos de Claude)**
- Visión, resolución y coordenadas aproximadas: https://platform.claude.com/docs/en/build-with-claude/vision
- Precios: https://platform.claude.com/docs/en/about-claude/pricing — Haiku 5.5: https://platform.claude.com/docs/en/models/haiku-5-5/overview
- Retención de datos: https://platform.claude.com/docs/en/build-with-claude/zero-data-retention

**Comparación breve (Google, Azure) y calidad de manuscrito**
- Google Vision precios: https://cloud.google.com/vision/pricing — cuotas: https://docs.cloud.google.com/vision/quotas — idiomas: https://docs.cloud.google.com/vision/docs/languages — manuscrito: https://docs.cloud.google.com/vision/docs/handwriting — uso de datos: https://docs.cloud.google.com/vision/docs/data-usage
- Azure idiomas (manuscrito): https://learn.microsoft.com/en-us/azure/ai-services/computer-vision/language-support — nota de transparencia: https://learn.microsoft.com/en-us/legal/cognitive-services/computer-vision/ocr-transparency-note — precios: https://azure.microsoft.com/en-us/pricing/details/cognitive-services/computer-vision/ y API pública https://prices.azure.com/api/retail/prices
- Gemini API (referencia, no recomendada aquí porque el nivel gratuito usa los datos para mejorar productos de Google): https://ai.google.dev/gemini-api/docs/pricing
- Benchmark de manuscrito (inglés): https://aimultiple.com/handwriting-recognition — artículo: https://arxiv.org/abs/2604.16504 — blog de proveedor de OCR: https://www.handwritingocr.com/blog/best-handwriting-ocr-api

**Detección clásica y datos de prueba**
- OpenCV, espacio HSV: https://docs.opencv.org/4.x/df/d9d/tutorial_py_colorspaces.html — watershed: https://docs.opencv.org/4.x/d3/db4/tutorial_py_watershed.html
- Wikimedia Commons (ejemplo con licencia CC BY 2.0): https://commons.wikimedia.org/wiki/File:Sticky's_(38713869981).jpg — Roboflow Universe: https://universe.roboflow.com/
- Ley 21.719 (fechas en conflicto): https://eipd.cl/ley-21719-explicada y https://www.preyproject.com/es/blog/ley-de-proteccion-de-datos-en-chile

---

## Anexo A. `main.py` (API FastAPI + Mangum, 100 líneas, probado `[L]` con eventos simulados de API Gateway REST)

```python
import base64, binascii, io, os, re, time, unicodedata
from botocore.exceptions import BotoCoreError, ClientError, ConnectTimeoutError, ReadTimeoutError
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel

import leer_postits as lector

app = FastAPI(title="Lectura de post-its", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv("ORIGEN_CORS", "*")], allow_methods=["POST"],
                   allow_headers=["Content-Type", "x-api-key"])  # el proxy de Lambda debe devolver las cabeceras CORS
Image.MAX_IMAGE_PIXELS = 60_000_000
MAX_BYTES = int(3.5 * 1024 * 1024)  # Converse acepta hasta 3,75 MB por imagen
UMBRAL = 0.50  # igual que el diseño: certeza < 0,50 exige revisión


class Entrada(BaseModel):
    imagen_base64: str


class Posicion(BaseModel):
    x: float
    y: float
    ancho: float
    alto: float


class PostIt(BaseModel):
    id: str
    texto: str
    posicion: Posicion
    confianza: float
    legible: bool


class Respuesta(BaseModel):
    postits: list[PostIt]
    advertencias: list[str]
    proveedor: str
    modelo: str
    duracion_ms: int


def limpiar_texto(t: str, para_nota: bool = False) -> str:
    """NFC, saltos de línea unificados, espacios colapsados. Con para_nota: una línea y máximo 280 caracteres."""
    t = unicodedata.normalize("NFC", t).replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[^\S\n]+", " ", t)  # espacios y tabs repetidos -> uno
    t = re.sub(r" ?\n ?", "\n", t)
    t = re.sub(r"\n{2,}", "\n", t).strip()
    if para_nota:
        t = t.replace("\n", " ")
        if len(t) > 280:
            t = t[:280].rsplit(" ", 1)[0] if " " in t[:280] else t[:280]
    return t


@app.post("/api/postits/leer", response_model=Respuesta)
def leer(entrada: Entrada):
    t0 = time.perf_counter()
    b64 = entrada.imagen_base64.split(",", 1)[-1]  # acepta "data:image/jpeg;base64,..."
    try:
        datos = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(400, "imagen_base64 no es base64 válido")
    if len(datos) > MAX_BYTES:
        raise HTTPException(413, "La imagen supera 3,5 MB; redúzcala antes de enviarla")
    try:  # valida la imagen ANTES de llamar al modelo (así un error de imagen no se confunde con uno de red)
        with Image.open(io.BytesIO(datos)) as im:
            im.verify()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError):
        raise HTTPException(422, "El archivo no es una imagen JPEG, PNG o WebP válida")
    try:
        crudo = lector.leer_postits(io.BytesIO(datos))
    except (ReadTimeoutError, ConnectTimeoutError):  # van primero: en botocore heredan de OSError
        raise HTTPException(504, "El modelo no respondió a tiempo")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ThrottlingException":
            raise HTTPException(503, "Servicio saturado; reintente en unos segundos", headers={"Retry-After": "3"})
        raise HTTPException(502, "Error del proveedor de IA")
    except BotoCoreError:
        raise HTTPException(502, "No se pudo contactar al proveedor de IA")
    except (ValueError, KeyError):
        raise HTTPException(502, "El modelo devolvió una respuesta que no se pudo interpretar")
    postits, avisos = [], []
    for i, p in enumerate(crudo, 1):
        texto = limpiar_texto(p["texto"])
        legible = bool(texto) and "[ilegible]" not in texto and p["confianza"] >= UMBRAL
        if not legible:
            avisos.append(f"revisar_pi-{i}")
        postits.append(PostIt(id=f"pi-{i}", texto=texto, posicion=p["posicion"], confianza=round(p["confianza"], 2), legible=legible))
    if not postits:
        avisos.append("no_se_detecto_postit")
    return Respuesta(postits=postits, advertencias=avisos, proveedor="bedrock", modelo=lector.MODELO,
                     duracion_ms=round((time.perf_counter() - t0) * 1000))


handler = Mangum(app, lifespan="off")
```

## Anexo B. `template.yaml` (AWS SAM, validado con `cfn-lint` 1.57.2 `[L]`)

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: Lectura de post-its manuscritos con Amazon Bedrock (Lambda + API Gateway REST + Mangum)

Parameters:
  ModeloId:
    Type: String
    Default: us.anthropic.claude-haiku-5-5
  OrigenCors:
    Type: String
    Default: "'*'"   # demo; en producción usar el dominio del front, por ejemplo "'https://app.ejemplo.cl'"

Globals:
  Function:
    Runtime: python3.13
    Architectures: [x86_64]
    Timeout: 25        # menor que los 29 s de API Gateway
    MemorySize: 1024
    Environment:
      Variables:
        BEDROCK_MODEL_ID: !Ref ModeloId

Resources:
  PostitsApi:
    Type: AWS::Serverless::Api
    Properties:
      StageName: Prod
      EndpointConfiguration:
        Type: REGIONAL
      Auth:
        ApiKeyRequired: true
        UsagePlan:
          CreateUsagePlan: PER_API
          Description: Plan de la demo
          Throttle:
            RateLimit: 2
            BurstLimit: 5
          Quota:
            Limit: 500
            Period: DAY
      Cors:
        AllowMethods: "'POST,OPTIONS'"
        AllowHeaders: "'Content-Type,x-api-key'"
        AllowOrigin: !Ref OrigenCors

  LectorFn:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: build/
      Handler: main.handler
      Policies:
        - Statement:
            - Effect: Allow
              Action: bedrock:InvokeModel
              Resource:
                - arn:aws:bedrock:us-*::foundation-model/anthropic.claude-haiku-5-5
                - arn:aws:bedrock:us-*::foundation-model/amazon.nova-2-lite-v1:0
                - !Sub arn:aws:bedrock:${AWS::Region}:${AWS::AccountId}:inference-profile/us.anthropic.claude-haiku-5-5
                - !Sub arn:aws:bedrock:${AWS::Region}:${AWS::AccountId}:inference-profile/us.amazon.nova-2-lite-v1:0
      Events:
        Leer:
          Type: Api
          Properties:
            RestApiId: !Ref PostitsApi
            Path: /api/postits/leer
            Method: POST

Outputs:
  Url:
    Value: !Sub https://${PostitsApi}.execute-api.${AWS::Region}.amazonaws.com/Prod/api/postits/leer
  ClaveApi:
    Description: Obtenga el valor con aws apigateway get-api-key --api-key <id> --include-value
    Value: !Ref PostitsApiApiKey
```
Para usar Sonnet 5.5 agregue su identificador de modelo y su perfil `us.` a los recursos permitidos de la política antes de cambiar `ModeloId` (identificador de modelo `anthropic.claude-sonnet-5-5` `[V]`). No agregué `ReservedConcurrentExecutions` porque en cuentas nuevas puede chocar con el mínimo de concurrencia sin reservar `[NV]`. Es una opción para limitar el gasto si su cuenta lo permite.

## Anexo C. Detector OpenCV de respaldo (fase 2; probado `[L]` con OpenCV 4.14.0.94 en el entorno virtual)

Dependencias adicionales (solo para correr local o empaquetar una segunda función): `opencv-python-headless==4.14.0.94` y `numpy==2.5.4`. La versión 5.0.0.93 también existe en PyPI; la 4.14 es la última de la rama 4 y es la que probé `[V][L]`.

```python
import cv2
import numpy as np

AMARILLO = ((18, 110, 130), (38, 255, 255))  # H va de 0 a 179 en OpenCV; S mínima alta evita fondos crema
VERDE = ((39, 60, 110), (85, 255, 255))


def detectar_postits(bgr, area_min: float = 0.004) -> list[dict]:
    h, w = bgr.shape[:2]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    mascara = cv2.inRange(hsv, *AMARILLO) | cv2.inRange(hsv, *VERDE)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17)))
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    notas = []
    for c in contornos:
        area = cv2.contourArea(c)
        if area < area_min * h * w:  # descarta manchas pequeñas
            continue
        (cx, cy), (rw, rh), ang = cv2.minAreaRect(c)
        if min(rw, rh) < 1:
            continue
        aspecto, relleno = max(rw, rh) / min(rw, rh), area / (rw * rh)
        if 1.8 <= aspecto <= 2.6 and relleno > 0.85:  # dos notas pegadas: partir por la mitad del lado largo
            u = np.array([np.cos(np.deg2rad(ang)), np.sin(np.deg2rad(ang))])
            if rw < rh:
                u = np.array([-u[1], u[0]])
            largo = max(rw, rh)
            for s in (-1, 1):
                ctr = (cx + s * u[0] * largo / 4, cy + s * u[1] * largo / 4)
                tam = (rw / 2, rh) if rw >= rh else (rw, rh / 2)
                notas.append({"poligono": cv2.boxPoints((ctr, tam, ang)), "revisar": True})
            continue
        notas.append({"poligono": cv2.boxPoints(((cx, cy), (rw, rh), ang)), "revisar": aspecto > 1.5 or relleno < 0.8})
    return notas


def enderezar(bgr, poligono, lado: int = 512):
    """Recorta el post-it y lo deja de frente (warpPerspective)."""
    p = poligono.astype("float32")
    suma, resta = p.sum(axis=1), np.diff(p, axis=1).ravel()
    orden = np.float32([p[suma.argmin()], p[resta.argmin()], p[suma.argmax()], p[resta.argmax()]])
    destino = np.float32([[0, 0], [lado - 1, 0], [lado - 1, lado - 1], [0, lado - 1]])
    return cv2.warpPerspective(bgr, cv2.getPerspectiveTransform(orden, destino), (lado, lado))
```
Con este módulo (escenas sintéticas de "par pegado") el recall con IoU ≥ 0,75 fue 30/30 y el recorte enderezado quedó 512×512 con 99 % de color de nota `[L]`. Limitación: el orden de esquinas por suma/diferencia puede dejar el recorte girado 90° si la nota está inclinada cerca de 45°; el modelo multimodal tolera texto girado, o pruebe los 4 giros si `legible` es falso `[I]`.

## Anexo D. Generador sintético y evaluador (probados `[L]` sin red)

**`generar_sinteticos.py`** (uso: `python generar_sinteticos.py sint 40`):
```python
"""Genera fotos sintéticas de post-its manuscritos (amarillo/verde) y su verdad de referencia (gt.json).
Uso: python generar_sinteticos.py carpeta_salida 30"""
import json, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FUENTES = [os.path.join(r"C:\Windows\Fonts", f) for f in ("Inkfree.ttf", "segoepr.ttf", "LHANDW.TTF", "BRADHITC.TTF", "segoesc.ttf")]
FRASES = ["Jugó con bloques y los apiló", "Dijo más agua al terminar", "Se columpió sola en el patio",
          "Pidió ayuda para amarrarse los zapatos", "Compartió la pelota con un compañero",
          "Pintó un árbol con pincel", "Contó hasta diez sin ayuda", "Lloró al despedirse y se calmó",
          "Armó una torre de seis bloques", "Cantó la canción de la rana", "Abrazó a la muñeca", "Recogió castañas"]
COLORES = [(255, 235, 59), (250, 225, 70), (170, 230, 90), (140, 220, 110)]
FONDOS = {"madera": (150, 118, 92), "blanco": (236, 236, 236), "crema": (228, 210, 160)}


def nota(lado, rng):
    im = Image.new("RGBA", (lado, lado), rng.choice(COLORES) + (255,))
    d, f = ImageDraw.Draw(im), ImageFont.truetype(rng.choice([p for p in FUENTES if os.path.exists(p)]), int(lado * 0.12))
    texto, lineas, act = rng.choice(FRASES), [], ""
    for w in texto.split():
        t = (act + " " + w).strip()
        if d.textlength(t, font=f) > lado * 0.8 and act:
            lineas.append(act)
            act = w
        else:
            act = t
    lineas.append(act)
    for i, ln in enumerate(lineas):
        d.text((lado * 0.1 + rng.uniform(-3, 3), lado * 0.18 + i * lado * 0.2), ln, font=f, fill=(30, 30, 70, 255))
    return im, texto


def coef(pa, pb):  # coeficientes PERSPECTIVE de Pillow: salida pa -> entrada pb
    A = [r for (x, y), (u, v) in zip(pa, pb) for r in ([x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y])]
    return np.linalg.solve(np.array(A, float), np.array(pb, float).reshape(8))


def escena(rng, W=1600, H=1200):
    lienzo = Image.new("RGBA", (W, H), rng.choice(list(FONDOS.values())) + (255,))
    celdas = [(60, 60), (560, 60), (1060, 60), (60, 600), (560, 600), (1060, 600)]
    rng.shuffle(celdas)
    mascaras, textos = [], []
    for _ in range(rng.randint(2, 5)):
        x, y = celdas.pop()
        im, t = nota(rng.randint(250, 330), rng)
        r = im.rotate(rng.uniform(-25, 25), expand=True, resample=Image.BICUBIC)
        sombra = Image.new("RGBA", r.size, (0, 0, 0, 0))
        sombra.putalpha(r.split()[3].filter(ImageFilter.GaussianBlur(7)).point(lambda v: int(v * 0.35)))
        x += rng.randint(0, 60)
        y += rng.randint(0, 60)
        lienzo.alpha_composite(sombra, (x + 6, y + 9))
        lienzo.alpha_composite(r, (x, y))
        m = Image.new("L", (W, H), 0)
        m.paste(r.split()[3].point(lambda v: 255 if v > 128 else 0), (x, y))
        mascaras.append(m)
        textos.append(t)
    img = np.array(lienzo.convert("RGB")).astype(np.float32) * np.linspace(0.82, 1.08, W)[None, :, None]
    img[..., 0] *= 1.05
    img[..., 2] *= 0.92
    img = Image.fromarray(np.clip(img + np.random.normal(0, 5, img.shape), 0, 255).astype(np.uint8))
    sal = [(25, 10), (W - 15, 30), (W - 30, H - 10), (10, H - 25)]  # perspectiva suave
    c = coef(sal, [(0, 0), (W, 0), (W, H), (0, H)])
    img = img.transform((W, H), Image.PERSPECTIVE, c, Image.BICUBIC).filter(ImageFilter.GaussianBlur(1))
    cajas = [m.transform((W, H), Image.PERSPECTIVE, c, Image.BILINEAR).point(lambda v: 255 if v > 127 else 0).getbbox() for m in mascaras]
    return img, [{"texto": t, "bbox": [b[0] / W, b[1] / H, b[2] / W, b[3] / H]} for t, b in zip(textos, cajas)]


if __name__ == "__main__":
    carpeta, n = sys.argv[1], int(sys.argv[2])
    os.makedirs(carpeta, exist_ok=True)
    rng, gt = random.Random(7), []
    np.random.seed(7)
    for i in range(n):
        img, notas = escena(rng)
        nombre = f"img_{i:03d}.jpg"
        img.save(os.path.join(carpeta, nombre), "JPEG", quality=85)
        gt.append({"archivo": nombre, "ancho": img.width, "alto": img.height, "postits": notas})
    json.dump(gt, open(os.path.join(carpeta, "gt.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{n} imágenes y gt.json en {carpeta}")
```

**`evaluar.py`** (uso: `python evaluar.py sint <URL> <API_KEY>`; imprime recall con IoU 0,5 y 0,75, CER con y sin tildes, WER, falsa legibilidad y latencia p50/p95):
```python
"""Evalúa el endpoint contra el set sintético. Uso: python evaluar.py carpeta URL API_KEY"""
import base64, json, os, re, statistics, sys, time, unicodedata
import httpx, jiwer


def norm(s, tildes=True):
    s = unicodedata.normalize("NFC", s.casefold())
    if not tildes:
        s = "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s)).strip()


def iou(a, b):
    ix, iy = max(0, min(a[2], b[2]) - max(a[0], b[0])), max(0, min(a[3], b[3]) - max(a[1], b[1]))
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - ix * iy
    return ix * iy / u if u else 0


def main(carpeta, url, clave):
    gt = json.load(open(os.path.join(carpeta, "gt.json"), encoding="utf-8"))
    n_gt = r50 = r75 = fallos = 0
    lat, cer_s, cer_t, wer, falsas_legibles, pares = [], [], [], [], 0, 0
    for item in gt:
        b64 = base64.b64encode(open(os.path.join(carpeta, item["archivo"]), "rb").read()).decode()
        t0 = time.perf_counter()
        r = httpx.post(url, json={"imagen_base64": b64}, headers={"x-api-key": clave}, timeout=30)
        lat.append(time.perf_counter() - t0)
        n_gt += len(item["postits"])
        if r.status_code != 200:
            fallos += 1
            continue
        dets, usados = r.json()["postits"], set()
        for g in item["postits"]:
            gb = g["bbox"]
            cand = [(iou(gb, [d["posicion"]["x"], d["posicion"]["y"], d["posicion"]["x"] + d["posicion"]["ancho"],
                              d["posicion"]["y"] + d["posicion"]["alto"]]), i) for i, d in enumerate(dets) if i not in usados]
            v, i = max(cand, default=(0, None))
            r50 += v >= 0.5
            r75 += v >= 0.75
            if v >= 0.5:
                usados.add(i)
                ref, hip = norm(g["texto"]), norm(dets[i]["texto"])
                c = jiwer.cer(ref, hip)
                cer_s.append(c)
                cer_t.append(jiwer.cer(norm(g["texto"], False), norm(dets[i]["texto"], False)))
                wer.append(jiwer.wer(ref, hip))
                pares += 1
                falsas_legibles += bool(dets[i]["legible"]) and c > 0.30
    q = lambda xs, p: sorted(xs)[min(len(xs) - 1, int(p * len(xs)))]
    m = statistics.mean
    print(json.dumps({"fotos": len(gt), "postits": n_gt, "fotos_con_error_http": fallos,
                      "recall_iou50": round(r50 / n_gt, 3), "recall_iou75": round(r75 / n_gt, 3),
                      "cer_con_tildes": round(m(cer_s), 3) if cer_s else None, "cer_sin_tildes": round(m(cer_t), 3) if cer_t else None,
                      "wer": round(m(wer), 3) if wer else None, "legibles_pero_cer_mayor_30": f"{falsas_legibles}/{pares}",
                      "latencia_p50_s": round(q(lat, 0.5), 2), "latencia_p95_s": round(q(lat, 0.95), 2)}, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:4])
```

## Anexo E. Qué se probó localmente y cómo (resumen)
Entorno temporal aislado (ya eliminado) con `fastapi==0.143.1`, `mangum==0.22.0`, `pydantic==2.14.1`, `pillow==12.3.0`, `boto3==1.43.114`, `numpy==2.5.4`, `opencv-python-headless==4.14.0.94`, `jiwer==4.0.0`, `httpx==0.28.1`, `uvicorn==0.54.0`: `pip check` sin conflictos en Windows con Python 3.13.14. Pruebas:
- Redimensión y giro EXIF; EXIF y GPS eliminados al reencodar.
- Bedrock simulado con `botocore.stub.Stubber` (valida la forma de los parámetros de `converse` contra el modelo de servicio real): camino feliz con JSON entre cercos de código, sin post-its, texto sin JSON, `ThrottlingException`, `AccessDeniedException`, tiempo agotado, y caja en escala 0–1000 (Nova).
- La API completa a través de `Mangum` con un evento de API Gateway REST simulado (cuerpo JSON, ruta, cabeceras, etapa): 200, 400, 413, 422 (dos causas), 502, 503, 504 y cabeceras CORS.
- Limpieza de texto (NFC, espacios, saltos, 280 caracteres), metadatos, contrato JSON exacto.
- Plantilla SAM con `cfn-lint` (incluida la transformación SAM): sin errores.
- Empaquetado cruzado Windows → Linux con `pip --platform`: 58,8 MB, `.so` de Linux `cp313`.
- Generador sintético (cajas de referencia sobre el color de las notas), evaluador y detector OpenCV (resultados de la sección 2).
- Experimento de detección HSV: 6 escenarios × 60 notas.
No se hizo ninguna llamada a Bedrock, Textract, Google, Azure ni a ningún otro servicio; solo se descargaron paquetes desde PyPI y listas públicas de precios de AWS y Azure.
