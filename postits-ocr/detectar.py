"""Detección de post-its con OpenCV: foto -> polígonos (plan 2.3 y 2.4).

Uso como módulo:

    from detectar import cargar_imagen, detectar_postits
    foto = cargar_imagen(datos_jpeg)        # RGB con la orientación EXIF ya aplicada
    detecciones = detectar_postits(foto.rgb)
    for d in detecciones:
        print(d.color, d.poligono)          # 4 esquinas en la resolución ORIGINAL

Uso por consola (depuración rápida de una foto):

    python detectar.py foto.jpg [--overlay salida.jpg]

Los 8 pasos, con los cuatro ajustes de 2.4:

1. Orientación EXIF primero: PIL.ImageOps.exif_transpose antes de pasar a NumPy.
2. Copia reducida a ~1600 px de lado mayor, solo para detectar (velocidad).
3. Máscara HSV por color con RANGOS_HSV (H de 0 a 179; S y V de 0 a 255).
4. Limpieza con kernels chicos (5 y 7 px en la copia de 1600 px): un cierre grande
   pegaría post-its vecinos.
5. Contornos POR COLOR con cv2.RETR_EXTERNAL, nunca sobre la unión de las máscaras:
   así dos post-its de distinto color que se tocan salen separados. Los huecos de la
   tinta no importan porque RETR_EXTERNAL solo toma el contorno exterior.
6. Filtros relativos al área A de la imagen: área entre 0.3% y 40% de A, proporción
   del rectángulo rotado <= 2.5, solidez >= 0.85 y rectangularidad >= 0.75.
7. Esquinas: cv2.approxPolyDP con ε entre 2% y 4% del perímetro (sobre el casco
   convexo, que rellena la "mordida" de un reflejo); si no da 4 puntos, las esquinas
   de cv2.minAreaRect.
8. Duplicados entre colores (IoU > 0.5, por si un post-it cae entre dos rangos) y
   esquinas escaladas a la foto original, donde se hace el warp (recortar.py).

Los rangos son puntos de partida: calíbralos con calibrar.py, los post-its reales y la
luz del lugar.
"""

from __future__ import annotations

import io
import time
from dataclasses import dataclass
from datetime import datetime

import cv2
import numpy as np
from PIL import ExifTags, Image, ImageOps, UnidentifiedImageError

# Rangos HSV iniciales de la tabla de 2.4: (H mín, S mín, V mín), (H máx, S máx, V máx).
# Rosado/fucsia cruza el 0 de H, por eso tiene dos tramos.
RANGOS_HSV: dict[str, list[tuple[tuple[int, int, int], tuple[int, int, int]]]] = {
    "amarillo": [((20, 70, 120), (35, 255, 255))],
    "naranjo": [((5, 110, 120), (19, 255, 255))],
    "rosado": [((140, 60, 120), (179, 255, 255)), ((0, 60, 120), (4, 255, 255))],
    "verde": [((36, 60, 80), (85, 255, 255))],
    "celeste": [((86, 60, 80), (125, 255, 255))],
}

LADO_DETECCION = 1600  # lado mayor de la copia donde se detecta
DESENFOQUE_PREVIO = 5  # Gaussiano 5x5 antes del HSV: baja el ruido del sensor y del JPEG
KERNEL_APERTURA = 5  # quita puntos sueltos
KERNEL_CIERRE = 7  # tapa grietas finas sin unir post-its separados ~1 cm

AREA_MIN_REL = 0.003  # 0.3% del área de la imagen
AREA_MAX_REL = 0.40  # 40%
PROPORCION_MAX = 2.5  # lado largo / lado corto del rectángulo rotado
SOLIDEZ_MIN = 0.85  # área / área del casco convexo
RECTANGULARIDAD_MIN = 0.75  # área / área del rectángulo rotado
EPSILONS_APROX = (0.02, 0.025, 0.03, 0.035, 0.04)  # fracción del perímetro
IOU_DUPLICADO = 0.5
# Segunda pasada (solo para lo que la primera no encontró): saturación y brillo mínimos sobre fondo neutro.
S_MIN_NEUTRO = 90
V_MIN_NEUTRO = 80
MARGEN_EXISTENTES = 9  # px (copia de 1600 px) que se borran alrededor de cada post-it ya detectado

# Firmas de HEIC/HEIF (fotos de iPhone): OpenCV y Pillow sin plugins no las abren.
_MARCAS_HEIC = (b"ftypheic", b"ftypheix", b"ftyphevc", b"ftypheim", b"ftypheis",
                b"ftyphevm", b"ftyphevs", b"ftypmif1", b"ftypmsf1")


