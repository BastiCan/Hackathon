"""Recortes de post-its -> texto literal con Amazon Bedrock (API Converse).

Adaptado del módulo aprobado `Hackaton/postits/leer.py` para el contrato de `integra-backend`
(texto.json): la lectura devuelve solo el texto literal y su legibilidad; separar, identificar
niños y clasificar lo hace ProcesarNota.

    lector = LectorBedrock()                      # BEDROCK_MODEL_ID, por defecto Claude Haiku 4.5
    lecturas = leer_recortes(recortes_jpeg, ninos, lector, contextos, plazo_s=30)
        -> [{"texto": str, "legibilidad": "alta" | "media" | "baja"}, ...]   (+ "error" / "no_json")
    postits = leer_foto(foto_jpeg, ninos, lector, plazo_s=30)              # Plan B: foto completa
        -> [{"texto", "legibilidad", "color", "caja": [x0, y0, x1, y1] (0-1000) | None}, ...]

- ninos: lista de {"nombre", "apellido", "apodos"} de la sala. Por defecto NO va en el prompt: con la
  lista, el modelo cambiaba nombres reales por otros parecidos de la sala ("Juanita" -> "Josefita").
  POSTITS_NOMBRES_EN_PROMPT=1 la vuelve a poner como ayuda de lectura. El backend reconoce variantes y
  apodos al identificar. El modelo copia los nombres tal como están escritos.
- El texto es literal: conserva los saltos de línea (\\n) y pone [ilegible] donde no se lee.
- Temperatura 0; si el modelo la rechaza (ValidationException que menciona "temperature"), se
  reintenta sin ella y las llamadas siguientes del contenedor ya no la envían (`sin_temperatura`).
- leer_recortes() lee en paralelo (POSTITS_HILOS_LECTURA hilos, por defecto 8) dentro de un plazo
  global (POSTITS_PLAZO_LECTURA_S, por defecto 20 s) y nunca se cae: un recorte que falla o no
  termina a tiempo vuelve con "error" (tipo de excepción o "PlazoAgotado") y legibilidad baja.
- Los logs nunca llevan textos leídos, prompts ni nombres: solo órdenes, tiempos y tipos de error.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as TiempoAgotadoFuturo
from concurrent.futures import wait

import cv2
import numpy as np

import recortar

log = logging.getLogger("postits.leer")

MODELO_POR_DEFECTO = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
REGION_POR_DEFECTO = "us-east-1"
HILOS_POR_DEFECTO = 8
MAX_TOKENS_RECORTE = 700
MAX_TOKENS_FOTO = 3000
LADO_LLM = 2000
LADO_MIN_LECTURA = 1000  # lado mayor mínimo del recorte que se manda al modelo
READ_TIMEOUT_S = 15  # por intento de Converse con un recorte: deja lugar a un reintento dentro del plazo
PLAZO_LECTURA_POR_DEFECTO_S = 20.0
MAX_CRUDO = 500  # caracteres del texto crudo cuando el modelo no devuelve JSON
ILEGIBLE = "[ilegible]"
COLORES = ("amarillo", "naranjo", "rosado", "verde", "celeste")
LEGIBILIDADES = ("alta", "media", "baja")


def _plazo_de_entorno() -> float:
    """Segundos de POSTITS_PLAZO_LECTURA_S ("12" o "12,5"); vacío o inválido: PLAZO_LECTURA_POR_DEFECTO_S."""
    crudo = os.environ.get("POSTITS_PLAZO_LECTURA_S", "").strip()
    if not crudo:
        return PLAZO_LECTURA_POR_DEFECTO_S
    try:
        plazo = float(crudo.replace(",", "."))
    except ValueError:
        plazo = math.nan
    if not math.isfinite(plazo) or plazo <= 0:
        log.warning("POSTITS_PLAZO_LECTURA_S invalido: se usan %g s", PLAZO_LECTURA_POR_DEFECTO_S)
        return PLAZO_LECTURA_POR_DEFECTO_S
    return plazo


def _hilos_de_entorno() -> int:
    """Hilos de POSTITS_HILOS_LECTURA (1 a 16); vacío o inválido: HILOS_POR_DEFECTO."""
    crudo = os.environ.get("POSTITS_HILOS_LECTURA", "").strip()
    if not crudo:
        return HILOS_POR_DEFECTO
    if crudo.isdigit() and 1 <= int(crudo) <= 16:
        return int(crudo)
    log.warning("POSTITS_HILOS_LECTURA invalido: se usan %d hilos", HILOS_POR_DEFECTO)
    return HILOS_POR_DEFECTO


def _nombres_en_prompt_de_entorno() -> bool:
    """POSTITS_NOMBRES_EN_PROMPT: "1" pone la lista de niños de la sala en el prompt de lectura; "0" o vacío
    (por defecto) no la pone."""
    crudo = os.environ.get("POSTITS_NOMBRES_EN_PROMPT", "").strip()
    if crudo not in ("", "0", "1"):
        log.warning("POSTITS_NOMBRES_EN_PROMPT invalido: la lista no va en el prompt")
    return crudo == "1"


PLAZO_LECTURA_S = _plazo_de_entorno()
HILOS = _hilos_de_entorno()
NOMBRES_EN_PROMPT = _nombres_en_prompt_de_entorno()

_BLOQUE_NINOS = """Niños de la sala (nombre y apodos), solo para ayudarte a leer la letra:
{ninos}
"""

_REGLAS_NOMBRE_CON_LISTA = """- Copia cada nombre tal como está escrito, aunque se parezca a uno de la lista o esté mal escrito.
- Si no puedes leer el nombre con seguridad, escribe [ilegible]. Nunca elijas un nombre de la lista solo porque se parece.
"""
_REGLAS_NOMBRE_SIN_LISTA = """- Copia cada nombre tal como está escrito, aunque esté mal escrito.
- Si no puedes leer el nombre con seguridad, escribe [ilegible].
"""

_REGLAS = """- Transcribe literal: no resumas, no corrijas ortografía, no completes ni agregues palabras.
{reglas_nombre}- Mantén los saltos de línea {de} (en el JSON van como \\n).
- Si una palabra o un trozo no se puede leer, escribe [ilegible] en su lugar. Si no se puede leer nada, el texto es [ilegible].
- No adivines ni inventes: si no estás seguro de una palabra, escribe [ilegible].
"""

# Orientación: índices 0 a 3 = 0°, 90° horario, 180° y 90° antihorario (giro_grados 0, 90, 180, 270).
# El eje de la letra lo decide recortar.eje_texto sin el modelo; solo si la letra está vertical, el modelo
# elige entre 90° horario (imagen 1) y 90° antihorario (imagen 2). El 180° no se considera.
GIROS = (None, cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_180, cv2.ROTATE_90_COUNTERCLOCKWISE)
GIROS_VERTICAL = (1, 3)
LADO_GIRO = 640
PROMPT_GIRO = """Las 2 imágenes (1 y 2) son el mismo post-it escrito a mano, girado de 2 formas: una es la otra dada vuelta (180°).
¿En cuál de las 2 la letra está derecha, es decir, se lee normalmente de izquierda a derecha y con las líneas de arriba hacia abajo?
Responde solo JSON: {"derecha": 1, "seguro": true}
("derecha" es 1 o 2; "seguro" es false si no se puede saber)."""

PROMPT_RECORTE = ("""Transcribe este post-it escrito a mano por una educadora de párvulos en Chile.
Formato habitual: "Nombre: observación".
{bloque_ninos}Reglas:
""" + _REGLAS.replace("{de}", "del post-it") + """Responde solo JSON:
{{"texto": "...", "legibilidad": "alta|media|baja"}}""")

PROMPT_FOTO = ("""Esta foto muestra varios post-its escritos a mano por una educadora de párvulos en Chile.
Formato habitual de cada post-it: "Nombre: observación".
{bloque_ninos}Algunos post-its pueden estar girados: lee cada uno en la orientación de su letra.
Para cada post-it entrega su color (amarillo, naranjo, rosado, verde o celeste), su posición aproximada como caja [x_min, y_min, x_max, y_max] en coordenadas normalizadas de 0 a 1000 (0,0 es la esquina superior izquierda de la foto) y su texto.
Reglas:
""" + _REGLAS.replace("{de}", "de cada post-it") + """- No juntes dos post-its en uno ni separes uno en dos.
Responde solo JSON:
{{"postits": [{{"color": "amarillo", "caja": [0, 0, 1000, 1000], "texto": "...", "legibilidad": "alta|media|baja"}}]}}""")


# ----------------------------------------------------------------------------- utilidades

def lista_ninos(roster) -> str:
    """'Benjamín (Benja), Sofía (Sofi), ...' para el prompt."""
    partes = []
    for nino in roster or []:
        nombre = " ".join(p for p in (nino.get("nombre", ""), nino.get("apellido", "")) if p).strip()
        apodos = [a for a in nino.get("apodos") or [] if a]
        partes.append(f"{nombre} ({', '.join(apodos)})" if apodos else nombre)
    return ", ".join(p for p in partes if p)


def _partes_prompt(roster) -> dict:
    """Bloque con la lista de niños y reglas de nombres: con lista solo si POSTITS_NOMBRES_EN_PROMPT=1."""
    ninos = lista_ninos(roster) if NOMBRES_EN_PROMPT else ""
    if not ninos:
        return {"bloque_ninos": "", "reglas_nombre": _REGLAS_NOMBRE_SIN_LISTA}
    return {"bloque_ninos": _BLOQUE_NINOS.format(ninos=ninos), "reglas_nombre": _REGLAS_NOMBRE_CON_LISTA}


def prompt_recorte(roster) -> str:
    return PROMPT_RECORTE.format(**_partes_prompt(roster))


def prompt_foto(roster) -> str:
    return PROMPT_FOTO.format(**_partes_prompt(roster))


def _sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def _primer_objeto(texto: str) -> str | None:
    """Primer objeto JSON {...} balanceado del texto (respeta strings y escapes)."""
    inicio = texto.find("{")
    if inicio < 0:
        return None
    profundidad, en_string, escape = 0, False, False
    for i in range(inicio, len(texto)):
        c = texto[i]
        if en_string:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                en_string = False
        elif c == '"':
            en_string = True
        elif c == "{":
            profundidad += 1
        elif c == "}":
            profundidad -= 1
            if profundidad == 0:
                return texto[inicio:i + 1]
    return None


def extraer_json(texto: str):
    """Objeto (dict o lista) de la respuesta del modelo, tolerando cercas ```, texto alrededor y
    saltos de línea literales dentro de los strings (strict=False)."""
    limpio = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", texto.strip(), flags=re.IGNORECASE)
    for variante in (limpio, limpio.replace("\u201c", '"').replace("\u201d", '"')):
        for candidato in (variante, _primer_objeto(variante)):
            if not candidato:
                continue
            for estricto in (True, False):
                try:
                    valor = json.loads(candidato, strict=estricto)
                except json.JSONDecodeError:
                    continue
                if isinstance(valor, (dict, list)):
                    return valor
    return None


def _texto_literal(valor) -> str:
    """Texto literal: conserva los saltos internos, unifica \\r\\n, [?] -> [ilegible]; vacío -> [ilegible]."""
    if valor is None:
        texto = ""
    elif isinstance(valor, list):
        texto = "\n".join(_texto_literal(v) for v in valor if v is not None)
    else:
        texto = str(valor)
    texto = texto.replace("\r\n", "\n").replace("\r", "\n").replace("[?]", ILEGIBLE).strip()
    return texto or ILEGIBLE


def _legibilidad(valor) -> str:
    normal = _sin_tildes(str(valor or "")).strip().lower()
    return normal if normal in LEGIBILIDADES else "media"


def normalizar_lectura(valor, crudo: str = "") -> dict:
    """Lectura con tipos garantizados. Sin JSON: el texto crudo (500 caracteres) con legibilidad baja."""
    if not isinstance(valor, dict):
        return {"texto": _texto_literal(crudo.strip()[:MAX_CRUDO]), "legibilidad": "baja", "no_json": True}
    return {"texto": _texto_literal(valor.get("texto")), "legibilidad": _legibilidad(valor.get("legibilidad"))}


def _caja(valor):
    """Caja [x_min, y_min, x_max, y_max] en 0-1000 o None si no sirve."""
    if not isinstance(valor, (list, tuple)) or len(valor) != 4:
        return None
    try:
        x0, y0, x1, y1 = (min(1000.0, max(0.0, float(v))) for v in valor)
    except (TypeError, ValueError):
        return None
    if x1 <= x0 or y1 <= y0:
        return None
    return [round(x0), round(y0), round(x1), round(y1)]


def normalizar_postits_foto(valor) -> list[dict]:
    """Lista de post-its del Plan B con tipos garantizados y color dentro del conjunto conocido."""
    if isinstance(valor, dict):
        valor = valor.get("postits")
    if not isinstance(valor, list):
        return []
    salida = []
    for item in valor:
        if not isinstance(item, dict):
            continue
        lectura = normalizar_lectura(item)
        color = _sin_tildes(str(item.get("color") or "")).strip().lower()
        lectura["color"] = color if color in COLORES else "desconocido"
        lectura["caja"] = _caja(item.get("caja"))
        salida.append(lectura)
    return salida


def preparar_recorte_llm(rgb: np.ndarray, lado_min: int = LADO_MIN_LECTURA) -> bytes:
    """Recorte para el modelo: ampliado hasta `lado_min` px de lado mayor (un recorte de 300 px son muy
    pocos tokens de imagen y el modelo lee peor la letra). El recorte guardado en S3 no cambia."""
    escala = lado_min / max(rgb.shape[:2])
    if escala > 1:
        rgb = cv2.resize(rgb, None, fx=escala, fy=escala, interpolation=cv2.INTER_CUBIC)
    return recortar.codificar_jpeg(rgb, calidad=90)


def preparar_foto_llm(rgb: np.ndarray, lado: int = LADO_LLM) -> bytes:
    """Foto completa reducida a `lado` px y comprimida para los límites de Converse (Plan B)."""
    escala = min(1.0, lado / max(rgb.shape[:2]))
    reducida = rgb if escala == 1.0 else cv2.resize(rgb, None, fx=escala, fy=escala, interpolation=cv2.INTER_AREA)
    return recortar.codificar_jpeg(reducida, calidad=85)


def _texto_converse(respuesta: dict) -> str:
    contenido = respuesta.get("output", {}).get("message", {}).get("content", [])
    return "".join(bloque.get("text", "") for bloque in contenido if isinstance(bloque, dict))


def _region() -> str:
    return os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or REGION_POR_DEFECTO


def _configuracion_boto(read_timeout: float = READ_TIMEOUT_S):
    from botocore.config import Config  # el zip de Lambda usa el boto3 del runtime

    return Config(retries={"mode": "adaptive", "max_attempts": 6}, connect_timeout=5, read_timeout=read_timeout)


# ----------------------------------------------------------------------------- lector

class LectorBedrock:
    """Lectura con Amazon Bedrock (API Converse). `cliente` permite inyectar uno (Stubber en pruebas)."""

    nombre = "bedrock"

    def __init__(self, modelo: str | None = None, region: str | None = None, cliente=None):
        self.modelo = modelo or os.environ.get("BEDROCK_MODEL_ID") or MODELO_POR_DEFECTO
        self.region = region or _region()
        self._cliente = cliente  # recortes
        self._cliente_foto = cliente  # Plan B; un cliente inyectado sirve para los dos
        self._candado = threading.Lock()
        self.sin_temperatura = False

    def _crear_cliente(self, read_timeout: float):
        import boto3

        return boto3.client("bedrock-runtime", region_name=self.region, config=_configuracion_boto(read_timeout))

    @property
    def cliente(self):
        with self._candado:
            if self._cliente is None:
                self._cliente = self._crear_cliente(READ_TIMEOUT_S)
            return self._cliente

    @property
    def cliente_foto(self):
        with self._candado:
            if self._cliente_foto is None:
                self._cliente_foto = self._crear_cliente(max(READ_TIMEOUT_S, PLAZO_LECTURA_S))
            return self._cliente_foto

    def _converse(self, cliente, imagen_jpeg: bytes, prompt: str, max_tokens: int) -> str:
        if len(imagen_jpeg) > recortar.MAX_BYTES_IMAGEN:
            raise ValueError("La imagen supera el limite de 3.75 MB de Converse")
        return self._converse_contenido(cliente, [{"image": {"format": "jpeg", "source": {"bytes": imagen_jpeg}}},
                                                  {"text": prompt}], max_tokens)

    def _converse_contenido(self, cliente, contenido: list, max_tokens: int) -> str:
        from botocore.exceptions import ClientError

        mensajes = [{"role": "user", "content": contenido}]
        inferencia = ({"maxTokens": max_tokens} if self.sin_temperatura
                      else {"temperature": 0.0, "maxTokens": max_tokens})
        try:
            respuesta = cliente.converse(modelId=self.modelo, messages=mensajes, inferenceConfig=inferencia)
        except ClientError as e:
            err = e.response.get("Error", {})
            if (err.get("Code") == "ValidationException" and "temperature" in str(err.get("Message", "")).lower()
                    and "temperature" in inferencia):
                log.warning("temperatura_no_soportada modelo=%s", self.modelo)
                self.sin_temperatura = True  # las llamadas siguientes del contenedor ya no la envían
                inferencia = {k: v for k, v in inferencia.items() if k != "temperature"}
                respuesta = cliente.converse(modelId=self.modelo, messages=mensajes, inferenceConfig=inferencia)
            else:
                raise
        return _texto_converse(respuesta)

    def leer(self, imagen_jpeg: bytes, roster, contexto=None) -> dict:
        crudo = self._converse(self.cliente, imagen_jpeg, prompt_recorte(roster), MAX_TOKENS_RECORTE)
        return normalizar_lectura(extraer_json(crudo), crudo)

    def giro(self, rgb_recorte: np.ndarray) -> int | None:
        """Para un recorte con la letra vertical: índice de GIROS (1 = 90° horario o 3 = 90° antihorario) que
        la deja derecha, o None si el modelo no está seguro."""
        escala = LADO_GIRO / max(rgb_recorte.shape[:2])
        base = cv2.resize(rgb_recorte, None, fx=escala, fy=escala,
                          interpolation=cv2.INTER_AREA if escala < 1 else cv2.INTER_CUBIC)
        contenido = []
        for n, indice in enumerate(GIROS_VERTICAL, start=1):
            girada = cv2.rotate(base, GIROS[indice])
            contenido += [{"text": f"Imagen {n}:"},
                          {"image": {"format": "jpeg", "source": {"bytes": recortar.codificar_jpeg(girada, calidad=85)}}}]
        contenido.append({"text": PROMPT_GIRO})
        respuesta = self._converse_contenido(self.cliente, contenido, 60)
        valor = extraer_json(respuesta)
        if not isinstance(valor, dict) or valor.get("seguro") is False:
            return None
        try:
            n = int(valor.get("derecha"))
        except (TypeError, ValueError):
            return None
        return GIROS_VERTICAL[n - 1] if 1 <= n <= len(GIROS_VERTICAL) else None

    def leer_foto_completa(self, imagen_jpeg: bytes, roster, contexto=None) -> list[dict]:
        crudo = self._converse(self.cliente_foto, imagen_jpeg, prompt_foto(roster), MAX_TOKENS_FOTO)
        return normalizar_postits_foto(extraer_json(crudo))


class PlazoAgotado(TimeoutError):
    """La lectura no terminó dentro del plazo global."""


def _lectura_fallida(error: str) -> dict:
    return {"texto": "", "legibilidad": "baja", "error": error}


def leer_recortes(recortes: list[bytes], roster, lector, contextos=None, hilos: int | None = None,
                  plazo_s: float | None = None) -> list[dict]:
    """Lee todos los recortes en paralelo, en el mismo orden, dentro de un plazo global.

    Un recorte que falla no corta el resto. Los que no terminan en plazo_s segundos vuelven con
    "error": "PlazoAgotado", sin esperar a sus hilos.
    """
    contextos = contextos or [{} for _ in recortes]
    plazo = PLAZO_LECTURA_S if plazo_s is None else plazo_s
    hilos = HILOS if hilos is None else hilos

    def leer_uno(i: int) -> dict:
        inicio = time.perf_counter()
        try:
            lectura = lector.leer(recortes[i], roster, contextos[i])
        except Exception as error:  # Bedrock caído, sin permisos, cuota, etc.
            log.warning("lectura_fallida orden=%s error=%s", contextos[i].get("orden"), type(error).__name__)
            return _lectura_fallida(type(error).__name__)
        log.debug("lectura orden=%s ms=%d", contextos[i].get("orden"), (time.perf_counter() - inicio) * 1000)
        return lectura

    if not recortes:
        return []
    grupo = ThreadPoolExecutor(max_workers=max(1, min(hilos, len(recortes))))
    try:
        futuros = [grupo.submit(leer_uno, i) for i in range(len(recortes))]
        wait(futuros, timeout=plazo)
        lecturas = []
        for i, futuro in enumerate(futuros):
            if futuro.done():
                lecturas.append(futuro.result())
            else:
                log.warning("lectura_fuera_de_plazo orden=%s plazo_s=%g", contextos[i].get("orden"), plazo)
                lecturas.append(_lectura_fallida(PlazoAgotado.__name__))
        return lecturas
    finally:
        grupo.shutdown(wait=False, cancel_futures=True)


def leer_foto(imagen_jpeg: bytes, roster, lector, contexto=None, plazo_s: float | None = None) -> list[dict]:
    """lector.leer_foto_completa() (Plan B) con el plazo global; lanza PlazoAgotado si no termina a tiempo."""
    plazo = PLAZO_LECTURA_S if plazo_s is None else plazo_s
    grupo = ThreadPoolExecutor(max_workers=1)
    try:
        futuro = grupo.submit(lector.leer_foto_completa, imagen_jpeg, roster, contexto)
        try:
            return futuro.result(timeout=plazo)
        except TiempoAgotadoFuturo:
            if futuro.done():
                return futuro.result()
            raise PlazoAgotado(f"La lectura de la foto completa no termino en {plazo:g} s.") from None
    finally:
        grupo.shutdown(wait=False, cancel_futures=True)
