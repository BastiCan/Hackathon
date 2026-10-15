"""Pruebas de `datos/capturas.py`: contador atómico del día, filas y archivado.

Los módulos de otros carriles que todavía no están escritos se reemplazan por
dobles (`instalar_dobles`) y DynamoDB por un `Almacen` en memoria: estas pruebas
no tocan AWS. Cuando el carril dueño escribe el módulo real, el doble no se
instala y las pruebas corren contra el código real.
"""
from __future__ import annotations

import base64
import importlib
import importlib.machinery
import importlib.util
import json
import sys
import types
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from huellita_api.config import Config, cargar_config
from huellita_api.modelos import Usuaria

DIA = "2026-10-15"
CREADA_EN = "2026-10-15T14:05:57-03:00"
ID = "CAP-01M503FN5942S3MNAFA14C07AQ"

# Código estable -> estado HTTP, igual que `errores.CODIGOS_HTTP` del carril base.
CODIGOS_HTTP = {
    "sin_acceso": 403,
    "autora_desconocida": 422,
    "sala_desconocida": 404,
    "no_encontrado": 404,
    "solicitud_invalida": 422,
    "formato_no_soportado": 422,
    "texto_invalido": 422,
    "base64_invalido": 422,
    "sugerencia_desconocida": 404,
    "nino_de_otra_sala": 422,
    "audio_demasiado_grande": 413,
    "formato_audio_no_soportado": 415,
    "tope_diario": 429,
    "servicio_saturado": 503,
    "error_envio": 502,
    "transcriptor_caido": 502,
    "error_interno": 500,
}

# Las dos únicas condiciones que escribe datos/capturas.py.
CONDICIONES = {
    "attribute_not_exists(total) OR total < :max": lambda item, valores: (
        "total" not in item or int(item["total"]["N"]) < int(valores[":max"]["N"])
    ),
    "attribute_exists(id_captura) AND sala_key = :sk": lambda item, valores: (
        "id_captura" in item and item.get("sala_key") == valores[":sk"]
    ),
}


def cfg_de_prueba(**entorno: str) -> Config:
    """Config con los mismos nombres de variables que `template.yaml`."""
    base = {
        "TABLA_CAPTURAS": "huellita-capturas-prueba",
        "TABLA_DECISIONES": "huellita-decisiones-prueba",
        "BUCKET_CAPTURAS": "integra-capturas-prueba",
        "JARDIN_DEMO": "JAR-0001",
        "SALAS_DEMO": "SG-A,SG-B",
        "MAX_CAPTURAS_DIA": "300",
        "MINUTOS_MAX_PROCESANDO": "20",
        "ZONA_HORARIA": "America/Santiago",
    }
    base.update(entorno)
    return cargar_config(base)


def _doble(nombre: str) -> types.ModuleType | None:
    """Módulo vacío registrado en `sys.modules`, o `None` si el real ya existe."""
    if importlib.util.find_spec(nombre) is not None:
        return None
    modulo = types.ModuleType(nombre)
    modulo.__spec__ = importlib.machinery.ModuleSpec(nombre, None)
    sys.modules[nombre] = modulo
    paquete, _, hoja = nombre.rpartition(".")
    setattr(importlib.import_module(paquete), hoja, modulo)
    return modulo


def _doble_errores() -> None:
    """`errores.py` del carril base (CONTRATOS.md §2 y §4)."""
    modulo = _doble("huellita_api.errores")
    if modulo is None:
        return

    class ErrorApi(Exception):
        """Error con código estable."""

        def __init__(self, codigo: str, mensaje: str) -> None:
            super().__init__(mensaje)
            self.codigo = codigo
            self.mensaje = mensaje

    def error(codigo: str) -> ErrorApi:
        return ErrorApi(codigo, modulo.MENSAJES.get(codigo, "No pudimos hacer esto."))

    def estado_http(codigo: str) -> int:
        return modulo.CODIGOS_HTTP.get(codigo, 500)

    modulo.ErrorApi = ErrorApi
    modulo.CODIGOS_HTTP = dict(CODIGOS_HTTP)
    modulo.MENSAJES = {codigo: f"No pudimos hacer esto ({codigo})." for codigo in CODIGOS_HTTP}
    modulo.error = error
    modulo.estado_http = estado_http


