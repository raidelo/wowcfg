#!/usr/bin/env python3
import argparse
import datetime
import json
import subprocess
from pathlib import Path

from wowcfg.constants import (
    ACCOUNT_CONFIG,
    BACKUPS,
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

    account_config = (
        sorted(ACCOUNT_CONFIG.glob("*.lua")) if ACCOUNT_CONFIG.is_dir() else []
    )

    if not account_config:
        die("La plantilla esta vacia.")

    bdir = BACKUPS / datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    total_chars = 0

    for account in accounts():
        chars = characters(account)
        keys = [f"{pj} - {reino}" for reino, pj, _ in chars]
        total_chars += len(chars)

        for src in account_config:
            dst = account / "SavedVariables" / src.name
            backup(dst, bdir)
            write(dst, assign_profile(read(src), keys))

        print(f"  {account.name}: {len(chars)} personaje(s)")

    print(
        f"Listo: {len(account_config)} archivo(s) aplicados "
        f"a {total_chars} personaje(s), perfil '{PERFIL}'."
    )
    print(f"Copia de seguridad en: {bdir}")


def main():
    p = argparse.ArgumentParser(description="Plantilla de config de addons de WoW")
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("init")
    i.add_argument("path", type=Path, help="carpeta del WoW")
    i.add_argument("repo", help="repositorio que contiene la configuracion")

    sub.add_parser("fetch")

    sub.add_parser("apply")

    args = p.parse_args()

    {"init": init, "fetch": fetch, "apply": apply}[args.cmd](args)


if __name__ == "__main__":
    main()