class ImagenNoDecodificable(ValueError):
    """La imagen no se pudo abrir. `heic` es True si el archivo es HEIC/HEIF."""

    def __init__(self, mensaje: str, heic: bool = False):
        super().__init__(mensaje)
        self.heic = heic


@dataclass
class Foto:
    """Foto lista para procesar.

    rgb: arreglo HxWx3 uint8 en RGB, con la orientación EXIF ya aplicada.
    fecha_exif: fecha de la toma "AAAA-MM-DD" (DateTimeOriginal o DateTime), o None.
    """

    rgb: np.ndarray
    fecha_exif: str | None


@dataclass
class Deteccion:
    """Un post-it detectado.

    poligono: arreglo (4, 2) float32 con las esquinas en la resolución ORIGINAL
    (sin orden garantizado; recortar.ordenar_esquinas las ordena).
    area_rel: área del contorno / área de la imagen.
    metodo: "aprox" (approxPolyDP, corrige perspectiva) o "rect" (minAreaRect).
    """

    color: str
    poligono: np.ndarray
    area_rel: float
    solidez: float
    rectangularidad: float
    metodo: str


def es_heic(datos: bytes) -> bool:
    """True si los bytes tienen la firma de un archivo HEIC/HEIF."""
    return datos[4:12] in _MARCAS_HEIC


def fecha_exif(imagen: Image.Image) -> str | None:
    """Fecha de la toma desde EXIF (DateTimeOriginal o DateTime) como "AAAA-MM-DD"."""
    try:
        exif = imagen.getexif()
        valor = exif.get_ifd(ExifTags.IFD.Exif).get(ExifTags.Base.DateTimeOriginal)
        valor = valor or exif.get(ExifTags.Base.DateTime)
    except Exception:  # EXIF corrupto: no es motivo para rechazar la foto
        return None
    if not isinstance(valor, str):
        return None
    try:
        return datetime.strptime(valor.strip()[:19], "%Y:%m:%d %H:%M:%S").date().isoformat()
    except ValueError:
        return None


def cargar_imagen(datos: bytes) -> Foto:
    """Abre JPEG/PNG desde bytes, aplica la orientación EXIF y devuelve RGB.

    Lanza ImagenNoDecodificable si no es una imagen legible (HEIC incluido).
    """
    if es_heic(datos):
        raise ImagenNoDecodificable("La foto viene en HEIC/HEIF; súbela en JPEG.", heic=True)
    try:
        imagen = Image.open(io.BytesIO(datos))
        fecha = fecha_exif(imagen)
        imagen = ImageOps.exif_transpose(imagen)  # paso 1: antes de pasar a NumPy
        rgb = np.array(imagen.convert("RGB"))
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as error:
        raise ImagenNoDecodificable(f"No se pudo decodificar la imagen ({type(error).__name__}).") from error
    return Foto(rgb=rgb, fecha_exif=fecha)


def reducir(rgb: np.ndarray, lado: int = LADO_DETECCION) -> tuple[np.ndarray, float]:
    """Copia con el lado mayor <= `lado` (paso 2). Devuelve (copia, escala copia/original)."""
    alto, ancho = rgb.shape[:2]
    escala = lado / max(alto, ancho)
    if escala >= 1:
        return rgb, 1.0
    tam = (max(1, round(ancho * escala)), max(1, round(alto * escala)))
    return cv2.resize(rgb, tam, interpolation=cv2.INTER_AREA), escala


def a_hsv(rgb_reducida: np.ndarray) -> np.ndarray:
    """HSV de OpenCV (H 0-179) tras un desenfoque suave que estabiliza las máscaras."""
    suave = cv2.GaussianBlur(rgb_reducida, (DESENFOQUE_PREVIO, DESENFOQUE_PREVIO), 0)
    return cv2.cvtColor(suave, cv2.COLOR_RGB2HSV)


def mascara_color(hsv: np.ndarray, rangos) -> np.ndarray:
    """Máscara binaria de un color (paso 3) ya limpia (paso 4)."""
    mascara = np.zeros(hsv.shape[:2], np.uint8)
    for bajo, alto in rangos:
        mascara |= cv2.inRange(hsv, np.array(bajo, np.uint8), np.array(alto, np.uint8))
    apertura = cv2.getStructuringElement(cv2.MORPH_RECT, (KERNEL_APERTURA, KERNEL_APERTURA))
    cierre = cv2.getStructuringElement(cv2.MORPH_RECT, (KERNEL_CIERRE, KERNEL_CIERRE))
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, apertura)
    return cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, cierre)


