"""Genera la rúbrica 5 × 9 y la semilla local de Huellita desde el dataset sintético E-1.

Entradas (rutas desde la raíz del repositorio):
- Dump/dataset_e1_publico/datos_publicos/*.csv: ruta de niveles, manifestaciones,
  jardines, niños y observaciones.
- integra-backend/tests/fixtures/nomina_demo.json: nombres de demo de JAR-0001
  (los mismos que integra-procesador cargó en DynamoDB).
- huellita-web/src/huellita_api/datos/usuarias_demo.json: tías de la demo.

Salidas, en data/: rubrica_e1.json y semilla.json. El historial sigue las mismas
reglas que el BFF (huellita-web/src/huellita_api/mapeo.py), así el modo local y el
modo AWS muestran lo mismo.

Solo biblioteca estándar. Uso (PowerShell, desde huellita-formato-mejorado):
  python scripts/generar_datos_e1.py
"""
from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

CARPETA_APP = Path(__file__).resolve().parents[1]
RAIZ = CARPETA_APP.parent
DATASET = RAIZ / "Dump" / "dataset_e1_publico" / "datos_publicos"
NOMINA = RAIZ / "integra-backend" / "tests" / "fixtures" / "nomina_demo.json"
USUARIAS = RAIZ / "huellita-web" / "src" / "huellita_api" / "datos" / "usuarias_demo.json"
SALIDA = CARPETA_APP / "data"

VERSION_SEMILLA = 2
FECHA_DEMO = "2026-10-15"
JARDIN = "JAR-0001"
SALAS = ("SG-A", "SG-B")
ZONA = "-03:00"

# Dominio del dataset → etiqueta y ámbito de las BCEP (para el color de la interfaz).
DOMINIOS: list[tuple[str, str, str]] = [
    ("motor_grueso", "Motor grueso", "Desarrollo personal y social"),
    ("motor_fino", "Motor fino", "Desarrollo personal y social"),
    ("lenguaje_comunicacion", "Lenguaje y comunicación", "Comunicación integral"),
    ("socioemocional", "Socioemocional", "Desarrollo personal y social"),
    ("cognitivo", "Cognitivo", "Interacción y comprensión del entorno"),
]

NOTA_RUBRICA = (
    "Ruta orientativa de 9 niveles del dataset sintético E-1: 5 dominios, 9 niveles y 2 conductas "
    "observables por celda. Es apoyo pedagógico: no es un instrumento clínico, diagnóstico ni de "
    "tamizaje. Generada por scripts/generar_datos_e1.py."
)
NOTA_SEMILLA = (
    "Datos ficticios para la demo de Huellita: jardín JAR-0001 del dataset sintético E-1 (salas SG-A "
    "y SG-B) con nombres de demo. Generados por scripts/generar_datos_e1.py."
)

DIRECTORA_LOCAL = {
    "id": "USR-CARMEN",
    "nombre": "Directora Carmen",
    "rol": "directora",
    "jardinId": JARDIN,
    "salaIds": list(SALAS),
}


def leer_csv(nombre: str) -> list[dict[str, str]]:
    with (DATASET / nombre).open(encoding="utf-8", newline="") as archivo:
        return list(csv.DictReader(archivo))


def leer_json(ruta: Path) -> dict:
    return json.loads(ruta.read_text(encoding="utf-8"))


