"""Polígonos -> recortes derechos, orden de lectura y overlay (plan 2.4).

Uso como módulo:

    import recortar
    orden = recortar.orden_lectura([d.poligono for d in detecciones])
    for numero, i in enumerate(orden, start=1):
        esquinas = recortar.ordenar_esquinas(detecciones[i].poligono)
        recorte = recortar.recortar_postit(foto.rgb, esquinas)     # foto ORIGINAL
        jpeg = recortar.codificar_jpeg(recorte)                     # calidad 90
    overlay = recortar.dibujar_overlay(foto.rgb, [(poligono, color, numero), ...])

- ordenar_esquinas: sup-izq = menor x+y, inf-der = mayor x+y, sup-der = menor y-x,
  inf-izq = mayor y-x. Deja el post-it derecho mientras la inclinación sea menor a 45°.
- recortar_postit: getPerspectiveTransform + warpPerspective sobre la foto ORIGINAL
  (no sobre la copia de detección) y recorte de 2.5% hacia adentro para sacar el borde
  del fondo.
- orden_lectura: agrupa en filas los post-its cuyo centro difiere en y menos de media
  altura mediana y ordena cada fila por x (ordenar solo por (y, x) falla con post-its
  algo desalineados).
- dibujar_overlay: cada polígono con su color y su número de orden, sobre una copia de
  lado mayor 1600 px (liviana para el front).
- codificar_jpeg: JPEG calidad 90 dentro de los límites de una imagen de Bedrock Converse
  (3.75 MB y 8000 px por lado).

Las imágenes son RGB en todo el módulo; solo se pasa a BGR al codificar con OpenCV.
"""

from __future__ import annotations

import cv2
import numpy as np

MARGEN_INTERIOR = 0.025  # 2.5%: dentro del 2-3% del plan
CALIDAD_JPEG = 90
MAX_BYTES_IMAGEN = 3_750_000  # límite de Converse (3.75 MB), con holgura
MAX_LADO_IMAGEN = 8000  # límite de Converse por lado
LADO_OVERLAY = 1600

# Colores de dibujo (RGB) por etiqueta de color de detectar.RANGOS_HSV.
COLORES_DIBUJO = {
    "amarillo": (255, 204, 0),
    "naranjo": (255, 120, 0),
    "rosado": (255, 40, 160),
    "verde": (0, 190, 60),
    "celeste": (0, 150, 255),
}
COLOR_DESCONOCIDO = (160, 160, 160)


def ordenar_esquinas(puntos) -> np.ndarray:
    """Ordena 4 esquinas como [sup-izq, sup-der, inf-der, inf-izq] (float32, forma (4, 2))."""
    pts = np.asarray(puntos, dtype=np.float32).reshape(4, 2)
    suma = pts.sum(axis=1)
    resta = pts[:, 1] - pts[:, 0]  # y - x
    indices = [int(np.argmin(suma)), int(np.argmin(resta)), int(np.argmax(suma)), int(np.argmax(resta))]
    if len(set(indices)) == 4:
        return pts[indices]
    # Cerca de 45° las reglas empatan: orden horario por ángulo desde la de menor x+y.
    centro = pts.mean(axis=0)
    angulos = np.arctan2(pts[:, 1] - centro[1], pts[:, 0] - centro[0])
    horario = list(np.argsort(angulos))
    inicio = horario.index(int(np.argmin(suma)))
    return pts[horario[inicio:] + horario[:inicio]]


def _lados(esquinas: np.ndarray) -> tuple[float, float]:
    """(ancho, alto) del cuadrilátero ordenado: el mayor de cada par de lados opuestos."""
    sup_izq, sup_der, inf_der, inf_izq = esquinas
    ancho = max(np.linalg.norm(sup_der - sup_izq), np.linalg.norm(inf_der - inf_izq))
    alto = max(np.linalg.norm(inf_izq - sup_izq), np.linalg.norm(inf_der - sup_der))
    return float(ancho), float(alto)


def recortar_postit(rgb_original: np.ndarray, poligono, margen: float = MARGEN_INTERIOR) -> np.ndarray:
    """Recorte derecho del post-it: warp de perspectiva sobre la foto ORIGINAL."""
    esquinas = ordenar_esquinas(poligono)
    ancho, alto = _lados(esquinas)
    ancho, alto = max(2, int(round(ancho))), max(2, int(round(alto)))
    destino = np.array([[0, 0], [ancho - 1, 0], [ancho - 1, alto - 1], [0, alto - 1]], np.float32)
    matriz = cv2.getPerspectiveTransform(esquinas, destino)
    derecho = cv2.warpPerspective(rgb_original, matriz, (ancho, alto), flags=cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_REPLICATE)
    mx, my = int(round(ancho * margen)), int(round(alto * margen))
    return derecho[my:alto - my, mx:ancho - mx] if alto - 2 * my > 0 and ancho - 2 * mx > 0 else derecho


