"""Pruebas de `datos/audio.py` con un transcriptor falso: ni red, ni S3, ni DynamoDB.

Cubre lo que pide la tarea 7: el envío, los errores del transcriptor traducidos, la consulta
de cada estado, el reintento de `texto.json`, el tope de 4 MiB, el base64 inválido y que la
clave de API nunca aparezca en los logs.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from types import SimpleNamespace

import pytest

from huellita_api import errores, s3
from huellita_api.datos import audio

CLAVE = "clave-secreta-de-prueba-9f3a4c"
TEXTO = "Nayara apiló cinco cubos y dijo torre"
SALA_KEY = "JAR-0001#SG-A"


def fila(id_captura: str, **atributos) -> dict:
    """Una fila de Capturas de audio, como la deja `datos/capturas.crear_fila`."""
    base = {
        "id_captura": id_captura,
        "sala_key": SALA_KEY,
        "sala_grupo": "SG-A",
        "id_jardin": "JAR-0001",
        "autor_id": "EDU-0001",
        "creada_en": "2026-10-15T14:50:00-03:00",
        "formato": "audio",
        "estado_envio": "enviada",
        "id_trabajo": f"tr-{id_captura}",
    }
    base.update(atributos)
    item: dict = {}
    for clave, valor in base.items():
        item[clave] = {"BOOL": valor} if isinstance(valor, bool) else {"S": valor}
    return item


class FalsoS3:
    """Cliente de S3 de mentira: anota las claves y puede fallar."""

    def __init__(self) -> None:
        self.claves: list[str] = []
        self.cuerpos: dict[str, dict] = {}
        self.falla = False

    def put_object(self, **parametros: object) -> dict:
        if self.falla:
            raise RuntimeError("S3 no responde")
        clave = str(parametros["Key"])
        self.claves.append(clave)
        self.cuerpos[clave] = json.loads(parametros["Body"].decode("utf-8"))  # type: ignore[union-attr]
        return {}


@pytest.fixture
def falso_s3(monkeypatch: pytest.MonkeyPatch) -> FalsoS3:
    doble = FalsoS3()
    monkeypatch.setattr(s3, "cliente", lambda: doble)
    return doble


@pytest.fixture
def almacen(monkeypatch: pytest.MonkeyPatch, cfg):
    """Doble de `datos/capturas`: anota las escrituras y entrega las filas de la sala."""
    doble = SimpleNamespace(filas=[], envios=[], finales=[], textos=[], sala=None)

    def leer_de_sala(_cfg, sala_id: str) -> list[dict]:
        doble.sala = sala_id
        return list(doble.filas)

    def marcar_envio(_cfg, id_captura, estado, *, id_trabajo=None, texto_entregado=None) -> None:
        doble.envios.append((id_captura, estado, id_trabajo, texto_entregado))

    def marcar_final(_cfg, id_captura, estado, *, texto_extraido=None) -> None:
        doble.finales.append((id_captura, estado, texto_extraido))

    def guardar_texto(_cfg, id_captura, texto) -> None:
        doble.textos.append((id_captura, texto))

    monkeypatch.setattr(audio.capturas, "leer_de_sala", leer_de_sala)
    monkeypatch.setattr(audio.capturas, "marcar_envio", marcar_envio)
    monkeypatch.setattr(audio.capturas, "marcar_final", marcar_final)
    monkeypatch.setattr(audio.capturas, "guardar_texto", guardar_texto)
    return doble


@pytest.fixture
def transcriptor(monkeypatch: pytest.MonkeyPatch):
    """Reemplaza `transcriptor.iniciar` y `transcriptor.consultar` sin tocar la red."""

    def instalar(*, iniciar=None, consultar=None):
        doble = SimpleNamespace(
            ErrorTranscriptor=audio.transcriptor.ErrorTranscriptor,
            enviados=[],
            pedidos=[],
        )

        def _iniciar(cfg, id_captura: str, audio_base64: str) -> str:
            doble.enviados.append((id_captura, audio_base64))
            if iniciar is None:
                return f"tr-{id_captura}"
            return iniciar(cfg, id_captura, audio_base64)

        def _consultar(cfg, id_trabajo: str) -> dict:
            doble.pedidos.append(id_trabajo)
            return {} if consultar is None else consultar(cfg, id_trabajo)

        doble.iniciar = _iniciar
        doble.consultar = _consultar
        monkeypatch.setattr(audio, "transcriptor", doble)
        return doble

    return instalar


# --- decodificar ------------------------------------------------------------------------


def test_el_tope_de_audio_es_de_4_mib() -> None:
    assert audio.MAX_BYTES_AUDIO == 4194304
    assert audio.MAX_CONSULTAS_PARALELAS == 4


def test_decodificar_devuelve_los_bytes_de_la_grabacion() -> None:
    assert audio.decodificar("QUJDRA==") == b"ABCD"


@pytest.mark.parametrize("valor", ["no-es-base64!!", "QQ", "###", "QUJDR A=="])
def test_un_base64_invalido_es_422(valor: str) -> None:
    with pytest.raises(errores.ErrorApi) as falla:
        audio.decodificar(valor)

    assert falla.value.codigo == "base64_invalido"
    assert errores.estado_http(falla.value.codigo) == 422


def test_el_audio_de_mas_de_4_mib_es_413() -> None:
    import base64 as b64

    grande = b64.b64encode(b"\x00" * (audio.MAX_BYTES_AUDIO + 1)).decode("ascii")

    with pytest.raises(errores.ErrorApi) as falla:
        audio.decodificar(grande)

    assert falla.value.codigo == "audio_demasiado_grande"
    assert errores.estado_http(falla.value.codigo) == 413


def test_el_audio_de_4_mib_justos_sirve() -> None:
    import base64 as b64

    justo = b64.b64encode(b"\x00" * audio.MAX_BYTES_AUDIO).decode("ascii")

    assert len(audio.decodificar(justo)) == audio.MAX_BYTES_AUDIO


# --- enviar -----------------------------------------------------------------------------


def test_enviar_manda_el_audio_y_guarda_el_trabajo(cfg, almacen, transcriptor) -> None:
    doble = transcriptor()

    assert audio.enviar(cfg, "CAP-NUEVA", "QUJDRA==") == "tr-CAP-NUEVA"

    assert doble.enviados == [("CAP-NUEVA", "QUJDRA==")]
    assert almacen.envios == [("CAP-NUEVA", "enviada", "tr-CAP-NUEVA", None)]


@pytest.mark.parametrize(
    ("codigo", "estado"),
    [
        ("audio_demasiado_grande", 413),
        ("formato_audio_no_soportado", 415),
        ("servicio_saturado", 503),
        ("transcriptor_caido", 502),
    ],
)
def test_enviar_traduce_los_errores_del_transcriptor(
    cfg, almacen, transcriptor, codigo: str, estado: int
) -> None:
    def iniciar(_cfg, _id, _b64):
        raise audio.transcriptor.ErrorTranscriptor(codigo)

    transcriptor(iniciar=iniciar)

    with pytest.raises(errores.ErrorApi) as falla:
        audio.enviar(cfg, "CAP-NUEVA", "QUJDRA==")

    assert falla.value.codigo == codigo
    assert errores.estado_http(falla.value.codigo) == estado
    assert almacen.envios == [("CAP-NUEVA", "error_envio", None, None)]


def test_enviar_deja_la_fila_en_error_envio_antes_de_fallar(cfg, almacen, transcriptor) -> None:
    def iniciar(_cfg, _id, _b64):
        raise audio.transcriptor.ErrorTranscriptor("servicio_saturado", 429)

    transcriptor(iniciar=iniciar)

    with pytest.raises(errores.ErrorApi):
        audio.enviar(cfg, "CAP-NUEVA", "QUJDRA==")

    assert [envio[1] for envio in almacen.envios] == ["error_envio"]
    assert errores.MENSAJES["servicio_saturado"].endswith("intenta de nuevo.")


# --- sincronizar ------------------------------------------------------------------------


def test_completado_guarda_el_texto_y_entrega_texto_json(
    cfg, almacen, transcriptor, falso_s3
) -> None:
    almacen.filas = [fila("CAP-NUEVA")]
    doble = transcriptor(consultar=lambda _cfg, _id: {"estado": "completado", "texto_completo": TEXTO})

    audio.sincronizar(cfg, "SG-A")

    assert almacen.sala == "SG-A"
    assert doble.pedidos == ["tr-CAP-NUEVA"]
    assert almacen.textos == [("CAP-NUEVA", TEXTO)]
    assert falso_s3.claves == ["capturas/CAP-NUEVA/texto.json"]
    assert falso_s3.cuerpos["capturas/CAP-NUEVA/texto.json"] == {
        "id_captura": "CAP-NUEVA",
        "fuente": "audio",
        "partes": [{"texto": TEXTO}],
    }
    assert almacen.envios == [("CAP-NUEVA", "enviada", None, True)]
    assert almacen.finales == [], "el estado final lo pone Registros, no sincronizar"


def test_el_texto_json_no_se_entrega_dos_veces(cfg, almacen, transcriptor, falso_s3) -> None:
    almacen.filas = [fila("CAP-NUEVA", texto_entregado=True)]
    transcriptor(consultar=lambda _cfg, _id: {"estado": "completado", "texto_completo": TEXTO})

    audio.sincronizar(cfg, "SG-A")

    assert almacen.textos == [("CAP-NUEVA", TEXTO)]
    assert falso_s3.claves == []
    assert almacen.envios == []


def test_fallido_deja_la_nota_en_error(cfg, almacen, transcriptor, falso_s3) -> None:
    almacen.filas = [fila("CAP-NUEVA")]
    transcriptor(consultar=lambda _cfg, _id: {"estado": "fallido", "texto_completo": None})

    audio.sincronizar(cfg, "SG-A")

    assert almacen.finales == [("CAP-NUEVA", "error", None)]
    assert almacen.textos == []
    assert falso_s3.claves == []


def test_transcribiendo_no_escribe_nada(cfg, almacen, transcriptor, falso_s3) -> None:
    almacen.filas = [fila("CAP-NUEVA")]
    transcriptor(consultar=lambda _cfg, _id: {"estado": "transcribiendo", "texto_completo": None})

    audio.sincronizar(cfg, "SG-A")

    assert (almacen.textos, almacen.finales, almacen.envios, falso_s3.claves) == ([], [], [], [])


def test_no_pregunta_por_los_audios_cerrados_ni_sin_trabajo_ni_por_el_texto(
    cfg, almacen, transcriptor
) -> None:
    almacen.filas = [
        fila("CAP-CERRADA", estado_final="lista"),
        fila("CAP-EN-ERROR", estado_final="error"),
        fila("CAP-SIN-TRABAJO", id_trabajo=""),
        fila("CAP-DE-TEXTO", formato="texto"),
    ]
    doble = transcriptor(consultar=lambda _cfg, _id: {"estado": "transcribiendo"})

    audio.sincronizar(cfg, "SG-A")

    assert doble.pedidos == []


def test_una_consulta_que_falla_no_detiene_a_las_demas(cfg, almacen, transcriptor) -> None:
    almacen.filas = [fila("CAP-UNA"), fila("CAP-OTRA")]

    def consultar(_cfg, id_trabajo: str) -> dict:
        if id_trabajo == "tr-CAP-UNA":
            raise TimeoutError("el transcriptor no contestó")
        return {"estado": "completado", "texto_completo": "la otra sí"}

    transcriptor(consultar=consultar)

    audio.sincronizar(cfg, "SG-A")

    assert almacen.textos == [("CAP-OTRA", "la otra sí")]


def test_una_escritura_que_falla_no_voltea_la_sincronizacion(
    cfg, almacen, transcriptor, falso_s3
) -> None:
    almacen.filas = [fila("CAP-NUEVA")]
    falso_s3.falla = True
    transcriptor(consultar=lambda _cfg, _id: {"estado": "completado", "texto_completo": TEXTO})

    audio.sincronizar(cfg, "SG-A")  # no lanza

    assert almacen.textos == [("CAP-NUEVA", TEXTO)]
    assert almacen.envios == [], "sin texto.json no se marca texto_entregado"


def test_si_no_se_pueden_leer_las_capturas_la_sincronizacion_no_lanza(
    cfg, monkeypatch: pytest.MonkeyPatch, transcriptor
) -> None:
    def leer_de_sala(_cfg, _sala):
        raise RuntimeError("ResourceNotFoundException: Table: Capturas")

    monkeypatch.setattr(audio.capturas, "leer_de_sala", leer_de_sala)
    doble = transcriptor()

    audio.sincronizar(cfg, "SG-A")

    assert doble.pedidos == []


def test_las_consultas_van_de_a_cuatro(cfg, almacen, transcriptor) -> None:
    almacen.filas = [fila(f"CAP-{numero:02d}") for numero in range(12)]
    candado = threading.Lock()
    estado = {"ahora": 0, "tope": 0}

    def consultar(_cfg, _id_trabajo: str) -> dict:
        with candado:
            estado["ahora"] += 1
            estado["tope"] = max(estado["tope"], estado["ahora"])
        time.sleep(0.01)
        with candado:
            estado["ahora"] -= 1
        return {"estado": "transcribiendo"}

    transcriptor(consultar=consultar)

    audio.sincronizar(cfg, "SG-A")

    assert estado["tope"] <= audio.MAX_CONSULTAS_PARALELAS == 4
    assert estado["tope"] > 1, "las consultas tienen que ir en paralelo"


def test_sin_audios_pendientes_no_consulta_nada(cfg, almacen, transcriptor) -> None:
    doble = transcriptor()

    audio.sincronizar(cfg, "SG-A")

    assert doble.pedidos == []


# --- la clave de API nunca sale ---------------------------------------------------------


def test_la_clave_nunca_aparece_en_los_logs_ni_en_los_errores(
    cfg, almacen, transcriptor, caplog: pytest.LogCaptureFixture
) -> None:
    """Peor caso: una falla que lleva la clave en su mensaje. Ni el log ni la respuesta la ven.

    `caplog.text` trae también las trazas, así que acá se cae cualquier `exc_info` que
    arrastre el mensaje de la excepción.
    """
    caplog.set_level(logging.DEBUG)
    almacen.filas = [fila("CAP-UNA"), fila("CAP-OTRA")]

    def consultar(_cfg, _id_trabajo: str) -> dict:
        raise RuntimeError(f"403 Forbidden con x-api-key={CLAVE}")

    def iniciar(_cfg, _id, _b64):
        raise audio.transcriptor.ErrorTranscriptor("transcriptor_caido", 502)

    transcriptor(consultar=consultar, iniciar=iniciar)

    audio.sincronizar(cfg, "SG-A")
    with pytest.raises(errores.ErrorApi) as falla:
        audio.enviar(cfg, "CAP-NUEVA", "QUJDRA==")

    assert CLAVE not in str(falla.value)
    assert CLAVE not in falla.value.mensaje
    assert caplog.records, "se esperaban logs que revisar"
    assert CLAVE not in caplog.text
    assert "RuntimeError" in caplog.text, "el tipo de la falla sí queda, para poder depurar"


def test_tampoco_se_filtra_la_clave_al_leer_las_capturas(
    cfg, monkeypatch: pytest.MonkeyPatch, transcriptor, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)

    def leer_de_sala(_cfg, _sala):
        raise RuntimeError(f"AccessDenied con x-api-key={CLAVE}")

    monkeypatch.setattr(audio.capturas, "leer_de_sala", leer_de_sala)
    transcriptor()

    audio.sincronizar(cfg, "SG-A")

    assert caplog.records
    assert CLAVE not in caplog.text