def escribir_json(ruta: Path, contenido: object) -> None:
    ruta.write_text(json.dumps(contenido, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


# --- reglas compartidas con el BFF (mapeo.py) ------------------------------------------


def clave_orden(texto: str) -> str:
    """Orden alfabético sin tildes ni mayúsculas ("Álvaro" queda junto a "Alba")."""
    plano = unicodedata.normalize("NFD", texto)
    return "".join(c for c in plano if not unicodedata.combining(c)).casefold()


def separar_nombre(nombre: str) -> tuple[str, str]:
    """ "Martina M." → ("Martina", "M."): la inicial distingue homónimos de la sala."""
    m = re.match(r"^(.+?)\s+([A-ZÁÉÍÓÚÑ])\.$", nombre.strip())
    return (m.group(1), f"{m.group(2)}.") if m else (nombre.strip(), "")


def edad_meses(nacimiento: str, hoy: str) -> int:
    """Meses completos cumplidos (la misma fórmula de lib/evaluacion.ts)."""
    an, mn, dn = (int(x) for x in nacimiento[:10].split("-"))
    ah, mh, dh = (int(x) for x in hoy[:10].split("-"))
    meses = (ah - an) * 12 + (mh - mn) - (1 if dh < dn else 0)
    return max(0, meses)


def nivel_educativo(meses: int) -> str:
    if meses < 12:
        return "Sala Cuna Menor"
    if meses < 24:
        return "Sala Cuna Mayor"
    if meses < 36:
        return "Medio Menor"
    if meses < 48:
        return "Medio Mayor"
    if meses < 60:
        return "Transición 1"
    return "Transición 2"


def mediana_baja(valores: list[int]) -> int:
    ordenados = sorted(valores)
    return ordenados[(len(ordenados) - 1) // 2]


def nombre_sala(sala_grupo: str) -> str:
    """ "SG-A" → "Sala A"."""
    return f"Sala {sala_grupo.split('-')[-1]}"


def texto_literal(manifestaciones: list[dict[str, str]], nota_breve: str) -> str:
    """Misma receta que integra-backend/scripts/cargar_aws.py: conductas + nota breve."""
    partes = [m["texto_observable"] for m in manifestaciones]
    if nota_breve and nota_breve.strip():
        partes.append(nota_breve.strip())
    return " ".join(partes)


def sugerencias_historial(
    id_obs: str,
    id_nino: str,
    sala: str,
    autor: str,
    creada_en: str,
    nivel_obs: int | None,
    manifestaciones: list[dict[str, str]],
) -> list[dict]:
    """Una sugerencia aceptada por dominio distinto, en el orden de las manifestaciones."""
    por_dominio: dict[str, list[dict[str, str]]] = defaultdict(list)
    for m in manifestaciones:
        por_dominio[m["dominio"]].append(m)
    resultado = []
    for dominio, delDominio in por_dominio.items():
        nivel = nivel_obs if nivel_obs is not None else max(int(m["nivel"]) for m in delDominio)
        resultado.append(
            {
                "id": f"{id_obs}~{dominio}",
                "evidenciaId": id_obs,
                "salaId": sala,
                "tipo": "evaluacion",
                "ninoId": id_nino,
                "nucleo": dominio,
                "nivel": nivel,
                "conducta": delDominio[0]["texto_observable"],
                "cita": " ".join(m["texto_observable"] for m in delDominio),
                "certeza": "alta",
                "estado": "aceptada",
                "validadaPor": autor,
                "validadaEn": creada_en,
            }
        )
    return resultado


# --- rúbrica ----------------------------------------------------------------------------


def generar_rubrica() -> dict:
    ruta = sorted(leer_csv("ruta_niveles.csv"), key=lambda f: int(f["nivel"]))
    manifestaciones = leer_csv("manifestaciones.csv")
    conductas: dict[tuple[str, int], list[str]] = defaultdict(list)
    for m in sorted(manifestaciones, key=lambda f: f["id_manifestacion"]):
        conductas[(m["dominio"], int(m["nivel"]))].append(m["texto_observable"])

    niveles = [
        {
            "nivel": int(f["nivel"]),
            "nombre": f["nombre_nivel"],
            "tramo_bcep": "",
            "grupo_orientativo": "",
            "edad_orientativa": f"{f['edad_min_meses']}–{f['edad_max_meses']} meses",
        }
        for f in ruta
    ]
    rubrica = []
    for codigo, etiqueta, ambito in DOMINIOS:
        rubrica.append(
            {
                "codigo": codigo,
                "nucleo": etiqueta,
                "ambito": ambito,
                "niveles": [
                    {
                        "nivel": int(f["nivel"]),
                        "nombre": f["nombre_nivel"],
                        "descriptor": f["descripcion"],
                        "conductas_observables": conductas[(codigo, int(f["nivel"]))],
                        "oa_referencia": [],
                    }
                    for f in ruta
                ],
            }
        )
    return {"nota": NOTA_RUBRICA, "niveles": niveles, "rubrica": rubrica}


# --- semilla ----------------------------------------------------------------------------


def manifestacion(cruce: dict[str, dict[str, str]], id_manifestacion: str) -> dict[str, str]:
    return {"id_manifestacion": id_manifestacion, **cruce[id_manifestacion]}


def demo_del_dia(conducta: dict[str, str]) -> tuple[list[dict], list[dict]]:
    """Notas de hoy: 3 por revisar en la Sala A y la foto de las tortugas ya confirmada."""
    hoy = FECHA_DEMO
    evidencias = [
        {
            "id": "EVI-D0001",
            "salaId": "SG-A",
            "autorId": "EDU-0001",
            "creadaEn": f"{hoy}T09:40:00{ZONA}",
            "formato": "foto",
            "textoExtraido": (
                "Durante la experiencia de la zona identifica las tortugas pequeñas, medianas y grandes; "
                "selecciona cantidades de piezas ordenando por colores y tamaños."
            ),
            "estado": "lista",
            "foto": "postit-tortugas",
        },
        {
            "id": "EVI-D0002",
            "salaId": "SG-A",
            "autorId": "EDU-0001",
            "creadaEn": f"{hoy}T09:55:00{ZONA}",
            "formato": "texto",
            "textoExtraido": "Josefa le pasó la pelota a Pedro y esperó su turno para volver a lanzar.",
            "estado": "lista",
        },
        {
            "id": "EVI-D0003",
            "salaId": "SG-A",
            "autorId": "EDU-0002",
            "creadaEn": f"{hoy}T10:50:00{ZONA}",
            "formato": "audio",
            "textoExtraido": "Sofía subió la escalera del patio sola alternando los pies, afirmándose de la baranda.",
            "estado": "lista",
        },
        {
            "id": "EVI-D0004",
            "salaId": "SG-A",
            "autorId": "EDU-0001",
            "creadaEn": f"{hoy}T11:50:00{ZONA}",
            "formato": "texto",
            "textoExtraido": "Naya guardó los cubos en la caja cuando la tía dijo que era hora de ordenar.",
            "estado": "lista",
        },
    ]
    sugerencias = [
        {
            "id": "SUG-D0001",
            "evidenciaId": "EVI-D0001",
            "salaId": "SG-A",
            "tipo": "evaluacion",
            "ninoId": "NINO-00356",
            "nombreDetectado": "Tomás",
            "nucleo": "cognitivo",
            "nivel": 9,
            "conducta": conducta["MAN-L09-CO-02"],
            "cita": "identifica las tortugas pequeñas, medianas y grandes; selecciona cantidades de piezas ordenando por colores y tamaños",
            "certeza": "alta",
            "estado": "aceptada",
            "validadaPor": "EDU-0001",
            "validadaEn": f"{hoy}T09:41:00{ZONA}",
        },
        {
            "id": "SUG-D0002",
            "evidenciaId": "EVI-D0002",
            "salaId": "SG-A",
            "tipo": "evaluacion",
            "ninoId": "NINO-00008",
            "nombreDetectado": "Josefa",
            "nucleo": "socioemocional",
            "nivel": 9,
            "conducta": conducta["MAN-L09-SE-01"],
            "cita": "Josefa le pasó la pelota a Pedro y esperó su turno para volver a lanzar.",
            "certeza": "alta",
            "estado": "pendiente",
        },
        {
            "id": "SUG-D0003",
            "evidenciaId": "EVI-D0003",
            "salaId": "SG-A",
            "tipo": "evaluacion",
            "ninoId": "NINO-00372",
            "nombreDetectado": "Sofía",
            "nucleo": "motor_grueso",
            "nivel": 9,
            "conducta": conducta["MAN-L09-MG-02"],
            "cita": "Sofía subió la escalera del patio sola alternando los pies, afirmándose de la baranda.",
            "certeza": "media",
            "estado": "pendiente",
        },
        {
            "id": "SUG-D0004",
            "evidenciaId": "EVI-D0004",
            "salaId": "SG-A",
            "tipo": "evaluacion",
            "ninoId": "NINO-00487",
            "nombreDetectado": "Naya",
            "nucleo": "socioemocional",
            "nivel": 9,
            "conducta": conducta["MAN-L09-SE-02"],
            "cita": "Naya guardó los cubos en la caja cuando la tía dijo que era hora de ordenar.",
            "certeza": "baja",
            "estado": "pendiente",
        },
    ]
    return evidencias, sugerencias


def guiones(conducta: dict[str, str]) -> list[dict]:
    """Guiones de la IA simulada para foto y audio, con niños/as de la Sala A."""
    return [
        {
            "formato": "foto",
            "foto": "postit-individuales",
            "texto": (
                "Josefa: cuando salía del baño se da cuenta que a la tía se le caen los individuales, ella se "
                "agacha y recoge los individuales, los ordena y se los pasa a la tía."
            ),
            "sugerencias": [
                {
                    "tipo": "evaluacion",
                    "nombreDetectado": "Josefa",
                    "ninoId": "NINO-00008",
                    "nucleo": "socioemocional",
                    "nivel": 9,
                    "conducta": conducta["MAN-L09-SE-02"],
                    "cita": "se agacha y recoge los individuales, los ordena y se los pasa a la tía",
                    "certeza": "alta",
                }
            ],
        },
        {
            "formato": "foto",
            "foto": "postit-hojas",
            "texto": "Emilio clasificó las hojas del otoño por tres colores, y después las separó en grandes y pequeñas.",
            "sugerencias": [
                {
                    "tipo": "evaluacion",
                    "nombreDetectado": "Emilio",
                    "ninoId": "NINO-00453",
                    "nucleo": "cognitivo",
                    "nivel": 9,
                    "conducta": conducta["MAN-L09-CO-02"],
                    "cita": "clasificó las hojas del otoño por tres colores, y después las separó en grandes y pequeñas",
                    "certeza": "media",
                }
            ],
        },
        {
            "formato": "foto",
            "texto": (
                "Los niños durante esta semana han tenido un cambio en su etapa emocional, conductas desafiantes, "
                "imitándose entre ellos. Se conversó como equipo buscando estrategias."
            ),
            "sugerencias": [
                {
                    "tipo": "nota_sala",
                    "cita": "cambio en su etapa emocional, conductas desafiantes, imitándose entre ellos",
                    "certeza": "alta",
                }
            ],
        },
        {
            "formato": "texto",
            "texto": "Sofía y Pedro armaron juntos una torre de seis bloques y Sofía los contó en voz alta.",
            "sugerencias": [
                {
                    "tipo": "evaluacion",
                    "nombreDetectado": "Sofía",
                    "ninoId": "NINO-00372",
                    "nucleo": "motor_fino",
                    "nivel": 8,
                    "conducta": conducta["MAN-L08-MF-01"],
                    "cita": "armaron juntos una torre de seis bloques",
                    "certeza": "alta",
                },
                {
                    "tipo": "evaluacion",
                    "nombreDetectado": "Pedro",
                    "ninoId": "NINO-00253",
                    "nucleo": "socioemocional",
                    "nivel": 8,
                    "conducta": conducta["MAN-L08-SE-01"],
                    "cita": "Sofía y Pedro armaron juntos una torre",
                    "certeza": "media",
                },
            ],
        },
        {
            "formato": "audio",
            "texto": "Hoy bajó la asistencia, los niños comenzaron a resfriarse y han estado con mucha tos.",
            "sugerencias": [
                {
                    "tipo": "nota_sala",
                    "cita": "bajó la asistencia, los niños comenzaron a resfriarse",
                    "certeza": "alta",
                }
            ],
        },
    ]


def generar_semilla() -> dict:
    cruce = {
        m["id_manifestacion"]: {
            "nivel": m["nivel"],
            "dominio": m["dominio"],
            "texto_observable": m["texto_observable"],
        }
        for m in leer_csv("manifestaciones.csv")
    }
    conducta = {k: v["texto_observable"] for k, v in cruce.items()}
    por_obs: dict[str, list[str]] = defaultdict(list)
    for fila in leer_csv("observacion_manifestaciones.csv"):
        por_obs[fila["id_observacion"]].append(fila["id_manifestacion"])

    jardin_csv = next(j for j in leer_csv("jardines.csv") if j["id_jardin"] == JARDIN)
    nomina = {n["id_nino"]: n for n in leer_json(NOMINA)["ninos"]}
    ninos_csv = {n["id_nino"]: n for n in leer_csv("ninos.csv") if n["id_nino"] in nomina}
    assert len(ninos_csv) == len(nomina), "la nómina de demo no calza con ninos.csv"

    ninos = []
    for id_nino, fila in ninos_csv.items():
        nombre, inicial = separar_nombre(nomina[id_nino]["nombre"])
        ninos.append(
            {
                "id": id_nino,
                "nombre": nombre,
                "apellidoInicial": inicial,
                "fechaNacimiento": fila["fecha_nacimiento"],
                "salaId": fila["sala_grupo"],
                "activo": True,
            }
        )
    ninos.sort(key=lambda n: (SALAS.index(n["salaId"]), clave_orden(n["nombre"]), n["apellidoInicial"]))

    salas = []
    for sala in SALAS:
        edades = [edad_meses(n["fechaNacimiento"], FECHA_DEMO) for n in ninos if n["salaId"] == sala]
        salas.append(
            {
                "id": sala,
                "jardinId": JARDIN,
                "nombre": nombre_sala(sala),
                "nivelEducativo": nivel_educativo(mediana_baja(edades)),
            }
        )

    usuarias = [*leer_json(USUARIAS)["usuarias"], DIRECTORA_LOCAL]

    observaciones = sorted(
        (o for o in leer_csv("observaciones.csv") if o["id_nino"] in ninos_csv),
        key=lambda o: (o["fecha_observacion"], o["id_observacion"]),
    )
    evidencias: list[dict] = []
    sugerencias: list[dict] = []
    for o in observaciones:
        sala = ninos_csv[o["id_nino"]]["sala_grupo"]
        creada_en = f"{o['fecha_observacion']}T12:00:00{ZONA}"
        mans = [manifestacion(cruce, m) for m in por_obs[o["id_observacion"]] if m in cruce]
        evidencias.append(
            {
                "id": o["id_observacion"],
                "salaId": sala,
                "autorId": o["id_educadora"],
                "creadaEn": creada_en,
                "formato": "texto",
                "textoExtraido": texto_literal(mans, o["nota_breve"]),
                "estado": "lista",
            }
        )
        nivel = int(o["nivel_estimado"]) if o["nivel_estimado"].strip() else None
        sugerencias.extend(
            sugerencias_historial(
                o["id_observacion"], o["id_nino"], sala, o["id_educadora"], creada_en, nivel, mans
            )
        )

    evidencias_hoy, sugerencias_hoy = demo_del_dia(conducta)
    return {
        "version": VERSION_SEMILLA,
        "nota": NOTA_SEMILLA,
        "fechaDemo": FECHA_DEMO,
        "jardin": {
            "id": JARDIN,
            "nombre": jardin_csv["nombre_fantasia"],
            "comuna": jardin_csv["comuna"],
            "region": jardin_csv["region"],
        },
        "salas": salas,
        "usuarias": usuarias,
        "ninos": ninos,
        "evidencias": evidencias + evidencias_hoy,
        "sugerencias": sugerencias + sugerencias_hoy,
        "demoCapturas": guiones(conducta),
    }


def main() -> None:
    rubrica = generar_rubrica()
    semilla = generar_semilla()
    escribir_json(SALIDA / "rubrica_e1.json", rubrica)
    escribir_json(SALIDA / "semilla.json", semilla)
    print(
        f"rubrica_e1.json: {len(rubrica['rubrica'])} dominios × {len(rubrica['niveles'])} niveles; "
        f"semilla.json: {len(semilla['ninos'])} niños, {len(semilla['evidencias'])} evidencias, "
        f"{len(semilla['sugerencias'])} sugerencias"
    )


if __name__ == "__main__":
    main()
