from pathlib import Path

from pydantic import BaseModel, ValidationError

from wowcfg.constants import CONFIG_FILE
from wowcfg.ui import die


class Config(BaseModel):
    path: Path
    repo: str


def load_config() -> Config:
    with CONFIG_FILE.open("r") as f:
        return Config.model_validate_json(f.read())


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        try:
            config = load_config()
        except FileNotFoundError:
            die(
                "El archivo de configuración no existe."
                + "\nEjecuta el commando `init` para crearlo."
            )
        except ValidationError as e:
            die(str(e))

        _config = config
    return _config
