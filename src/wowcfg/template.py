"""Repositorio de plantilla: descarga y estructura.

Estructura esperada del repositorio::

    outer/Config.wtf                -> WTF/Config.wtf
    SavedVariables/*.lua            -> WTF/Account/<cuenta>/SavedVariables/
    bindings-cache.wtf, ...         -> WTF/Account/<cuenta>/
    Characters/common/...           -> cada personaje
    Characters/<clase>/...          -> personajes de esa clase (después de common)

Dentro de `Characters/<x>/` se aplica la misma idea: `SavedVariables/*.lua`
va a la carpeta `SavedVariables` del personaje y los archivos sueltos a la
carpeta del personaje.

Solo se copian los archivos sueltos cuyo nombre WoW reconoce, para que un
README o LICENSE del repo no acabe dentro de `WTF/`.
"""

import os
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from wowcfg import WowcfgError, storage
from wowcfg.roster import Class_

COMMON = "common"

WOW_FILES = {
    "addons.txt",
    "bindings-cache.wtf",
    "chat-cache.txt",
    "config-cache.wtf",
    "layout-local.txt",
    "macros-cache.txt",
}

REPO_DOCS = {"README", "LICENSE", "CHANGELOG", "COPYING"}


@dataclass
class Layer:
    """Un conjunto de archivos que va a una misma carpeta de WoW."""

    files: list[Path] = field(default_factory=list)
    saved_variables: list[Path] = field(default_factory=list)


@dataclass
class Template:
    root: Path
    global_config: Path | None
    account: Layer
    common: Layer
    classes: dict[Class_, Layer]
    warnings: list[str]


def _is_wow_file(p: Path) -> bool:
    return p.is_file() and p.name.lower() in WOW_FILES


def _is_repo_doc(p: Path) -> bool:
    """Archivos propios del repositorio que se ignoran sin avisar."""
    return p.name.startswith(".") or p.stem.upper() in REPO_DOCS


def _read_layer(folder: Path, root: Path, warnings: list[str]) -> Layer:
    layer = Layer()
    if not folder.is_dir():
        return layer
    for p in sorted(folder.iterdir()):
        if not p.is_file() or _is_repo_doc(p):
            continue
        if _is_wow_file(p):
            layer.files.append(p)
        else:
            warnings.append(
                f"Se ignora {p.relative_to(root).as_posix()}: no es un archivo de WoW conocido."
            )
    sv = folder / "SavedVariables"
    if sv.is_dir():
        layer.saved_variables = sorted(
            p for p in sv.iterdir() if p.is_file() and p.suffix == ".lua"
        )
    return layer


def load(root: Path | None = None) -> Template:
    root = root or storage.template_dir()
    if not root.is_dir():
        raise WowcfgError("La plantilla no está descargada. Ejecuta `wowcfg fetch`.")

    warnings: list[str] = []

    global_config = root / "outer" / "Config.wtf"
    account = _read_layer(root, root, warnings)

    chars_dir = root / "Characters"
    common = _read_layer(chars_dir / COMMON, root, warnings)
    classes: dict[Class_, Layer] = {}
    if chars_dir.is_dir():
        valid = {c.value for c in Class_}
        for d in sorted(chars_dir.iterdir()):
            if not d.is_dir() or d.name == COMMON or d.name.startswith("."):
                continue
            if d.name not in valid:
                warnings.append(
                    f"Characters/{d.name} no es una clase conocida y se ignora "
                    f"(válidas: {', '.join(sorted(valid))})."
                )
                continue
            classes[Class_(d.name)] = _read_layer(d, root, warnings)

    return Template(
        root=root,
        global_config=global_config if global_config.is_file() else None,
        account=account,
        common=common,
        classes=classes,
        warnings=warnings,
    )


# --- descarga -----------------------------------------------------------------


def _git(*args: str, cwd: Path | None = None) -> str:
    if shutil.which("git") is None:
        raise WowcfgError("No se encontró `git`. Instálalo y vuelve a intentarlo.")
    res = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
    )
    if res.returncode != 0:
        raise WowcfgError(f"`git {' '.join(args)}` falló:\n{res.stderr.strip()}")
    return res.stdout.strip()


def _force_remove(func, path, _exc) -> None:
    # git deja sus objetos en solo lectura; en Windows rmtree no puede borrarlos
    os.chmod(path, stat.S_IWRITE)
    func(path)


def remove_tree(path: Path) -> None:
    if not path.exists():
        return
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_force_remove)
    else:
        shutil.rmtree(path, onerror=_force_remove)


def fetch(repo: str, ref: str | None) -> str:
    """Clona o actualiza la plantilla. Devuelve el commit descargado."""
    dst = storage.template_dir()
    same_repo = False
    if (dst / ".git").is_dir():
        try:
            same_repo = _git("remote", "get-url", "origin", cwd=dst) == repo
        except WowcfgError:
            same_repo = False

    if same_repo:
        _git("fetch", "--depth", "1", "origin", ref or "HEAD", cwd=dst)
        _git("reset", "--hard", "FETCH_HEAD", cwd=dst)
        _git("clean", "-fdx", cwd=dst)
    else:
        remove_tree(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        args = ["clone", "--depth", "1"]
        if ref:
            args += ["--branch", ref]
        _git(*args, repo, str(dst))

    return _git("log", "-1", "--format=%h %s", cwd=dst)
