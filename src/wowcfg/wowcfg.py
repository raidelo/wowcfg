#!/usr/bin/env python3
import argparse
import datetime
import json
import shutil
import subprocess
from pathlib import Path

from wowcfg.constants import (
    ACCOUNT_CONFIG,
    BACKUPS,
    CHARACTERS_CONFIG,
    CONFIG_FILE,
    PERFIL,
    REPO,
)
from wowcfg.utils import (
    accounts,
    assign_profile,
    backup,
    characters,
    die,
    get_accounts_path,
    get_config_repo,
    is_wow_open,
    read,
    write,
)


def init(args: argparse.Namespace) -> None:
    with CONFIG_FILE.open("w") as f:
        json.dump({"wow_path": args.path.as_posix(), "repo": args.repo}, f)


def fetch(args: argparse.Namespace) -> None:
    repo = get_config_repo()
    subprocess.Popen(f"git clone {repo} {REPO}".split()).wait()


def apply(args):
    if is_wow_open():
        die("Cierra WoW antes de aplicar (al salir sobrescribiria los cambios).")
    archivos_cuenta = (
        sorted(ACCOUNT_CONFIG.glob("*.lua")) if ACCOUNT_CONFIG.is_dir() else []
    )
    archivos_pj = (
        sorted(CHARACTERS_CONFIG.glob("*.lua")) if CHARACTERS_CONFIG.is_dir() else []
    )
    if not archivos_cuenta and not archivos_pj:
        die("La plantilla esta vacia. Usa 'capture' o copia tus .lua a plantilla/.")

    bdir = BACKUPS / datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    total_pj = 0

    for cuenta in accounts():
        pjs = characters(cuenta)
        claves = [f"{pj} - {reino}" for reino, pj, _ in pjs]
        total_pj += len(pjs)

        for src in archivos_cuenta:
            dst = cuenta / "SavedVariables" / src.name
            backup(dst, bdir)
            write(dst, assign_profile(read(src), claves))

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
    cuenta = get_accounts_path() / args.cuenta if args.cuenta else cs[0]
    if not cuenta.is_dir():
        die(f"No existe la cuenta {cuenta.name}")
    ACCOUNT_CONFIG.mkdir(parents=True, exist_ok=True)
    n = 0
    for src in sorted((cuenta / "SavedVariables").glob("*.lua")):
        shutil.copy2(src, ACCOUNT_CONFIG / src.name)
        n += 1
    print(f"Capturados {n} archivo(s) de la cuenta {cuenta.name} en plantilla/cuenta/.")
    print("Borra de ahi los addons que no quieras aplicar.")


def main():
    p = argparse.ArgumentParser(description="Plantilla de config de addons de WoW")
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("init")
    i.add_argument("path", type=Path, help="carpeta del WoW")
    i.add_argument("repo", help="repositorio que contiene la configuracion")

    sub.add_parser("fetch")

    sub.add_parser("apply")

    c = sub.add_parser("capture")
    c.add_argument(
        "cuenta", nargs="?", help="carpeta de la cuenta (por defecto la primera)"
    )

    args = p.parse_args()

    {"init": init, "fetch": fetch, "apply": apply, "capture": capture}[args.cmd](args)


if __name__ == "__main__":
    main()
