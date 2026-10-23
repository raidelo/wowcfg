import os
import subprocess
import sys
from pathlib import Path
from typing import NoReturn


def die(msg: str) -> NoReturn:
    print(f"ERROR: {msg}")
    sys.exit(1)


def read(p: Path) -> str:
    with open(p, "r", encoding="utf-8", newline="") as f:
        return f.read()


def write(p: Path, t: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(t)


def characters(cuenta: Path) -> list[tuple[str, str, Path]]:
    """[(reino, personaje, carpeta)] de una cuenta."""
    res = []
    for reino in sorted(cuenta.iterdir()):
        if not reino.is_dir() or reino.name == "SavedVariables":
            continue
        for pj in sorted(reino.iterdir()):
            if pj.is_dir():
                res.append((reino.name, pj.name, pj))
    return res


def is_wow_open() -> bool:
    try:
        cmd = ["tasklist"] if os.name == "nt" else ["ps", "-A"]
        out = subprocess.run(
            cmd, capture_output=True, text=True, check=False
        ).stdout.lower()
    except Exception:
        return False
    return "wow.exe" in out or "wow-64.exe" in out
