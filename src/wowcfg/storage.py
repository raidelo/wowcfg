"""Ubicación de los datos propios de wowcfg.

Por defecto se usa el directorio de aplicación del sistema
(`~/.config/wowcfg` en Linux, `%APPDATA%\\wowcfg` en Windows,
`~/Library/Application Support/wowcfg` en macOS). La variable de entorno
`WOWCFG_HOME` permite cambiarlo (útil para pruebas).
"""

import json
import os
from pathlib import Path
from typing import Any

import typer

APP_NAME = "wowcfg"


def home() -> Path:
    override = os.environ.get("WOWCFG_HOME")
    if override:
        return Path(override)
    return Path(typer.get_app_dir(APP_NAME))


def config_file() -> Path:
    return home() / "config.json"


def roster_file() -> Path:
    return home() / "characters.json"


def template_dir() -> Path:
    """Clon local del repositorio de configuración."""
    return home() / "template"


def backups_dir() -> Path:
    return home() / "backups"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    """Escribe JSON de forma atómica (archivo temporal + reemplazo)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    os.replace(tmp, path)
