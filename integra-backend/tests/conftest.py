"""Configuracion de pruebas: hace importable `src/` y fija el cwd en la raiz.

Asi los tests pueden `from core...` y abrir rutas relativas (p. ej. src/schemas/)
desde la raiz del proyecto sin depender de desde donde se invoque pytest.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SRC = RAIZ / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Rutas relativas de los tests (src/schemas/...) se resuelven desde la raiz.
os.chdir(RAIZ)
