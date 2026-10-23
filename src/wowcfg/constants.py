import re
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "wowcfg"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = CONFIG_DIR / "config.json"
BACKUPS = CONFIG_DIR / "backups"

REPO = CONFIG_DIR / "wow-config"

ACCOUNT_CONFIG = REPO / "SavedVariables"
CHARACTERS_CONFIG = REPO / "characters"

PERFIL = "main"

PK_RE = re.compile(r'(\["profileKeys"\]\s*=\s*\{)([^{}]*)(\})')
