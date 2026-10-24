import os
import re
import shutil
import subprocess
from pathlib import Path

from wowcfg.constants import PK_RE, PROFILE
from wowcfg.ui import die


def read(p: Path) -> str:
    """Reads and returns the content of a file."""
    with open(p, "r", encoding="utf-8", newline="") as f:
        return f.read()


def write(p: Path, t: str) -> None:
    """Writes the given content into a file."""
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(t)


def is_wow_open() -> bool:
    """Returns `True` if there is an isinstance of World
    of Warcraft is open in the system, `False` otherwise."""
    try:
        cmd = ["tasklist"] if os.name == "nt" else ["ps", "-A"]
        out = subprocess.run(
            cmd, capture_output=True, text=True, check=False
        ).stdout.lower()
    except Exception:  # noqa: BLE001
        return False
    return "wow.exe" in out or "wow-64.exe" in out


def get_accounts_path(wow_path: Path) -> Path:
    """Returns the path that contains all user accounts."""
    return wow_path / "WTF" / "Account"


def list_accounts(wow_path: Path) -> list[Path]:
    """Lists the user accounts."""
    accounts = get_accounts_path(wow_path)
    if not accounts.is_dir():
        die(f"No existe {accounts}.")
    return [d for d in sorted(accounts.iterdir()) if d.is_dir()]


def list_characters(account: Path) -> list[tuple[str, str, Path]]:
    """[(realm, character, folder)] of an account."""
    res = []
    for realm in sorted(account.iterdir()):
        if not realm.is_dir() or realm.name == "SavedVariables":
            continue
        for char in sorted(realm.iterdir()):
            if char.is_dir():
                res.append((realm.name, char.name, char))
    return res


def assign_profile_keys(texto: str, claves: list[str]) -> str:
    """Re-creates each `profileKeys` so that it only contains
    all the characters for that particular account, and asign
    them the `PERFIL` profile."""
    nl = "\r\n" if "\r\n" in texto else "\n"

    def repl(m: re.Match[str]) -> str:
        head, body, close = m.groups()
        ind = re.search(r"\n([ \t]*)$", body)
        ind = ind.group(1) if ind else ""
        lineas = "".join(f'{nl}{ind}\t["{k}"] = "{PROFILE}",' for k in claves)
        return head + lineas + nl + ind + close

    return PK_RE.sub(repl, texto)


def backup(destino: Path, wow_path: Path, bdir: Path) -> None:
    """Creates a backup for the existing WoW configuration."""
    if destino.is_file():
        rel = destino.relative_to(wow_path)
        (bdir / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(destino, bdir / rel)
