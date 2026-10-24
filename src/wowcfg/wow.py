"""Lectura de la estructura `WTF/` de una instalación de WoW."""

import csv
import io
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

WOW_PROCESSES = {"wow.exe", "wow-64.exe", "wow_tweaked.exe"}


@dataclass(frozen=True)
class CharacterDir:
    install: Path
    account: str
    realm: str
    name: str
    path: Path

    @property
    def profile_key(self) -> str:
        """Clave que usa AceDB en `profileKeys`."""
        return f"{self.name} - {self.realm}"

    @property
    def label(self) -> str:
        return f"{self.name} - {self.realm} ({self.account})"


def wtf_dir(install: Path) -> Path:
    return install / "WTF"


def accounts_dir(install: Path) -> Path:
    return wtf_dir(install) / "Account"


def list_accounts(install: Path) -> list[Path]:
    """Carpetas de cuenta de una instalación (vacío si aún no hay ninguna)."""
    root = accounts_dir(install)
    if not root.is_dir():
        return []
    return sorted(
        (d for d in root.iterdir() if d.is_dir()), key=lambda d: d.name.lower()
    )


def list_characters(install: Path, account: Path) -> list[CharacterDir]:
    chars = []
    for realm in sorted(account.iterdir(), key=lambda d: d.name.lower()):
        if not realm.is_dir() or realm.name == "SavedVariables":
            continue
        for char in sorted(realm.iterdir(), key=lambda d: d.name.lower()):
            if char.is_dir():
                chars.append(
                    CharacterDir(install, account.name, realm.name, char.name, char)
                )
    return chars


def scan(installs: list[Path]) -> list[CharacterDir]:
    """Todos los personajes de todas las instalaciones."""
    return [
        c
        for install in installs
        for account in list_accounts(install)
        for c in list_characters(install, account)
    ]


def running_processes() -> set[str]:
    """Nombres (en minúsculas) de los procesos en ejecución."""
    try:
        if os.name == "nt":
            out = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                check=False,
            ).stdout
            return {row[0].lower() for row in csv.reader(io.StringIO(out)) if row}
        out = subprocess.run(
            ["ps", "-A", "-o", "comm="], capture_output=True, text=True, check=False
        ).stdout
        return {
            Path(line.strip()).name.lower() for line in out.splitlines() if line.strip()
        }
    except OSError:
        return set()


def is_wow_running() -> bool:
    return bool(running_processes() & WOW_PROCESSES)
