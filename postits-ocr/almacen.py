"""Almacén de capturas: S3 (Lambda) o memoria (pruebas locales).

Interfaz común:
    listar(prefijo) -> {clave: tamaño}
    metadatos(clave) -> {"tamano", "tipo", "meta", "etag"} | None        (None con 404/403)
    leer(clave, max_bytes=None) -> bytes        ObjetoNoEncontrado / ObjetoDemasiadoGrande
    leer_json(clave) -> object                  json.loads de hasta 1 MB (como recursos.leer_json_s3)
    guardar(clave, datos, tipo, *, metadatos=None, solo_si_no_existe=False) -> bool
        False si solo_si_no_existe y el objeto ya existía (412/409 de la escritura condicional)
    url(clave, expira=3600) -> str
    escritura_condicional: bool

Todo objeto escrito lleva el metadato origen=postits-ocr.
"""

from __future__ import annotations

import json
import logging
import threading

log = logging.getLogger("postits.almacen")

ORIGEN = "postits-ocr"
MAX_JSON = 1024 * 1024


class ObjetoNoEncontrado(LookupError):
    pass


class ObjetoDemasiadoGrande(ValueError):
    pass


def _codigo(error) -> str:
    return str(getattr(error, "response", {}).get("Error", {}).get("Code", ""))


class AlmacenS3:
    def __init__(self, bucket: str, cliente=None):
        self.bucket = bucket
        if cliente is None:
            import boto3
            from botocore.config import Config

            cliente = boto3.client("s3", config=Config(signature_version="s3v4",
                                                       retries={"mode": "standard", "max_attempts": 3},
                                                       connect_timeout=5, read_timeout=30))
        self.cliente = cliente
        try:
            miembros = cliente.meta.service_model.operation_model("PutObject").input_shape.members
            self.escritura_condicional = "IfNoneMatch" in miembros
        except Exception:
            self.escritura_condicional = False

    def listar(self, prefijo: str) -> dict[str, int]:
        claves: dict[str, int] = {}
        for pagina in self.cliente.get_paginator("list_objects_v2").paginate(Bucket=self.bucket, Prefix=prefijo):
            for obj in pagina.get("Contents", []):
                claves[obj["Key"]] = int(obj.get("Size", 0))
        return claves

    def metadatos(self, clave: str) -> dict | None:
        from botocore.exceptions import ClientError

        try:
            r = self.cliente.head_object(Bucket=self.bucket, Key=clave)
        except ClientError as e:
            if _codigo(e) in ("404", "403", "NoSuchKey", "NotFound", "AccessDenied"):
                return None
            raise
        return {"tamano": int(r.get("ContentLength", 0)), "tipo": r.get("ContentType"),
                "meta": {k.lower(): v for k, v in (r.get("Metadata") or {}).items()}, "etag": r.get("ETag")}

    def leer(self, clave: str, max_bytes: int | None = None) -> bytes:
        from botocore.exceptions import ClientError

        try:
            r = self.cliente.get_object(Bucket=self.bucket, Key=clave)
        except ClientError as e:
            if _codigo(e) in ("404", "403", "NoSuchKey", "NotFound", "AccessDenied"):
                raise ObjetoNoEncontrado(clave) from None
            raise
        cuerpo = r["Body"]
        try:
            if max_bytes is not None and int(r.get("ContentLength", 0)) > max_bytes:
                raise ObjetoDemasiadoGrande(clave)
            return cuerpo.read()
        finally:
            cuerpo.close()

    def leer_json(self, clave: str):
        return json.loads(self.leer(clave, max_bytes=MAX_JSON))

    def guardar(self, clave: str, datos: bytes, tipo: str, *, metadatos: dict | None = None,
                solo_si_no_existe: bool = False) -> bool:
        from botocore.exceptions import ClientError

        argumentos = {"Bucket": self.bucket, "Key": clave, "Body": datos, "ContentType": tipo,
                      "Metadata": {"origen": ORIGEN, **(metadatos or {})}}
        if solo_si_no_existe and self.escritura_condicional:
            argumentos["IfNoneMatch"] = "*"
        try:
            self.cliente.put_object(**argumentos)
        except ClientError as e:
            if solo_si_no_existe and _codigo(e) in ("PreconditionFailed", "412", "ConditionalRequestConflict", "409"):
                return False
            raise
        return True

    def url(self, clave: str, expira: int = 3600) -> str:
        return self.cliente.generate_presigned_url("get_object", Params={"Bucket": self.bucket, "Key": clave},
                                                   ExpiresIn=expira)


class AlmacenMemoria:
    """Almacén en memoria para pruebas locales (sin AWS)."""

    escritura_condicional = True

    def __init__(self):
        self.objetos: dict[str, tuple[bytes, str, dict]] = {}
        self.escrituras: list[str] = []
        self._candado = threading.Lock()

    def poner(self, clave: str, datos: bytes, tipo: str = "application/octet-stream", meta: dict | None = None):
        """Precarga un objeto sin registrarlo como escritura de la Lambda."""
        self.objetos[clave] = (datos, tipo, dict(meta or {}))

    def listar(self, prefijo: str) -> dict[str, int]:
        with self._candado:
            return {k: len(v[0]) for k, v in self.objetos.items() if k.startswith(prefijo)}

    def metadatos(self, clave: str) -> dict | None:
        with self._candado:
            if clave not in self.objetos:
                return None
            datos, tipo, meta = self.objetos[clave]
            return {"tamano": len(datos), "tipo": tipo, "meta": dict(meta), "etag": None}

    def leer(self, clave: str, max_bytes: int | None = None) -> bytes:
        with self._candado:
            if clave not in self.objetos:
                raise ObjetoNoEncontrado(clave)
            datos = self.objetos[clave][0]
        if max_bytes is not None and len(datos) > max_bytes:
            raise ObjetoDemasiadoGrande(clave)
        return datos

    def leer_json(self, clave: str):
        return json.loads(self.leer(clave, max_bytes=MAX_JSON))

    def guardar(self, clave: str, datos: bytes, tipo: str, *, metadatos: dict | None = None,
                solo_si_no_existe: bool = False) -> bool:
        with self._candado:
            if solo_si_no_existe and clave in self.objetos:
                return False
            self.objetos[clave] = (bytes(datos), tipo, {"origen": ORIGEN, **(metadatos or {})})
            self.escrituras.append(clave)
            return True

    def url(self, clave: str, expira: int = 3600) -> str:
        return f"memoria://{clave}"
