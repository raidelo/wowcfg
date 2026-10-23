import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from wowcfg.constants import CONFIG_FILE
from wowcfg.ui import die


@dataclass
class Config:
    path: Path
    repo: str


class ConfigError(Enum):
    NOT_FOUND = 0
    INVALID_FORMAT = 1
    MISSING_PATH = 2
    MISSING_REPO = 3


def load_config() -> Config | ConfigError:
    if not CONFIG_FILE.exists():
        return ConfigError.NOT_FOUND

    with CONFIG_FILE.open("r") as f:
        obj = json.load(f)
        if isinstance(obj, dict):
            path = obj.get("wow_path")
            if path is None:
                return ConfigError.MISSING_PATH
            repo = obj.get("repo")
            if repo is None:
                return ConfigError.MISSING_REPO
            path = Path(path).resolve()
            return Config(path, repo)

    return ConfigError.INVALID_FORMAT


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        config = load_config()

        if isinstance(config, ConfigError):
            match config:
                case ConfigError.NOT_FOUND:
                    msg = "El archivo de configuración no existe."
                case ConfigError.INVALID_FORMAT:
                    msg = "El archivo de configuración tiene un formato inválido."
                case ConfigError.MISSING_PATH:
                    msg = "Falta el key `wow_path` en el archivo de configuración."
                case ConfigError.MISSING_REPO:
                    msg = "Falta el key `repo` en el archivo de configuración."
            die(msg)

        _config = config
    return _config
