"""Configuración de wowcfg (`config.json`)."""

import os
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from wowcfg import WowcfgError, storage

DEFAULT_REPO = "https://github.com/raidelo/wow-config"
DEFAULT_PROFILE = "main"


class Config(BaseModel):
    repo: str = DEFAULT_REPO
    """URL del repositorio git con la plantilla."""

    ref: str | None = None
    """Rama o tag a usar. `None` usa la rama por defecto del repo."""

    profile: str = DEFAULT_PROFILE
    """Perfil de AceDB que se asigna a todos los personajes en `profileKeys`."""

    paths: list[Path] = Field(default_factory=list)
    """Instalaciones de WoW (carpetas que contienen `WTF/`)."""

    def has_path(self, path: Path) -> bool:
        return any(same_path(p, path) for p in self.paths)


def same_path(a: Path, b: Path) -> bool:
    """Compara rutas resueltas; en Windows sin distinguir mayúsculas."""
    a, b = a.resolve(), b.resolve()
    try:
        return a.samefile(b)
    except OSError:  # alguna de las dos ya no existe
        if os.name == "nt":
            return str(a).casefold() == str(b).casefold()
        return a == b


def exists() -> bool:
    return storage.config_file().is_file()


def load() -> Config:
    path = storage.config_file()
    if not path.is_file():
        raise WowcfgError("No hay configuración. Ejecuta `wowcfg init` primero.")
    try:
        return Config.model_validate(storage.read_json(path))
    except (ValidationError, ValueError) as e:
        raise WowcfgError(f"{path} no es válido:\n{e}") from e


def save(config: Config) -> None:
    storage.write_json(storage.config_file(), config.model_dump(mode="json"))