def orden_lectura(poligonos) -> list[int]:
    """Índices de `poligonos` en orden de lectura: filas de arriba a abajo, cada una por x."""
    if not poligonos:
        return []
    esquinas = [ordenar_esquinas(p) for p in poligonos]
    centros = [e.mean(axis=0) for e in esquinas]
    alturas = [_lados(e)[1] for e in esquinas]
    tolerancia = float(np.median(alturas)) / 2
    filas: list[list[int]] = []
    for i in sorted(range(len(poligonos)), key=lambda k: centros[k][1]):
        if filas and abs(centros[i][1] - np.mean([centros[k][1] for k in filas[-1]])) < tolerancia:
            filas[-1].append(i)
        else:
            filas.append([i])
    return [i for fila in filas for i in sorted(fila, key=lambda k: centros[k][0])]


def codificar_jpeg(rgb: np.ndarray, calidad: int = CALIDAD_JPEG, max_bytes: int = MAX_BYTES_IMAGEN,
                   max_lado: int = MAX_LADO_IMAGEN) -> bytes:
    """JPEG desde RGB, achicando calidad y tamaño si hace falta para no pasar los límites."""
    imagen = rgb
    if max(imagen.shape[:2]) > max_lado:
        escala = max_lado / max(imagen.shape[:2])
        imagen = cv2.resize(imagen, None, fx=escala, fy=escala, interpolation=cv2.INTER_AREA)
    bgr = cv2.cvtColor(np.ascontiguousarray(imagen), cv2.COLOR_RGB2BGR)
    while True:
        ok, datos = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, calidad])
        if not ok:
            raise ValueError("OpenCV no pudo codificar el JPEG")
        if len(datos) <= max_bytes:
            return datos.tobytes()
        if calidad > 60:
            calidad -= 10
        else:
            bgr = cv2.resize(bgr, None, fx=0.8, fy=0.8, interpolation=cv2.INTER_AREA)


def dibujar_overlay(rgb: np.ndarray, elementos, lado: int = LADO_OVERLAY, calidad: int = 85,
                    extra=None) -> bytes:
    """Overlay JPEG: polígonos con el color de cada post-it y su número de orden.

    elementos: iterable de (poligono en coordenadas de `rgb`, etiqueta de color, número).
    extra: polígonos adicionales (coordenadas de `rgb`) que se marcan en rojo con una X,
    por ejemplo los post-its esperados que no se detectaron (lo usa evaluar.py).
    """
    escala = min(1.0, lado / max(rgb.shape[:2]))
    lienzo = rgb if escala == 1.0 else cv2.resize(rgb, None, fx=escala, fy=escala,
                                                  interpolation=cv2.INTER_AREA)
    lienzo = np.ascontiguousarray(lienzo).copy()
    grosor = max(2, round(max(lienzo.shape[:2]) / 400))
    for poligono, color, numero in elementos:
        pts = np.round(ordenar_esquinas(poligono) * escala).astype(np.int32)
        rgb_color = COLORES_DIBUJO.get(color, COLOR_DESCONOCIDO)
        cv2.polylines(lienzo, [pts], True, (0, 0, 0), grosor + 3, cv2.LINE_AA)
        cv2.polylines(lienzo, [pts], True, rgb_color, grosor, cv2.LINE_AA)
        centro = pts.mean(axis=0).round().astype(int)
        radio = int(max(14, min(40, 0.22 * min(_lados(pts.astype(np.float32))))))
        cv2.circle(lienzo, tuple(int(v) for v in centro), radio, rgb_color, -1, cv2.LINE_AA)
        cv2.circle(lienzo, tuple(int(v) for v in centro), radio, (0, 0, 0), 2, cv2.LINE_AA)
        texto = str(numero)
        escala_fuente = radio / 22
        (tw, th), _ = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, escala_fuente, 2)
        origen = (int(centro[0] - tw / 2), int(centro[1] + th / 2))
        cv2.putText(lienzo, texto, origen, cv2.FONT_HERSHEY_SIMPLEX, escala_fuente, (0, 0, 0), 3, cv2.LINE_AA)
    for poligono in extra or []:
        pts = np.round(ordenar_esquinas(poligono) * escala).astype(np.int32)
        rojo = (230, 0, 0)
        cv2.polylines(lienzo, [pts], True, rojo, grosor + 1, cv2.LINE_AA)
        cv2.line(lienzo, tuple(int(v) for v in pts[0]), tuple(int(v) for v in pts[2]), rojo, grosor, cv2.LINE_AA)
        cv2.line(lienzo, tuple(int(v) for v in pts[1]), tuple(int(v) for v in pts[3]), rojo, grosor, cv2.LINE_AA)
    return codificar_jpeg(lienzo, calidad=calidad)