def _esquinas(casco: np.ndarray, rect) -> tuple[np.ndarray, str]:
    """Paso 7: 4 esquinas con approxPolyDP (ε 2-4%) o, si no, las de minAreaRect."""
    perimetro = cv2.arcLength(casco, True)
    for epsilon in EPSILONS_APROX:
        aprox = cv2.approxPolyDP(casco, epsilon * perimetro, True)
        if len(aprox) == 4 and cv2.isContourConvex(aprox):
            return aprox.reshape(4, 2).astype(np.float32), "aprox"
    return cv2.boxPoints(rect).astype(np.float32), "rect"


def candidatos_color(mascara: np.ndarray, color: str, area_imagen: float) -> list[Deteccion]:
    """Pasos 5-7 sobre la máscara de UN color. Polígonos en coordenadas de la copia reducida."""
    contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    salida = []
    for contorno in contornos:
        area = cv2.contourArea(contorno)
        if not (AREA_MIN_REL * area_imagen <= area <= AREA_MAX_REL * area_imagen):
            continue
        rect = cv2.minAreaRect(contorno)
        lado_a, lado_b = rect[1]
        if min(lado_a, lado_b) <= 0 or max(lado_a, lado_b) / min(lado_a, lado_b) > PROPORCION_MAX:
            continue
        casco = cv2.convexHull(contorno)
        solidez = area / max(cv2.contourArea(casco), 1e-6)
        rectangularidad = area / (lado_a * lado_b)
        if solidez < SOLIDEZ_MIN or rectangularidad < RECTANGULARIDAD_MIN:
            continue
        esquinas, metodo = _esquinas(casco, rect)
        salida.append(Deteccion(color, esquinas, area / area_imagen, solidez, rectangularidad, metodo))
    return salida


def iou_poligonos(a: np.ndarray, b: np.ndarray) -> float:
    """IoU de dos polígonos rasterizándolos en su caja común (coordenadas en px)."""
    xa, ya, wa, ha = cv2.boundingRect(np.round(a).astype(np.int32))
    xb, yb, wb, hb = cv2.boundingRect(np.round(b).astype(np.int32))
    if xa > xb + wb or xb > xa + wa or ya > yb + hb or yb > ya + ha:
        return 0.0
    x0, y0 = min(xa, xb), min(ya, yb)
    ancho, alto = max(xa + wa, xb + wb) - x0 + 1, max(ya + ha, yb + hb) - y0 + 1
    lienzo_a = np.zeros((alto, ancho), np.uint8)
    lienzo_b = np.zeros((alto, ancho), np.uint8)
    desplazamiento = np.array([x0, y0], np.float32)
    cv2.fillPoly(lienzo_a, [np.round(a - desplazamiento).astype(np.int32)], 1)
    cv2.fillPoly(lienzo_b, [np.round(b - desplazamiento).astype(np.int32)], 1)
    union = np.count_nonzero(lienzo_a | lienzo_b)
    return np.count_nonzero(lienzo_a & lienzo_b) / union if union else 0.0


def quitar_duplicados(detecciones: list[Deteccion]) -> list[Deteccion]:
    """Paso 8a: si dos detecciones (de colores distintos) tienen IoU > 0.5, queda la mayor."""
    restantes: list[Deteccion] = []
    for candidata in sorted(detecciones, key=lambda d: d.area_rel, reverse=True):
        if all(iou_poligonos(candidata.poligono, otra.poligono) <= IOU_DUPLICADO for otra in restantes):
            restantes.append(candidata)
    return restantes


def color_de_tono(h: float) -> str:
    """Etiqueta de RANGOS_HSV cuyo tramo de H contiene `h` (o el tramo más cercano, H circular de 0 a 179)."""
    mejor, distancia = "desconocido", 1e9
    for color, rangos in RANGOS_HSV.items():
        for bajo, alto in rangos:
            if bajo[0] <= h <= alto[0]:
                return color
            d = min(abs(h - bajo[0]), abs(h - alto[0]), 180 - abs(h - bajo[0]), 180 - abs(h - alto[0]))
            if d < distancia:
                mejor, distancia = color, d
    return mejor


def _tono_medio(hsv: np.ndarray, poligono: np.ndarray) -> float:
    """Media circular de H (0-179) dentro del polígono."""
    mascara = np.zeros(hsv.shape[:2], np.uint8)
    cv2.fillPoly(mascara, [np.round(poligono).astype(np.int32)], 1)
    angulos = hsv[..., 0][mascara > 0].astype(np.float64) * (np.pi / 90.0)
    if angulos.size == 0:
        return -1.0
    return float(np.degrees(np.arctan2(np.sin(angulos).mean(), np.cos(angulos).mean())) / 2.0) % 180.0


