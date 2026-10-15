"""Implementacion DynamoDB de la interfaz Datos (tareas 8 y 8c).

Tablas (design.md):
- Jardines:     PK id_jardin
- Educadoras:   PK id_educadora                 GSI porJardin (PK id_jardin)
- Ninos:        PK id_jardin, SK id_nino        GSI porJardin (PK id_jardin)
- Registros:    PK id_captura                   GSI porSala  (PK sala_key, SK subido_en)
- Observaciones: PK id_captura, SK id_obs       GSI porNino  (PK id_nino,  SK orden)
                                                 GSI porSala  (PK sala_key, SK orden)

Mismo contrato que DatosLocal, para que el pipeline no sepa de donde salen los datos.
No se escribe el texto de las notas en logs (requirements 5): aqui solo se persiste.

Las claves derivadas (`sala_key`, `orden`) y los timestamps viven en funciones puras
module-level para poder testearlas sin AWS.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import boto3

from .config import config
from .modelos import Educadora, Jardin, Nino, Observacion

# Horario de Chile continental usado para los timestamps (ISO 8601 con zona -03:00).
TZ_CHILE = timezone(timedelta(hours=-3))


# --- Claves derivadas y timestamps (puros, testeables sin AWS) ---

def sala_key(id_jardin: str, sala_grupo: str) -> str:
    """Clave de particion de sala: '{id_jardin}#{sala_grupo}'."""
    return f"{id_jardin}#{sala_grupo}"


def clave_orden(fecha: str, creado_en: str) -> str:
    """SK de los GSIs porNino/porSala: '{fecha}#{creado_en}'.

    `fecha` es el dia de la observacion (de meta.json), no la fecha de subida: asi
    "las ultimas N de la sala" son las mas recientes observadas (design.md).
    """
    return f"{fecha}#{creado_en}"


def ahora_iso() -> str:
    """Timestamp actual en ISO 8601 con zona -03:00 (p. ej. '2026-10-15T12:34:56-03:00')."""
    return datetime.now(TZ_CHILE).isoformat(timespec="seconds")


def _a_item_dynamo(valor: Any) -> Any:
    """Convierte un valor Python a algo que DynamoDB acepta.

    - float -> Decimal (DynamoDB no acepta float).
    - date/datetime -> isoformat.
    - dict/list -> recursivo; se omiten los None (DynamoDB no guarda null comodo).
    """
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, float):
        return Decimal(str(valor))
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    if isinstance(valor, dict):
        return {k: _a_item_dynamo(v) for k, v in valor.items() if v is not None}
    if isinstance(valor, list):
        return [_a_item_dynamo(v) for v in valor]
    return valor


def _observacion_a_item(
    obs: Observacion,
    id_captura: str,
    cabecera: dict[str, Any],
    *,
    origen: str = "app",
    creado_en: str | None = None,
) -> dict[str, Any]:
    """Serializa una Observacion a un item de la tabla Observaciones.

    `cabecera` trae los datos de captura comunes (fecha, id_educadora, id_jardin,
    sala_grupo). Agrega las claves derivadas: `sala_key`, `orden`, `origen`, `creado_en`.
    """
    cuerpo = json.loads(obs.model_dump_json(exclude_none=True))
    creado = creado_en or ahora_iso()
    fecha = str(cabecera.get("fecha", ""))
    id_jardin = str(cabecera.get("id_jardin", ""))
    grupo = str(cabecera.get("sala_grupo", ""))
    item = {
        "id_captura": id_captura,
        "id_obs": obs.id_obs,
        "creado_en": creado,
        "origen": origen,
        "sala_key": sala_key(id_jardin, grupo),
        "orden": clave_orden(fecha, creado),
        **cabecera,
        **cuerpo,
    }
    return _a_item_dynamo(item)


class DatosDynamo:
    """Acceso a datos sobre DynamoDB."""

    def __init__(self) -> None:
        faltan = [
            nombre
            for nombre, valor in (
                ("TABLA_EDUCADORAS", config.tabla_educadoras),
                ("TABLA_NINOS", config.tabla_ninos),
                ("TABLA_OBSERVACIONES", config.tabla_observaciones),
            )
            if not valor
        ]
        if faltan:
            raise ValueError(f"faltan variables de entorno: {', '.join(faltan)}")
        self._ddb = boto3.resource("dynamodb", region_name=config.region)
        self._t_educadoras = self._ddb.Table(config.tabla_educadoras)
        self._t_ninos = self._ddb.Table(config.tabla_ninos)
        self._t_observaciones = self._ddb.Table(config.tabla_observaciones)
        # Opcionales: solo se usan cuando el flujo S3 los necesita.
        self._t_jardines = self._ddb.Table(config.tabla_jardines) if config.tabla_jardines else None
        self._t_registros = self._ddb.Table(config.tabla_registros) if config.tabla_registros else None

    # --- Lectura ---

    def jardin(self, id_jardin: str) -> Jardin | None:
        if self._t_jardines is None:
            return None
        item = self._t_jardines.get_item(Key={"id_jardin": id_jardin}).get("Item")
        if not item:
            return None
        return Jardin(
            id_jardin=item["id_jardin"],
            nombre_fantasia=item.get("nombre_fantasia"),
            comuna=item.get("comuna"),
            region=item.get("region"),
            numero_salas=_int_o_none(item.get("numero_salas")),
            numero_educadoras=_int_o_none(item.get("numero_educadoras")),
            salas=list(item.get("salas", [])),
        )

    def educadora(self, id_educadora: str) -> Educadora | None:
        item = self._t_educadoras.get_item(Key={"id_educadora": id_educadora}).get("Item")
        if not item:
            return None
        return Educadora(
            id_educadora=item["id_educadora"],
            id_jardin=item["id_jardin"],
            rol=item.get("rol"),
        )

    def educadoras_de_jardin(self, id_jardin: str) -> list[Educadora]:
        """Lista educadoras de un jardin via GSI porJardin."""
        from boto3.dynamodb.conditions import Key

        salida: list[Educadora] = []
        for item in self._query_todo(
            self._t_educadoras,
            IndexName="porJardin",
            KeyConditionExpression=Key("id_jardin").eq(id_jardin),
        ):
            salida.append(
                Educadora(
                    id_educadora=item["id_educadora"],
                    id_jardin=item["id_jardin"],
                    rol=item.get("rol"),
                )
            )
        return salida

    def ninos_de_jardin(self, id_jardin: str) -> list[Nino]:
        from boto3.dynamodb.conditions import Key

        ninos: list[Nino] = []
        for item in self._query_todo(
            self._t_ninos, KeyConditionExpression=Key("id_jardin").eq(id_jardin)
        ):
            ninos.append(
                Nino(
                    id_nino=item["id_nino"],
                    id_jardin=item["id_jardin"],
                    sala_grupo=item["sala_grupo"],
                    nombre=item["nombre"],
                    apodos=list(item.get("apodos", [])),
                    fecha_nacimiento=date.fromisoformat(item["fecha_nacimiento"]),
                    fecha_ingreso=date.fromisoformat(item["fecha_ingreso"]),
                )
            )
        return ninos

    # --- Escritura ---

    def upsert_registro(
        self,
        id_captura: str,
        campos: dict[str, Any],
        conservar_si_existe: set[str] | None = None,
    ) -> None:
        """Upsert de la tabla Registros (meta.json y texto.json llegan en cualquier orden).

        Escribe los campos presentes en `campos` (mas `actualizado_en`). Los campos listados
        en `conservar_si_existe` se escriben con `if_not_exists(campo, :valor)`: solo toman el
        valor nuevo si el atributo aun no existe, para no pisar un estado mas avanzado cuando
        `meta.json` llega despues de `texto.json` (S3 no garantiza el orden). Si falta la
        tabla, no hace nada (pruebas directas).
        """
        if self._t_registros is None:
            return
        conservar = conservar_si_existe or set()
        valores = {k: v for k, v in campos.items() if v is not None}
        valores.setdefault("actualizado_en", ahora_iso())
        valores = _a_item_dynamo(valores)

        nombres: dict[str, str] = {}
        atributos: dict[str, Any] = {}
        asignaciones: list[str] = []
        for i, (clave, valor) in enumerate(valores.items()):
            n, a = f"#c{i}", f":v{i}"
            nombres[n] = clave
            atributos[a] = valor
            if clave in conservar:
                # No pisar si ya existe (p. ej. estado mas avanzado o subido_en previo).
                asignaciones.append(f"{n} = if_not_exists({n}, {a})")
            else:
                asignaciones.append(f"{n} = {a}")

        self._t_registros.update_item(
            Key={"id_captura": id_captura},
            UpdateExpression="SET " + ", ".join(asignaciones),
            ExpressionAttributeNames=nombres,
            ExpressionAttributeValues=atributos,
        )

    def guardar_observaciones(
        self,
        observaciones: list[Observacion],
        id_captura: str = "",
        cabecera: dict[str, Any] | None = None,
        *,
        origen: str = "app",
    ) -> None:
        """Guarda las observaciones (BatchWrite) y actualiza Ninos por cada niño/a."""
        cab = cabecera or {}
        creado_en = ahora_iso()
        with self._t_observaciones.batch_writer() as batch:
            for obs in observaciones:
                batch.put_item(
                    Item=_observacion_a_item(obs, id_captura, cab, origen=origen, creado_en=creado_en)
                )
        self._actualizar_ninos(observaciones, cab)

    def _actualizar_ninos(self, observaciones: list[Observacion], cabecera: dict[str, Any]) -> None:
        """UpdateItem en Ninos: ultima_obs_fecha siempre; ultimo_nivel/_fecha solo si hay nivel.

        Por cada niño/a identificado se queda con la observacion de fecha mas reciente.
        """
        id_jardin = str(cabecera.get("id_jardin", ""))
        fecha = str(cabecera.get("fecha", ""))
        if not id_jardin or not fecha:
            return
        # Deduplicar por niño: ¿alguna observacion suya trajo nivel?
        con_nivel: dict[str, bool] = {}
        for obs in observaciones:
            if not obs.id_nino:
                continue
            con_nivel[obs.id_nino] = con_nivel.get(obs.id_nino, False) or (obs.nivel is not None)
        for id_nino, tiene_nivel in con_nivel.items():
            self._actualizar_nino(id_jardin, id_nino, fecha, tiene_nivel, observaciones)

    def _actualizar_nino(
        self,
        id_jardin: str,
        id_nino: str,
        fecha: str,
        tiene_nivel: bool,
        observaciones: list[Observacion],
    ) -> None:
        nombres = {"#f": "ultima_obs_fecha"}
        valores: dict[str, Any] = {":f": fecha}
        sets = ["#f = :f"]
        if tiene_nivel:
            nivel = next(
                (o.nivel for o in observaciones if o.id_nino == id_nino and o.nivel is not None),
                None,
            )
            if nivel is not None:
                nombres["#n"] = "ultimo_nivel"
                nombres["#nf"] = "ultimo_nivel_fecha"
                valores[":n"] = nivel
                valores[":nf"] = fecha
                sets.append("#n = :n")
                sets.append("#nf = :nf")
        self._t_ninos.update_item(
            Key={"id_jardin": id_jardin, "id_nino": id_nino},
            UpdateExpression="SET " + ", ".join(sets),
            ExpressionAttributeNames=nombres,
            ExpressionAttributeValues=valores,
        )

    # --- util ---

    @staticmethod
    def _query_todo(tabla: Any, **kwargs: Any):
        """Itera todas las paginas de un query y produce items."""
        while True:
            resp = tabla.query(**kwargs)
            yield from resp.get("Items", [])
            if "LastEvaluatedKey" not in resp:
                break
            kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]


def _int_o_none(valor: Any) -> int | None:
    if valor is None:
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None
