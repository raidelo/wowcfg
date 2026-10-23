#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NoReturn


def die(msg: str) -> NoReturn:
    print(f"ERROR: {msg}")
    sys.exit(1)


def get_wow_path() -> Path | None:
    with CONFIG_FILE.open("r") as f:
        obj = json.load(f)
        if isinstance(obj, dict) and (path := obj.get("wow_path")):
            if path is None:
                return None
            elif isinstance(path, str):
                return Path(path).resolve()

    die("Formato del archivo de configuracion invalido.")


# ======================= CONFIGURACION =======================

# Carpeta raiz del cliente (donde esta Wow.exe)
WOW_PATH = get_wow_path()
if WOW_PATH is None:
    die(
        "No existe la ruta al WoW.\nEjecute `wowcfg init <WOW_PATH>` para añadirlo a la configuracion."
    )

# Archivo de configuracion
CONFIG_DIR = Path.home() / ".config" / "wowcfg"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Nombre del perfil que usaran todos los personajes en Bartender, SUF y
# demas addons con perfiles. Tiene que existir en la plantilla.
PERFIL = "main"

# =============================================================

REPO = Path(__file__).resolve().parent
PLANTILLA_CUENTA = REPO / "plantilla" / "cuenta"
PLANTILLA_PJ = REPO / "plantilla" / "personaje"
BACKUPS = REPO / "backups"
ACCOUNTS = Path(WOW_PATH) / "WTF" / "Account"

PK_RE = re.compile(r'(\["profileKeys"\]\s*=\s*\{)([^{}]*)(\})')


def is_wow_open() -> bool:
    try:
        cmd = ["tasklist"] if os.name == "nt" else ["ps", "-A"]
        out = subprocess.run(
            cmd, capture_output=True, text=True, check=False
        ).stdout.lower()
    except Exception:
        return False
    return "wow.exe" in out or "wow-64.exe" in out


def accounts() -> list[Path]:
    if not ACCOUNTS.is_dir():
        die(f"No existe {ACCOUNTS}.")
    return [d for d in sorted(ACCOUNTS.iterdir()) if d.is_dir()]


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


def asignar_perfil(texto: str, claves: list[str]) -> str:
    """Rehace cada tabla profileKeys para que contenga solo los personajes
    de esta cuenta, todos apuntando a PERFIL."""
    nl = "\r\n" if "\r\n" in texto else "\n"

    def repl(m: re.Match[str]) -> str:
        head, body, close = m.groups()
        ind = re.search(r"\n([ \t]*)$", body)
        ind = ind.group(1) if ind else ""
        lineas = "".join(f'{nl}{ind}\t["{k}"] = "{PERFIL}",' for k in claves)
        return head + lineas + nl + ind + close

    return PK_RE.sub(repl, texto)


def read(p: Path) -> str:
    with open(p, "r", encoding="utf-8", newline="") as f:
        return f.read()


def write(p: Path, t: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(t)


def backup(destino: Path, bdir: Path) -> None:
    if destino.is_file():
        rel = destino.relative_to(ACCOUNTS)
        (bdir / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(destino, bdir / rel)


def init(args: argparse.Namespace) -> None:
    with CONFIG_FILE.open("w") as f:
        json.dump({"wow_path": args.path}, f)


def apply(args):
    if is_wow_open():
        die("Cierra WoW antes de aplicar (al salir sobrescribiria los cambios).")
    archivos_cuenta = (
        sorted(PLANTILLA_CUENTA.glob("*.lua")) if PLANTILLA_CUENTA.is_dir() else []
    )
    archivos_pj = sorted(PLANTILLA_PJ.glob("*.lua")) if PLANTILLA_PJ.is_dir() else []
    if not archivos_cuenta and not archivos_pj:
        die("La plantilla esta vacia. Usa 'capturar' o copia tus .lua a plantilla/.")

    bdir = BACKUPS / datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    total_pj = 0

    for cuenta in accounts():
        pjs = characters(cuenta)
        claves = [f"{pj} - {reino}" for reino, pj, _ in pjs]
        total_pj += len(pjs)

        for src in archivos_cuenta:
            dst = cuenta / "SavedVariables" / src.name
            backup(dst, bdir)
            write(dst, asignar_perfil(read(src), claves))

        for reino, pj, carpeta in pjs:
            for src in archivos_pj:
                dst = carpeta / "SavedVariables" / src.name
                backup(dst, bdir)
                write(dst, read(src))

        print(f"  {cuenta.name}: {len(pjs)} personaje(s)")

    print(
        f"Listo: {len(archivos_cuenta) + len(archivos_pj)} archivo(s) aplicados "
        f"a {total_pj} personaje(s), perfil '{PERFIL}'."
    )
    print(f"Copia de lo anterior en: {bdir}")


def capture(args):
    if is_wow_open():
        print("AVISO: WoW esta abierto; puede que la config no este guardada aun.")
    cs = accounts()
    cuenta = ACCOUNTS / args.cuenta if args.cuenta else cs[0]
    if not cuenta.is_dir():
        die(f"No existe la cuenta {cuenta.name}")
    PLANTILLA_CUENTA.mkdir(parents=True, exist_ok=True)
    n = 0
    for src in sorted((cuenta / "SavedVariables").glob("*.lua")):
        shutil.copy2(src, PLANTILLA_CUENTA / src.name)
        n += 1
    print(f"Capturados {n} archivo(s) de la cuenta {cuenta.name} en plantilla/cuenta/.")
    print("Borra de ahi los addons que no quieras aplicar.")


def main():
    p = argparse.ArgumentParser(description="Plantilla de config de addons de WoW")
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("init")
    i.add_argument("path", type=Path, help="carpeta del WoW")

    sub.add_parser("aplicar")

    c = sub.add_parser("capturar")
    c.add_argument(
        "cuenta", nargs="?", help="carpeta de la cuenta (por defecto la primera)"
    )

    args = p.parse_args()

    {"init": init, "aplicar": apply, "capturar": capture}[args.cmd](args)


if __name__ == "__main__":
    main()
