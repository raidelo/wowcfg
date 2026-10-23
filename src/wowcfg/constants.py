import re
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "wowcfg"
CONFIG_FILE = CONFIG_DIR / "config.json"

REPO = Path(__file__).resolve().parent
PLANTILLA_CUENTA = REPO / "plantilla" / "cuenta"
PLANTILLA_PJ = REPO / "plantilla" / "personaje"
BACKUPS = REPO / "backups"

PERFIL = "main"

PK_RE = re.compile(r'(\["profileKeys"\]\s*=\s*\{)([^{}]*)(\})')
