r"""Prueba de humo de Huellita en AWS: el flujo completo contra la URL publicada.

Solo biblioteca estandar. Pasos: salud, contexto, los ninos de SG-A, una nota de texto con un
nombre conocido de la sala, la espera hasta que la nota quede lista (maximo 5 minutos), confirmar
una de sus sugerencias, comprobar que quedo aceptada y devolverla a pendiente.

Uso en PowerShell, desde huellita-web:
  .\.venv\Scripts\python.exe scripts\smoke.py https://d111111abcdef8.cloudfront.net
  .\.venv\Scripts\python.exe scripts\smoke.py https://d111111abcdef8.cloudfront.net --audio "C:\ruta\nota.m4a"

No necesita credenciales de AWS: habla con el BFF por HTTPS con la cabecera X-Usuaria-Id.
Sale con 0 si todo paso y con 1 describiendo el primer paso que fallo.
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request

CABECERA_USUARIA = "X-Usuaria-Id"
USUARIA = "EDU-0001"
SALA = "SG-A"
INTERVALO = 5
ESPERA_MAX = 300
MAX_BYTES_AUDIO = 4194304
TIEMPO_LECTURA = 30
TIEMPO_ENVIO = 90
TIPOS_AUDIO = {
    ".m4a": "audio/mp4",
    ".mp4": "audio/mp4",
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
}


class Falla(Exception):
    """Un paso de la prueba de humo que no paso."""


def comprobar(condicion: object, mensaje: str) -> None:
    """Corta la prueba con el motivo si la condicion no se cumple."""
    if not condicion:
        raise Falla(mensaje)


def resumen(cuerpo: object) -> str:
    """Una linea corta del cuerpo recibido, para los mensajes de falla."""
    if isinstance(cuerpo, dict) and isinstance(cuerpo.get("error"), dict):
        detalle = cuerpo["error"]
        return f"{detalle.get('codigo')}: {detalle.get('mensaje')}"
    texto = json.dumps(cuerpo, ensure_ascii=False)
    return texto if len(texto) <= 200 else texto[:200] + "..."


def pedir(base: str, metodo: str, ruta: str, cuerpo: dict | None = None, tiempo: int = TIEMPO_LECTURA) -> tuple[int, object]:
    """Llama al BFF y devuelve (estado HTTP, cuerpo JSON). Un 4xx o 5xx no lanza."""
    cabeceras = {"Content-Type": "application/json", CABECERA_USUARIA: USUARIA}
    datos = None if cuerpo is None else json.dumps(cuerpo).encode("utf-8")
    solicitud = urllib.request.Request(base + ruta, data=datos, headers=cabeceras, method=metodo)
    try:
        with urllib.request.urlopen(solicitud, timeout=tiempo) as respuesta:
            return respuesta.status, _json(respuesta.read())
    except urllib.error.HTTPError as exc:
        return exc.code, _json(exc.read())
    except urllib.error.URLError as exc:
        raise SystemExit(f"No pude conectar con {base} ({exc.reason}). Revisa la URL publicada (salida UrlApp).") from None


def _json(crudo: bytes) -> object:
    """El cuerpo parseado; {} si no es JSON (por ejemplo, si llego index.html)."""
    try:
        return json.loads(crudo or b"{}")
    except ValueError:
        return {}


def salud(base: str) -> None:
    estado, cuerpo = pedir(base, "GET", "/api/salud")
    comprobar(
        estado == 200 and isinstance(cuerpo, dict) and cuerpo.get("estado") == "ok",
        f"GET /api/salud respondio {estado} {resumen(cuerpo)} (se esperaba 200 con estado ok en JSON)",
    )
    print("1. salud: ok")


def contexto(base: str) -> None:
    estado, cuerpo = pedir(base, "GET", "/api/contexto")
    comprobar(estado == 200 and isinstance(cuerpo, dict), f"GET /api/contexto respondio {estado} {resumen(cuerpo)}")
    jardin = cuerpo.get("jardin")
    salas = [s.get("id") for s in cuerpo.get("salas", []) if isinstance(s, dict)]
    usuarias = [u.get("id") for u in cuerpo.get("usuarias", []) if isinstance(u, dict)]
    comprobar(isinstance(jardin, dict) and jardin.get("id"), "el contexto no trae el jardin")
    comprobar(SALA in salas, f"el contexto no trae la sala {SALA} (salas: {salas})")
    comprobar(USUARIA in usuarias, f"el contexto no trae la tia {USUARIA} (usuarias: {usuarias})")
    print(f"2. contexto: {jardin.get('nombre')} con salas {', '.join(salas)} y {len(usuarias)} tias")


def elegir_nino(base: str) -> dict:
    """La lista de ninos de SG-A; devuelve el primero, que es el nombre conocido de la nota."""
    estado, cuerpo = pedir(base, "GET", f"/api/salas/{SALA}/ninos")
    comprobar(
        estado == 200 and isinstance(cuerpo, list) and cuerpo,
        f"GET /api/salas/{SALA}/ninos respondio {estado} {resumen(cuerpo)} (se esperaba una lista con ninos)",
    )
    nino = cuerpo[0]
    comprobar(isinstance(nino, dict) and nino.get("id") and nino.get("nombre"), f"el primer nino llego incompleto: {resumen(nino)}")
    comprobar(
        all(n.get("salaId") == SALA for n in cuerpo if isinstance(n, dict)),
        f"la lista de {SALA} trae ninos de otra sala",
    )
    estado, ficha = pedir(base, "GET", f"/api/ninos/{nino['id']}")
    comprobar(
        estado == 200 and isinstance(ficha, dict) and ficha.get("id") == nino["id"],
        f"GET /api/ninos/{nino['id']} respondio {estado} {resumen(ficha)}",
    )
    print(f"3. ninos de {SALA}: {len(cuerpo)}; para la nota usamos a {nino['nombre']} ({nino['id']})")
    return nino


def crear_nota(base: str, nombre: str) -> str:
    texto = f"{nombre} apiló cinco cubos y dijo torre"
    estado, cuerpo = pedir(
        base,
        "POST",
        "/api/capturas",
        {"salaId": SALA, "autorId": USUARIA, "formato": "texto", "texto": texto},
        TIEMPO_ENVIO,
    )
    comprobar(estado == 201, f"POST /api/capturas respondio {estado} {resumen(cuerpo)} (se esperaba 201)")
    evidencia = cuerpo.get("evidencia") if isinstance(cuerpo, dict) else None
    comprobar(isinstance(evidencia, dict) and evidencia.get("id"), f"la respuesta no trae la evidencia: {resumen(cuerpo)}")
    comprobar(
        evidencia.get("estado") == "procesando",
        f"la nota {evidencia.get('id')} nacio en {evidencia.get('estado')} y se esperaba procesando",
    )
    print(f"4. nota creada: {evidencia['id']} (\"{texto}\")")
    return evidencia["id"]


def crear_nota_audio(base: str, ruta: str) -> str:
    comprobar(os.path.isfile(ruta), f"no encuentro el archivo de audio {ruta}")
    with open(ruta, "rb") as archivo:
        crudo = archivo.read()
    comprobar(crudo, f"el archivo {ruta} esta vacio")
    comprobar(
        len(crudo) <= MAX_BYTES_AUDIO,
        f"el audio pesa {len(crudo)} bytes y el tope es {MAX_BYTES_AUDIO} (baja el bitrate o la duracion)",
    )
    extension = os.path.splitext(ruta)[1].lower()
    tipo = TIPOS_AUDIO.get(extension) or mimetypes.guess_type(ruta)[0] or "audio/mp4"
    cuerpo_envio = {
        "salaId": SALA,
        "autorId": USUARIA,
        "formato": "audio",
        "audioBase64": base64.b64encode(crudo).decode("ascii"),
        "mimeType": tipo,
    }
    estado, cuerpo = pedir(base, "POST", "/api/capturas", cuerpo_envio, TIEMPO_ENVIO)
    comprobar(estado == 201, f"POST /api/capturas con audio respondio {estado} {resumen(cuerpo)} (se esperaba 201)")
    evidencia = cuerpo.get("evidencia") if isinstance(cuerpo, dict) else None
    comprobar(isinstance(evidencia, dict) and evidencia.get("id"), f"la respuesta no trae la evidencia: {resumen(cuerpo)}")
    comprobar(
        evidencia.get("estado") == "procesando",
        f"la nota de voz {evidencia.get('id')} nacio en {evidencia.get('estado')} y se esperaba procesando",
    )
    print(f"   nota de voz creada: {evidencia['id']} ({len(crudo) // 1024} KB, {tipo})")
    return evidencia["id"]


def leer_registros(base: str) -> dict:
    estado, cuerpo = pedir(base, "GET", f"/api/salas/{SALA}/registros")
    comprobar(
        estado == 200
        and isinstance(cuerpo, dict)
        and isinstance(cuerpo.get("evidencias"), list)
        and isinstance(cuerpo.get("sugerencias"), list),
        f"GET /api/salas/{SALA}/registros respondio {estado} {resumen(cuerpo)}",
    )
    return cuerpo


def esperar_lista(base: str, id_captura: str, numero: str) -> tuple[dict, list[dict]]:
    """Sondea los registros cada 5 s hasta que la nota queda lista, con tope de 5 minutos."""
    comienzo = time.monotonic()
    limite = comienzo + ESPERA_MAX
    while True:
        registros = leer_registros(base)
        evidencia = next(
            (e for e in registros["evidencias"] if isinstance(e, dict) and e.get("id") == id_captura),
            None,
        )
        comprobar(evidencia is not None, f"la nota {id_captura} no aparece en los registros de {SALA}")
        transcurrido = int(time.monotonic() - comienzo)
        if evidencia.get("estado") == "lista":
            sugerencias = [
                s for s in registros["sugerencias"] if isinstance(s, dict) and s.get("evidenciaId") == id_captura
            ]
            comprobar(sugerencias, f"la nota {id_captura} quedo lista pero sin sugerencias")
            print(f"{numero} nota lista en {transcurrido} s con {len(sugerencias)} sugerencia(s)")
            if evidencia.get("textoExtraido"):
                print(f"   texto: {evidencia['textoExtraido'][:160]}")
            for sugerencia in sugerencias:
                print(
                    f"   - {sugerencia['id']}: nino {sugerencia.get('ninoId') or sugerencia.get('nombreDetectado')},"
                    f" {sugerencia.get('nucleo')} nivel {sugerencia.get('nivel')}, certeza {sugerencia.get('certeza')}"
                )
            return evidencia, sugerencias
        comprobar(
            evidencia.get("estado") != "error",
            f"la nota {id_captura} quedo en error a los {transcurrido} s (revisa los logs de la funcion)",
        )
        comprobar(
            time.monotonic() + INTERVALO < limite,
            f"la nota {id_captura} sigue en procesando despues de {ESPERA_MAX} s",
        )
        print(f"   procesando... {transcurrido} s")
        time.sleep(INTERVALO)


def decidir(base: str, id_sugerencia: str, estado_pedido: str) -> dict:
    """Manda una decision de un solo item y devuelve la sugerencia que respondio el BFF."""
    estado, cuerpo = pedir(
        base,
        "PUT",
        "/api/decisiones",
        {"salaId": SALA, "usuariaId": USUARIA, "items": [{"idSugerencia": id_sugerencia, "estado": estado_pedido}]},
    )
    comprobar(estado == 200, f"PUT /api/decisiones ({estado_pedido}) respondio {estado} {resumen(cuerpo)}")
    sugerencias = cuerpo.get("sugerencias") if isinstance(cuerpo, dict) else None
    comprobar(isinstance(sugerencias, list), f"la respuesta no trae sugerencias: {resumen(cuerpo)}")
    actualizada = next((s for s in sugerencias if isinstance(s, dict) and s.get("id") == id_sugerencia), None)
    comprobar(actualizada is not None, f"la respuesta no trae la sugerencia {id_sugerencia}")
    return actualizada


def estado_guardado(base: str, id_sugerencia: str) -> dict:
    """Vuelve a leer los registros para ver como quedo guardada la decision."""
    registros = leer_registros(base)
    guardada = next(
        (s for s in registros["sugerencias"] if isinstance(s, dict) and s.get("id") == id_sugerencia),
        None,
    )
    comprobar(guardada is not None, f"la sugerencia {id_sugerencia} no aparece al releer los registros")
    return guardada


def confirmar_sugerencia(base: str, id_sugerencia: str) -> None:
    actualizada = decidir(base, id_sugerencia, "aceptada")
    comprobar(
        actualizada.get("estado") == "aceptada",
        f"al confirmar, la sugerencia quedo en {actualizada.get('estado')}",
    )
    comprobar(
        actualizada.get("validadaPor") == USUARIA,
        f"la sugerencia quedo validada por {actualizada.get('validadaPor')} y se esperaba {USUARIA}",
    )
    guardada = estado_guardado(base, id_sugerencia)
    comprobar(
        guardada.get("estado") == "aceptada",
        f"al releer, la sugerencia esta en {guardada.get('estado')} y no en aceptada",
    )
    print(f"6. {id_sugerencia} confirmada: aceptada por {guardada.get('validadaPor')} el {guardada.get('validadaEn')}")


def devolver_a_pendiente(base: str, id_sugerencia: str) -> None:
    actualizada = decidir(base, id_sugerencia, "pendiente")
    comprobar(
        actualizada.get("estado") == "pendiente",
        f"al deshacer, la sugerencia quedo en {actualizada.get('estado')}",
    )
    guardada = estado_guardado(base, id_sugerencia)
    comprobar(
        guardada.get("estado") == "pendiente",
        f"al releer, la sugerencia esta en {guardada.get('estado')} y no en pendiente",
    )
    comprobar(not guardada.get("validadaPor"), "la sugerencia volvio a pendiente pero conservo validadaPor")
    print(f"7. {id_sugerencia} devuelta a pendiente")


def flujo_audio(base: str, ruta: str) -> None:
    print("8. flujo de voz")
    id_captura = crear_nota_audio(base, ruta)
    evidencia, _ = esperar_lista(base, id_captura, "  ")
    comprobar(
        evidencia.get("textoExtraido"),
        f"la nota de voz {id_captura} quedo lista sin transcripcion",
    )


def analizar(argumentos: list[str] | None = None) -> argparse.Namespace:
    analizador = argparse.ArgumentParser(
        prog="smoke.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    analizador.add_argument("url", help="URL base publicada, por ejemplo https://d111111abcdef8.cloudfront.net")
    analizador.add_argument(
        "--audio",
        metavar="archivo.m4a",
        help="prueba tambien el flujo de voz con este archivo (hasta 4 MiB)",
    )
    return analizador.parse_args(argumentos)


def main(argumentos: list[str] | None = None) -> int:
    opciones = analizar(argumentos)
    base = opciones.url.rstrip("/")
    if not base.startswith(("http://", "https://")):
        print(f"La URL tiene que empezar con https:// ({base})")
        return 2
    print(f"Prueba de humo contra {base} como {USUARIA} en {SALA}")
    try:
        salud(base)
        contexto(base)
        nino = elegir_nino(base)
        id_captura = crear_nota(base, nino["nombre"])
        _, sugerencias = esperar_lista(base, id_captura, "5.")
        id_sugerencia = sugerencias[0]["id"]
        confirmar_sugerencia(base, id_sugerencia)
        devolver_a_pendiente(base, id_sugerencia)
        if opciones.audio:
            flujo_audio(base, opciones.audio)
    except Falla as falla:
        print(f"FALLA: {falla}")
        return 1
    print("Todo paso.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
