"""Punto 1: prompts/ y schemas/ se resuelven relativos al paquete, no a RAIZ.

Simula el layout que deja `sam build` (el contenido de src/ queda SIN el nivel src/:
/var/task/core/llm.py, /var/task/prompts/, /var/task/schemas/) copiando esas carpetas a
un directorio temporal, cargando llm.py desde ahi con importlib y verificando que
PROMPTS_DIR/SCHEMAS_DIR apuntan dentro del tmp y que cargan los 3 prompts y 3 esquemas.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SRC = RAIZ / "src"
PROMPTS = ("separar_identificar", "extraer_conductas", "clasificar")
ESQUEMAS = ("separar_identificar", "extraer_conductas", "clasificar")


def _limpiar_core() -> None:
    for mod in [m for m in list(sys.modules) if m == "core" or m.startswith("core.")]:
        del sys.modules[mod]


def _cargar_llm_desde(base: Path):
    """Carga el paquete 'core' (y core.llm) desde `base`, como lo haria Lambda.

    Se inserta `base` al frente de sys.path y se re-importa 'core' desde ahi (no desde el
    src/ del repo). Los modulos se registran en sys.modules para que @dataclass funcione.
    """
    sys.path.insert(0, str(base))
    _limpiar_core()
    try:
        import importlib

        return importlib.import_module("core.llm")
    finally:
        sys.path.remove(str(base))
        _limpiar_core()


def test_prompts_y_esquemas_cargan_en_layout_de_build(tmp_path: Path, monkeypatch) -> None:
    # Credenciales/region ficticias: config no debe exigir AWS para importar llm.
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")

    # Copiar el contenido de src/ (core, prompts, schemas) SIN el nivel src/.
    shutil.copytree(SRC / "core", tmp_path / "core")
    shutil.copytree(SRC / "prompts", tmp_path / "prompts")
    shutil.copytree(SRC / "schemas", tmp_path / "schemas")

    llm = _cargar_llm_desde(tmp_path)

    # Las rutas se resuelven DENTRO del tmp (no en RAIZ del repo).
    assert llm.PROMPTS_DIR == tmp_path / "prompts"
    assert llm.SCHEMAS_DIR == tmp_path / "schemas"
    assert "src" not in llm.PROMPTS_DIR.parts  # no quedo el nivel src/

    # Cargan los 3 prompts (system+user) y los 3 esquemas.
    for pid in PROMPTS:
        system, user, version = llm.cargar_prompt(pid)
        assert system and user and version
    for nombre in ESQUEMAS:
        esquema = llm.cargar_esquema(nombre)
        assert isinstance(esquema, dict) and esquema
