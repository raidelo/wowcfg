#!/usr/bin/env python3
import argparse
import datetime
import subprocess
import sys
from pathlib import Path
from shutil import rmtree

from wowcfg.config import Config, get_config
from wowcfg.constants import (
    BACKUPS,
    CONFIG_FILE,
    REPO,
)
from wowcfg.roster import (
    Account,
    Class_,
    get_character_class,
    get_roster,
    save_roster,
    set_character_class,
)
from wowcfg.ui import die
from wowcfg.utils import (
    assign_profile_keys,
    backup,
    is_wow_open,
    list_accounts,
    list_characters,
    read,
    write,
)


def init(path: Path, repo: str) -> None:
    path = path.resolve()
    with CONFIG_FILE.open("w") as f:
        f.write(Config(paths=[path], repo=repo).model_dump_json(indent=2))


def fetch() -> None:
    config = get_config()
    if REPO.exists():
        rmtree(REPO)
    subprocess.run(["git", "clone", config.repo, REPO.as_posix()], check=True)


def apply() -> None:
    if is_wow_open():
        die("Cierra WoW antes de aplicar (al salir sobrescribiría los cambios).")

    config = get_config()

    if not REPO.exists():
        ask_for_fetch()

    bdir = BACKUPS / datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    total_chars = 0

    roster = get_roster()

    for wow_path in config.paths:
        if not wow_path.exists():
            print(f"La ruta al WoW es inválida ({wow_path.as_posix()})")
            continue

        apply_global_config(config, wow_path, bdir)

        for account in list_accounts(wow_path):
            chars = list_characters(account)
            total_chars += len(chars)

            keys = [f"{pj} - {reino}" for reino, pj, _ in chars]

            apply_config_by_account(account, keys, wow_path, bdir)

            apply_config_by_character(account, chars, roster, wow_path, bdir)

            print(f"  {account.name}: {len(chars)} personaje(s)")

    print("Operación terminada con éxito!")
    print(f"Copia de seguridad en: {bdir}")


def register(account: str, realm: str, character: str, class_: Class_) -> None:
    class_mappings = get_roster()

    set_character_class(class_mappings, account, realm, character, class_)

    save_roster(class_mappings)


def add_path(wow_path: Path) -> None:
    config = get_config()
    config.paths.append(wow_path.resolve())

    with CONFIG_FILE.open("w") as f:
        f.write(config.model_dump_json(indent=2))


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

    a = sub.add_parser("add-path")
    a.add_argument("path", type=Path, help="carpeta del WoW")

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
        case "add-path":
            add_path(args.path)


def apply_global_config(config: Config, wow_path: Path, bdir: Path) -> None:
    src = REPO / "outer" / "Config.wtf"
    dst = wow_path / "WTF" / src.name
    backup(dst, wow_path, bdir)
    write(dst, read(src))


def apply_config_by_account(
    account: Path, keys: list[str], wow_path: Path, bdir: Path
) -> None:
    for src in (REPO / "SavedVariables").iterdir():
        dst = account / "SavedVariables" / src.name
        backup(dst, wow_path, bdir)
        write(dst, assign_profile_keys(read(src), keys))

    for src in REPO.iterdir():
        if not src.is_file():
            continue
        dst = account / src.name
        backup(dst, wow_path, bdir)
        write(dst, read(src))


def apply_config_by_character(
    account: Path,
    chars: list[tuple[str, str, Path]],
    roster: list[Account],
    wow_path: Path,
    bdir: Path,
) -> None:
    for realm, name, folder in chars:
        character_class = get_character_class(roster, account.name, realm, name)
        if character_class is None:
            continue
        for class_template in (REPO / "Characters").iterdir():
            if (
                class_template.name != "common"
                and class_template.name != character_class
            ):
                continue

            for src in (class_template / "SavedVariables").iterdir():
                dst = folder / "SavedVariables" / src.name
                backup(dst, wow_path, bdir)
                write(dst, read(src))

            for src in class_template.iterdir():
                if not src.is_file():
                    continue
                dst = folder / src.name
                backup(dst, wow_path, bdir)
                write(dst, read(src))


def ask_for_fetch() -> None:
    print(
        "El repositorio de configuración no existe. Te gustaría descargarlo y aplicarlo? (Y/n) ",
        end="",
        flush=True,
    )

    if (input().lower().strip() or "y") != "y":
        sys.exit(1)

    fetch()


if __name__ == "__main__":
    main()