def _doble_tiempo() -> None:
    """`tiempo.py` del carril base, con la hora de Chile."""
    modulo = _doble("huellita_api.tiempo")
    if modulo is None:
        return

    def ahora(cfg: Config) -> datetime:
        return datetime.now(ZoneInfo(cfg.zona_horaria))

    def reloj_de(cfg: Config, reloj=None) -> datetime:
        return reloj() if reloj is not None else ahora(cfg)

    def iso(momento: datetime) -> str:
        return momento.isoformat(timespec="seconds")

    def dia(momento: datetime) -> str:
        return momento.date().isoformat()

    modulo.ahora = ahora
    modulo.reloj_de = reloj_de
    modulo.iso = iso
    modulo.dia = dia


def _doble_dynamo() -> None:
    """`datos/dynamo.py` del carril base: sin `Almacen` conectado, no responde."""
    modulo = _doble("huellita_api.datos.dynamo")
    if modulo is None:
        return

    def sin_conectar(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("conecta un Almacen con almacen.conectar(monkeypatch)")

    for nombre in ("cliente", "consultar_todo", "obtener", "obtener_varios", "poner", "actualizar", "borrar"):
        setattr(modulo, nombre, sin_conectar)


def _doble_auth() -> None:
    """`auth.py` del carril de lectura, con el `usuarias_demo.json` de verdad."""
    modulo = _doble("huellita_api.auth")
    if modulo is None:
        return
    errores = importlib.import_module("huellita_api.errores")
    paquete = importlib.import_module("huellita_api")
    ruta = Path(paquete.__file__).parent / "datos" / "usuarias_demo.json"
    filas = json.loads(ruta.read_text(encoding="utf-8"))["usuarias"]

    def usuarias() -> list[Usuaria]:
        return [Usuaria(**fila) for fila in filas]

    def existe(id_usuaria: str) -> bool:
        return any(fila["id"] == id_usuaria for fila in filas)

    def usuaria_o_error(id_usuaria: str | None) -> Usuaria:
        if not id_usuaria:
            raise errores.error("sin_acceso")
        for usuaria in usuarias():
            if usuaria.id == id_usuaria:
                return usuaria
        raise errores.error("autora_desconocida")

    def exigir_sala(cfg: Config, usuaria: Usuaria, sala_id: str) -> None:
        if sala_id not in cfg.salas:
            raise errores.error("sala_desconocida")
        if sala_id not in usuaria.salaIds:
            raise errores.error("sin_acceso")

    modulo.CABECERA_USUARIA = "X-Usuaria-Id"
    modulo.usuarias = usuarias
    modulo.existe = existe
    modulo.usuaria_o_error = usuaria_o_error
    modulo.exigir_sala = exigir_sala


def _doble_audio() -> None:
    """`datos/audio.py` del carril de audio. `enviar` nunca sale a la red: las
    pruebas que lo necesitan lo reemplazan."""
    modulo = _doble("huellita_api.datos.audio")
    if modulo is None:
        return
    errores = importlib.import_module("huellita_api.errores")

    def decodificar(audio_base64: str) -> bytes:
        try:
            crudo = base64.b64decode(audio_base64, validate=True)
        except Exception as falla:
            raise errores.error("base64_invalido") from falla
        if len(crudo) > modulo.MAX_BYTES_AUDIO:
            raise errores.error("audio_demasiado_grande")
        return crudo

    def enviar(cfg: Config, id_captura: str, audio_base64: str) -> str:
        raise AssertionError("la prueba tiene que reemplazar audio.enviar")

    def sincronizar(cfg: Config, sala_id: str, reloj=None) -> None:
        return None

    modulo.MAX_BYTES_AUDIO = 4194304
    modulo.MAX_CONSULTAS_PARALELAS = 4
    modulo.decodificar = decodificar
    modulo.enviar = enviar
    modulo.sincronizar = sincronizar


def instalar_dobles() -> None:
    """Dobles de lo que necesita `datos/capturas.py` y todavía no esté escrito."""
    _doble_errores()
    _doble_tiempo()
    _doble_dynamo()


def instalar_dobles_de_rutas() -> None:
    """Lo anterior más lo que necesita `rutas/capturas.py`."""
    instalar_dobles()
    _doble_auth()
    _doble_audio()


def _aplicar(expresion: str, item: dict, valores: dict, nombres: dict) -> None:
    """Aplica las expresiones `ADD` y `SET` que escribe datos/capturas.py."""
    verbo, _, cuerpo = expresion.partition(" ")
    if verbo == "ADD":
        atributo, token = cuerpo.split()
        actual = int(item.get(atributo, {"N": "0"})["N"])
        item[atributo] = {"N": str(actual + int(valores[token]["N"]))}
        return
    if verbo == "SET":
        for asignacion in cuerpo.split(", "):
            atributo, token = (parte.strip() for parte in asignacion.split("="))
            item[nombres.get(atributo, atributo)] = valores[token]
        return
    raise AssertionError(f"expresión que el doble no entiende: {expresion}")


class Almacen:
    """DynamoDB de mentira para la tabla Capturas: ítems en memoria y solo las
    expresiones y condiciones que escribe `datos/capturas.py`."""

    def __init__(self) -> None:
        self.tablas: dict[str, dict[str, dict]] = {}
        self.consultas: list[tuple[str, dict]] = []

    def conectar(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Reemplaza las funciones de `datos/dynamo.py` por las del almacén."""
        modulo = importlib.import_module("huellita_api.datos.dynamo")
        for nombre in ("poner", "obtener", "actualizar", "borrar", "consultar_todo"):
            monkeypatch.setattr(modulo, nombre, getattr(self, nombre))

    def filas(self, tabla: str) -> dict[str, dict]:
        return self.tablas.setdefault(tabla, {})

    def fila(self, tabla: str, id_captura: str) -> dict | None:
        return self.filas(tabla).get(id_captura)

    def poner(self, tabla: str, item: dict, condicion: str | None = None) -> bool:
        if condicion is not None and not CONDICIONES[condicion](item, {}):
            return False
        self.filas(tabla)[item["id_captura"]["S"]] = dict(item)
        return True

    def obtener(self, tabla: str, clave: dict) -> dict | None:
        item = self.fila(tabla, clave["id_captura"]["S"])
        return dict(item) if item is not None else None

    def borrar(self, tabla: str, clave: dict) -> None:
        self.filas(tabla).pop(clave["id_captura"]["S"], None)

    def actualizar(
        self,
        tabla: str,
        clave: dict,
        expresion: str,
        valores: dict | None = None,
        condicion: str | None = None,
        nombres: dict | None = None,
    ) -> dict | None:
        id_captura = clave["id_captura"]["S"]
        actual = self.fila(tabla, id_captura) or {}
        if condicion is not None and not CONDICIONES[condicion](actual, valores or {}):
            return None
        item = dict(actual) if actual else dict(clave)
        _aplicar(expresion, item, valores or {}, nombres or {})
        self.filas(tabla)[id_captura] = item
        return dict(item)

    def consultar_todo(self, tabla: str, **parametros: object) -> list[dict]:
        self.consultas.append((tabla, dict(parametros)))
        valores = parametros.get("ExpressionAttributeValues", {})
        buscada = valores.get(":sk") if isinstance(valores, dict) else None
        items = [item for item in self.filas(tabla).values() if item.get("sala_key") == buscada]
        return sorted(items, key=lambda item: item.get("creada_en", {}).get("S", ""))


instalar_dobles()

capturas = importlib.import_module("huellita_api.datos.capturas")
errores = importlib.import_module("huellita_api.errores")


@pytest.fixture
def cfg() -> Config:
    return cfg_de_prueba()


@pytest.fixture
def almacen(monkeypatch: pytest.MonkeyPatch) -> Almacen:
    doble = Almacen()
    doble.conectar(monkeypatch)
    return doble


def crear(cfg: Config, id_captura: str = ID, sala_id: str = "SG-A", **extra: object) -> None:
    """Fila de captura nueva, con los valores de la demo."""
    datos: dict = {
        "sala_id": sala_id,
        "autor_id": "EDU-0001",
        "formato": "texto",
        "creada_en": CREADA_EN,
        "dia": DIA,
    }
    datos.update(extra)
    capturas.crear_fila(cfg, id_captura=id_captura, **datos)


def test_el_contador_del_dia_es_un_item_sin_sala_key(cfg: Config, almacen: Almacen) -> None:
    capturas.reservar_cupo_del_dia(cfg, "SG-A", DIA)

    item = almacen.fila(cfg.tabla_capturas, "CONTADOR#2026-10-15")
    assert capturas.id_contador(DIA) == "CONTADOR#2026-10-15"
    assert item == {"id_captura": {"S": "CONTADOR#2026-10-15"}, "total": {"N": "1"}}
    assert "sala_key" not in item  # así queda fuera del índice porSala


def test_el_cupo_se_reserva_sumando_y_al_pasarse_responde_tope_diario(almacen: Almacen) -> None:
    cfg = cfg_de_prueba(MAX_CAPTURAS_DIA="2")

    assert capturas.reservar_cupo_del_dia(cfg, "SG-A", DIA) == 1
    assert capturas.reservar_cupo_del_dia(cfg, "SG-B", DIA) == 2
    with pytest.raises(errores.ErrorApi) as falla:
        capturas.reservar_cupo_del_dia(cfg, "SG-A", DIA)

    assert falla.value.codigo == "tope_diario"
    assert capturas.contar_del_dia(cfg, "SG-A", DIA) == 2  # el rechazo no suma


def test_el_tope_es_por_dia_asi_que_el_dia_siguiente_parte_de_cero(almacen: Almacen) -> None:
    cfg = cfg_de_prueba(MAX_CAPTURAS_DIA="2")
    capturas.reservar_cupo_del_dia(cfg, "SG-A", DIA)
    capturas.reservar_cupo_del_dia(cfg, "SG-A", DIA)

    assert capturas.reservar_cupo_del_dia(cfg, "SG-A", "2026-10-16") == 1


def test_contar_del_dia_sin_contador_es_cero(cfg: Config, almacen: Almacen) -> None:
    assert capturas.contar_del_dia(cfg, "SG-A", DIA) == 0


def test_la_fila_nueva_queda_enviando_y_con_los_atributos_del_spec(cfg: Config, almacen: Almacen) -> None:
    crear(cfg, nino_id_sugerido="NIN-0003", mime_type="audio/webm", formato="audio")

    item = almacen.fila(cfg.tabla_capturas, ID)
    assert item["sala_key"] == {"S": "JAR-0001#SG-A"}
    assert item["creada_en"] == {"S": CREADA_EN}
    assert item["id_jardin"] == {"S": "JAR-0001"}
    assert item["sala_grupo"] == {"S": "SG-A"}
    assert item["autor_id"] == {"S": "EDU-0001"}
    assert item["formato"] == {"S": "audio"}
    assert item["estado_envio"] == {"S": "enviando"}
    assert item["actualizado_en"] == {"S": CREADA_EN}
    assert item["nino_id_sugerido"] == {"S": "NIN-0003"}
    assert item["mime_type"] == {"S": "audio/webm"}
    assert "estado_final" not in item
    assert "archivada" not in item


def test_la_fila_nueva_sin_opcionales_no_guarda_esos_atributos(cfg: Config, almacen: Almacen) -> None:
    crear(cfg)

    item = almacen.fila(cfg.tabla_capturas, ID)
    assert "nino_id_sugerido" not in item
    assert "mime_type" not in item
    assert "texto_extraido" not in item


def test_marcar_envio_deja_el_estado_y_la_marca_de_tiempo(cfg: Config, almacen: Almacen) -> None:
    crear(cfg)

    capturas.marcar_envio(cfg, ID, "enviada")

    item = almacen.fila(cfg.tabla_capturas, ID)
    assert item["estado_envio"] == {"S": "enviada"}
    assert item["actualizado_en"]["S"] != CREADA_EN


def test_marcar_envio_guarda_el_trabajo_del_transcriptor(cfg: Config, almacen: Almacen) -> None:
    crear(cfg, formato="audio")

    capturas.marcar_envio(cfg, ID, "enviada", id_trabajo=f"tr-{ID}")
    capturas.marcar_envio(cfg, ID, "enviada", texto_entregado=True)

    item = almacen.fila(cfg.tabla_capturas, ID)
    assert item["id_trabajo"] == {"S": f"tr-{ID}"}
    assert item["texto_entregado"] == {"BOOL": True}


def test_marcar_envio_solo_acepta_los_tres_estados(cfg: Config, almacen: Almacen) -> None:
    crear(cfg)

    with pytest.raises(ValueError):
        capturas.marcar_envio(cfg, ID, "mandando")


def test_marcar_final_cierra_la_captura(cfg: Config, almacen: Almacen) -> None:
    crear(cfg)

    capturas.marcar_final(cfg, ID, "lista", texto_extraido="apiló cinco cubos")

    item = almacen.fila(cfg.tabla_capturas, ID)
    assert item["estado_final"] == {"S": "lista"}
    assert item["texto_extraido"] == {"S": "apiló cinco cubos"}


def test_marcar_final_solo_acepta_lista_o_error(cfg: Config, almacen: Almacen) -> None:
    crear(cfg)

    with pytest.raises(ValueError):
        capturas.marcar_final(cfg, ID, "procesando")


def test_guardar_texto_deja_el_texto_extraido(cfg: Config, almacen: Almacen) -> None:
    crear(cfg)

    capturas.guardar_texto(cfg, ID, "Nayara apiló cinco cubos y dijo torre")

    item = almacen.fila(cfg.tabla_capturas, ID)
    assert item["texto_extraido"] == {"S": "Nayara apiló cinco cubos y dijo torre"}


def test_archivar_marca_la_fila_y_la_deja_lista(cfg: Config, almacen: Almacen) -> None:
    crear(cfg)

    assert capturas.archivar(cfg, ID, "SG-A") is True

    item = almacen.fila(cfg.tabla_capturas, ID)
    assert item["archivada"] == {"BOOL": True}
    assert item["estado_final"] == {"S": "lista"}


def test_archivar_una_captura_de_otra_sala_no_hace_nada(cfg: Config, almacen: Almacen) -> None:
    crear(cfg)

    assert capturas.archivar(cfg, ID, "SG-B") is False
    assert "archivada" not in almacen.fila(cfg.tabla_capturas, ID)


def test_archivar_una_captura_que_no_existe_no_hace_nada(cfg: Config, almacen: Almacen) -> None:
    assert capturas.archivar(cfg, ID, "SG-A") is False
    assert almacen.fila(cfg.tabla_capturas, ID) is None


def test_obtener_devuelve_la_fila(cfg: Config, almacen: Almacen) -> None:
    crear(cfg)

    assert capturas.obtener(cfg, ID)["id_captura"] == {"S": ID}
    assert capturas.obtener(cfg, "CAP-00000000000000000000000000") is None


def test_leer_de_sala_usa_el_indice_y_deja_fuera_los_contadores(cfg: Config, almacen: Almacen) -> None:
    capturas.reservar_cupo_del_dia(cfg, "SG-A", DIA)
    crear(cfg)
    crear(cfg, id_captura="CAP-01M503FN5942S3MNAFA14C07AR", creada_en="2026-10-15T15:00:00-03:00")
    crear(cfg, id_captura="CAP-01M503FN5942S3MNAFA14C07AS", sala_id="SG-B")

    filas = capturas.leer_de_sala(cfg, "SG-A")

    assert [fila["id_captura"]["S"] for fila in filas] == [ID, "CAP-01M503FN5942S3MNAFA14C07AR"]
    tabla, parametros = almacen.consultas[-1]
    assert tabla == cfg.tabla_capturas
    assert parametros["IndexName"] == "porSala"
    assert parametros["KeyConditionExpression"] == "sala_key = :sk"
    assert parametros["ExpressionAttributeValues"] == {":sk": {"S": "JAR-0001#SG-A"}}
