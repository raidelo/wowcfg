import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

from .constants import CONFIG_FILE, PERFIL, PK_RE


def die(msg: str) -> NoReturn:
    """Exits the app with the given error message."""
    print(f"ERROR: {msg}")
    sys.exit(1)


def read(p: Path) -> str:
    """Reads and returns the content of a file."""
    with open(p, "r", encoding="utf-8", newline="") as f:
        return f.read()


def write(p: Path, t: str) -> None:
    """Writes the given content into a file."""
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(t)


def characters(cuenta: Path) -> list[tuple[str, str, Path]]:
    """[(reino, personaje, carpeta)] of an account."""
    res = []
    for reino in sorted(cuenta.iterdir()):
        if not reino.is_dir() or reino.name == "SavedVariables":
            continue
        for pj in sorted(reino.iterdir()):
            if pj.is_dir():
                res.append((reino.name, pj.name, pj))
    return res


def is_wow_open() -> bool:
    """Returns `True` if there is an isinstance of World
    of Warcraft is open in the system, `False` otherwise."""
    try:
        cmd = ["tasklist"] if os.name == "nt" else ["ps", "-A"]
        out = subprocess.run(
            cmd, capture_output=True, text=True, check=False
        ).stdout.lower()
    except Exception:
        return False
    return "wow.exe" in out or "wow-64.exe" in out


def get_wow_path() -> Path:
    """Returns the World of Warcraft installation path
    from the config file."""
    with CONFIG_FILE.open("r") as f:
        obj = json.load(f)
        if isinstance(obj, dict) and (path := obj.get("wow_path")):
            if path is None:
                die(
                    "No existe la ruta al WoW.\nEjecute `wowcfg init <WOW_PATH> <REPO>` para añadirlo a la configuracion."
                )
            elif isinstance(path, str):
                return Path(path).resolve()

    die("Formato del archivo de configuracion invalido.")


def get_config_repo() -> str:
    """Returns the World of Warcraft configuration
    repository path from the config file."""
    with CONFIG_FILE.open("r") as f:
        obj = json.load(f)
        if isinstance(obj, dict) and (repo := obj.get("repo")):
            if repo is None:
                die(
                    "No existe el repositorio con la configuracion.\nEjecute `wowcfg init <WOW_PATH> <REPO>` para añadirlo a la configuracion."
                )
            elif isinstance(repo, str):
                return repo

    die("Formato del archivo de configuracion invalido.")


def get_accounts_path() -> Path:
    """Returns the path that contains all user accounts."""
    return Path(get_wow_path()) / "WTF" / "Account"


def assign_profile(texto: str, claves: list[str]) -> str:
    """Re-creates each `profileKeys` so that it only contains
    all the characters for that particular account, and asign
    them the `PERFIL` profile."""
    nl = "\r\n" if "\r\n" in texto else "\n"

    def repl(m: re.Match[str]) -> str:
        head, body, close = m.groups()
        ind = re.search(r"\n([ \t]*)$", body)
        ind = ind.group(1) if ind else ""
        lineas = "".join(f'{nl}{ind}\t["{k}"] = "{PERFIL}",' for k in claves)
        return head + lineas + nl + ind + close

    return PK_RE.sub(repl, texto)


def accounts() -> list[Path]:
    """Lists the user accounts."""
    accounts = get_accounts_path()
    if not accounts.is_dir():
        die(f"No existe {accounts}.")
    return [d for d in sorted(accounts.iterdir()) if d.is_dir()]


def backup(destino: Path, bdir: Path) -> None:
    """Creates a backup for the existing WoW configuration."""
    if destino.is_file():
        rel = destino.relative_to(get_accounts_path())
        (bdir / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(destino, bdir / rel)