def segunda_pasada(hsv: np.ndarray, detecciones: list[Deteccion], area_imagen: float) -> list[Deteccion]:
    """Post-its que la primera pasada no encontró: un tono entre dos rangos, sombra fuerte o un post-it
    tapado en parte por otro. Máscara solo por saturación y brillo (el fondo neutro queda fuera), sin
    las zonas ya detectadas, con los mismos filtros de forma; el color sale de la media de H."""
    mascara = cv2.inRange(hsv, np.array((0, S_MIN_NEUTRO, V_MIN_NEUTRO), np.uint8),
                          np.array((179, 255, 255), np.uint8))
    apertura = cv2.getStructuringElement(cv2.MORPH_RECT, (KERNEL_APERTURA, KERNEL_APERTURA))
    cierre = cv2.getStructuringElement(cv2.MORPH_RECT, (KERNEL_CIERRE, KERNEL_CIERRE))
    mascara = cv2.morphologyEx(cv2.morphologyEx(mascara, cv2.MORPH_OPEN, apertura), cv2.MORPH_CLOSE, cierre)
    for d in detecciones:  # sin los post-its ya detectados (y un borde), para no volver a encontrarlos
        pts = np.round(d.poligono).astype(np.int32)
        cv2.fillPoly(mascara, [pts], 0)
        cv2.polylines(mascara, [pts], True, 0, MARGEN_EXISTENTES)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, apertura)
    nuevas = []
    for c in candidatos_color(mascara, "desconocido", area_imagen):
        if all(iou_poligonos(c.poligono, d.poligono) <= IOU_DUPLICADO for d in detecciones + nuevas):
            c.color = color_de_tono(_tono_medio(hsv, c.poligono))
            nuevas.append(c)
    return nuevas


def detectar_postits(rgb: np.ndarray, rangos=None, lado: int = LADO_DETECCION) -> list[Deteccion]:
    """Detecta los post-its de una foto RGB (ya enderezada con cargar_imagen).

    Devuelve las detecciones con el polígono en coordenadas de `rgb` (la resolución
    original), sin orden de lectura (lo da recortar.orden_lectura).
    """
    rangos = rangos or RANGOS_HSV
    reducida, escala = reducir(rgb, lado)
    hsv = a_hsv(reducida)
    area_imagen = float(reducida.shape[0] * reducida.shape[1])
    detecciones: list[Deteccion] = []
    for color, rangos_color in rangos.items():  # contornos POR COLOR, nunca sobre la unión
        detecciones.extend(candidatos_color(mascara_color(hsv, rangos_color), color, area_imagen))
    detecciones = quitar_duplicados(detecciones)
    detecciones += segunda_pasada(hsv, detecciones, area_imagen)
    alto, ancho = rgb.shape[:2]
    for d in detecciones:  # paso 8b: esquinas a la resolución original
        d.poligono = d.poligono / np.float32(escala)
        d.poligono[:, 0] = np.clip(d.poligono[:, 0], 0, ancho - 1)
        d.poligono[:, 1] = np.clip(d.poligono[:, 1], 0, alto - 1)
    return detecciones


def _main() -> None:
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(
        description="Detecta los post-its de una foto y lista color y esquinas (resolución original).")
    parser.add_argument("foto", help="ruta a la foto (JPEG o PNG)")
    parser.add_argument("--overlay", help="ruta donde guardar el overlay numerado (JPEG)")
    args = parser.parse_args()

    import recortar  # solo para el orden de lectura y el overlay

    inicio = time.perf_counter()
    foto = cargar_imagen(Path(args.foto).read_bytes())
    detecciones = detectar_postits(foto.rgb)
    ms = (time.perf_counter() - inicio) * 1000
    orden = recortar.orden_lectura([d.poligono for d in detecciones])
    alto, ancho = foto.rgb.shape[:2]
    print(f"{args.foto}: {ancho}x{alto}, {len(detecciones)} post-its en {ms:.0f} ms")
    for numero, i in enumerate(orden, start=1):
        d = detecciones[i]
        esquinas = recortar.ordenar_esquinas(d.poligono).round().astype(int).tolist()
        print(f"  {numero:2d}. {d.color:9s} {d.metodo:5s} área {d.area_rel:.2%}  {esquinas}")
    if args.overlay:
        elementos = [(detecciones[i].poligono, detecciones[i].color, n) for n, i in enumerate(orden, 1)]
        Path(args.overlay).write_bytes(recortar.dibujar_overlay(foto.rgb, elementos))
        print(f"overlay: {args.overlay}")


if __name__ == "__main__":
    _main()
