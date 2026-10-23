import re
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "wowcfg"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

ROSTER_FILE = CONFIG_DIR / "classes.json"
CONFIG_FILE = CONFIG_DIR / "config.json"
BACKUPS = CONFIG_DIR / "backups"

REPO = CONFIG_DIR / "wow-config"

PROFILE = "main"

PK_RE = re.compile(r'(\["profileKeys"\]\s*=\s*\{)([^{}]*)(\})')
