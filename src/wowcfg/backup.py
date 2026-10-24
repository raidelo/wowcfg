"""Copias de seguridad: ejecución de un plan y restauración.

Cada ejecución de `apply` crea `backups/<id>/` con:

- `manifest.json`: cada archivo tocado, con su copia (o `null` si el
  archivo no existía y fue creado por wowcfg).
- `<n>/...`: las copias, separadas por instalación para que dos
  instalaciones no se pisen entre sí.

Restaurar devuelve cada archivo a su estado anterior y borra los que
wowcfg creó.
"""

import datetime as dt
import shutil
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ValidationError

from wowcfg import WowcfgError, storage
from wowcfg.plan import Plan

MANIFEST = "manifest.json"


class ManifestEntry(BaseModel):
    target: Path
    backup: str | None
    """Ruta relativa a la carpeta del backup, o `None` si no había original."""


class Manifest(BaseModel):
    id: str
    created: dt.datetime
    installs: list[Path]
    entries: list[ManifestEntry]


@dataclass
class Result:
    backup_id: str | None
    written: int
    unchanged: int


def _new_id() -> str:
    base = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    root = storage.backups_dir()
    candidate, n = base, 1
    while (root / candidate).exists():
        n += 1
        candidate = f"{base}-{n}"
    return candidate


def _save_manifest(folder: Path, manifest: Manifest) -> None:
    storage.write_json(folder / MANIFEST, manifest.model_dump(mode="json"))


def execute(plan: Plan, profile: str) -> Result:
    """Escribe el plan haciendo copia de cada archivo antes de tocarlo.

    Los archivos que ya tienen el contenido correcto no se tocan ni se copian.
    El manifiesto se guarda aunque falle a mitad, para poder restaurar.
    """
    pending = [(op, op.render(profile)) for op in plan.operations]
    pending = [
        (op, data)
        for op, data in pending
        if not op.dst.is_file() or op.dst.read_bytes() != data
    ]
    unchanged = len(plan.operations) - len(pending)
    if not pending:
        return Result(None, 0, unchanged)

    backup_id = _new_id()
    folder = storage.backups_dir() / backup_id
    folder.mkdir(parents=True)

    installs: list[Path] = []
    for op, _ in pending:
        if op.install not in installs:
            installs.append(op.install)

    manifest = Manifest(
        id=backup_id, created=dt.datetime.now(), installs=installs, entries=[]
    )
    try:
        for op, data in pending:
            backup_rel = None
            if op.dst.is_file():
                n = installs.index(op.install)
                rel = Path(str(n)) / op.dst.relative_to(op.install)
                (folder / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(op.dst, folder / rel)
                backup_rel = rel.as_posix()
            # se registra antes de escribir: si la escritura falla, restaurar
            # sigue sabiendo qué había
            manifest.entries.append(ManifestEntry(target=op.dst, backup=backup_rel))
            op.dst.parent.mkdir(parents=True, exist_ok=True)
            op.dst.write_bytes(data)
    finally:
        _save_manifest(folder, manifest)

    return Result(backup_id, len(pending), unchanged)


def list_backups() -> list[Manifest]:
    root = storage.backups_dir()
    if not root.is_dir():
        return []
    out = []
    for d in root.iterdir():
        m = d / MANIFEST
        if m.is_file():
            try:
                out.append(Manifest.model_validate(storage.read_json(m)))
            except (ValidationError, ValueError):
                continue
    return sorted(out, key=lambda m: m.created, reverse=True)


def get(backup_id: str | None) -> Manifest:
    backups = list_backups()
    if not backups:
        raise WowcfgError("No hay copias de seguridad.")
    if backup_id is None:
        return backups[0]
    for m in backups:
        if m.id == backup_id:
            return m
    raise WowcfgError(
        f"No existe la copia `{backup_id}`. Mira las disponibles con `wowcfg backup list`."
    )


def restore(manifest: Manifest) -> tuple[int, int]:
    """Devuelve (restaurados, borrados)."""
    folder = storage.backups_dir() / manifest.id
    restored = deleted = 0
    for e in manifest.entries:
        if e.backup is None:
            if e.target.is_file():
                e.target.unlink()
                deleted += 1
        else:
            e.target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(folder / e.backup, e.target)
            restored += 1
    return restored, deleted
