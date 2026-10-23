#!/usr/bin/env python3
import argparse
import datetime
import subprocess
import sys
from pathlib import Path

from wowcfg.config import Config, get_config
from wowcfg.constants import (
    ACCOUNT_CONFIG,
    BACKUPS,
    CONFIG_FILE,
    PROFILE,
    REPO,
)
from wowcfg.roster import (
    Class_,
    get_character_class,
    get_roster,
    save_roster,
    set_character_class,
)
from wowcfg.ui import die
from wowcfg.utils import (
    assign_profile,
    backup,
    characters,
    is_wow_open,
    read,
    user_accounts,
    write,
)


def init(path: Path, repo: str) -> None:
    with CONFIG_FILE.open("w") as f:
        f.write(Config(path=path, repo=repo).model_dump_json(indent=2))


def fetch() -> None:
    config = get_config()
    subprocess.run(["git", "clone", config.repo, str(REPO)], check=True)


def apply() -> None:
    if is_wow_open():
        die("Cierra WoW antes de aplicar (al salir sobrescribiria los cambios).")

    config = get_config()

    if not config.path.exists():
        die(f"La ruta al WoW es inválida ({config.path.as_posix()})")

    if not REPO.exists():
        print(
            "El repositorio de configuración no existe. Te gustaría descargarlo y aplicarlo? (Y/n) ",
            end="",
            flush=True,
        )

        if (input().lower().strip() or "y") != "y":
            sys.exit(1)

        fetch()

    account_config = (
        sorted(ACCOUNT_CONFIG.glob("*.lua")) if ACCOUNT_CONFIG.is_dir() else []
    )

    if not account_config:
        die("La plantilla esta vacia.")

    bdir = BACKUPS / datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    total_chars = 0

    roster = get_roster()

    for account in user_accounts():
        chars = characters(account)
        keys = [f"{pj} - {reino}" for reino, pj, _ in chars]
        total_chars += len(chars)

        for src in account_config:
            dst = account / "SavedVariables" / src.name
            backup(dst, bdir)
            write(dst, assign_profile(read(src), keys))

        for realm, name, folder in chars:
            class_ = get_character_class(roster, account.name, realm, name)
            if class_ is None:
                continue
            for class_template in (REPO / "Characters").iterdir():
                if class_template.name != class_.value:
                    continue

                for src in (class_template / "SavedVariables").iterdir():
                    dst = folder / "SavedVariables" / src.name
                    backup(dst, bdir)
                    write(dst, read(src))

        print(f"  {account.name}: {len(chars)} personaje(s)")

    print(
        f"Listo: {len(account_config)} archivo(s) aplicados "
        f"a {total_chars} personaje(s), perfil '{PROFILE}'."
    )
    print(f"Copia de seguridad en: {bdir}")


def register(account: str, realm: str, character: str, class_: Class_) -> None:
    class_mappings = get_roster()

    set_character_class(class_mappings, account, realm, character, class_)

    save_roster(class_mappings)


def main():
    p = argparse.ArgumentParser(description="Plantilla de config de addons de WoW")
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("init")
    i.add_argument("path", type=Path, help="carpeta del WoW")
    i.add_argument("repo", help="repositorio que contiene la configuracion")

    sub.add_parser("fetch")

    sub.add_parser("apply")

    r = sub.add_parser("register")
    r.add_argument("account")
    r.add_argument("realm")
    r.add_argument("character")
    r.add_argument("class_", type=Class_)

    args = p.parse_args()

    match args.cmd:
        case "init":
            init(args.path, args.repo)
        case "fetch":
            fetch()
        case "apply":
            apply()
        case "register":
            register(args.account, args.realm, args.character, args.class_)


if __name__ == "__main__":
    main()
