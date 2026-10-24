"""Cálculo de qué archivos se escriben y dónde.

`build` no toca el disco de WoW: devuelve un `Plan` que se puede mostrar
(`--dry-run`) o ejecutar con `backup.execute`.
"""

from dataclasses import dataclass, field
from pathlib import Path

from wowcfg.profiles import assign_profile_keys
from wowcfg.roster import Class_, Roster
from wowcfg.template import Layer, Template
from wowcfg.wow import CharacterDir, list_accounts, list_characters, wtf_dir


@dataclass
class Operation:
    install: Path
    src: Path
    dst: Path
    profile_keys: list[str] | None = None
    """Si no es `None`, se reescribe `profileKeys` con estas claves."""

    def render(self, profile: str) -> bytes:
        if self.profile_keys is None:
            return self.src.read_bytes()
        with open(self.src, encoding="utf-8", newline="") as f:
            text = f.read()
        return assign_profile_keys(text, self.profile_keys, profile).encode("utf-8")

    def changes(self, profile: str) -> bool:
        if not self.dst.is_file():
            return True
        return self.dst.read_bytes() != self.render(profile)


@dataclass
class AccountPlan:
    install: Path
    account: Path
    characters: list[tuple[CharacterDir, Class_ | None]]


@dataclass
class Plan:
    operations: list[Operation] = field(default_factory=list)
    accounts: list[AccountPlan] = field(default_factory=list)

    @property
    def unclassed(self) -> list[CharacterDir]:
        return [c for a in self.accounts for c, cls in a.characters if cls is None]


class _Ops:
    """Operaciones indexadas por destino: si dos capas escriben el mismo
    archivo gana la última (p. ej. la clase sobre `common`)."""

    def __init__(self) -> None:
        self._ops: dict[str, Operation] = {}

    def add(self, op: Operation) -> None:
        key = str(op.dst).casefold()
        self._ops.pop(key, None)
        self._ops[key] = op

    def add_layer(
        self, install: Path, layer: Layer, folder: Path, keys: list[str] | None
    ) -> None:
        for src in layer.files:
            self.add(Operation(install, src, folder / src.name))
        for src in layer.saved_variables:
            self.add(
                Operation(install, src, folder / "SavedVariables" / src.name, keys)
            )

    def list(self) -> list[Operation]:
        return list(self._ops.values())


def build(
    template: Template,
    roster: Roster,
    installs: list[Path],
    account_filter: str | None = None,
) -> Plan:
    plan = Plan()
    ops = _Ops()

    for install in installs:
        if template.global_config is not None:
            ops.add(
                Operation(
                    install, template.global_config, wtf_dir(install) / "Config.wtf"
                )
            )

        for account in list_accounts(install):
            if account_filter and account.name.casefold() != account_filter.casefold():
                continue

            chars = list_characters(install, account)
            classed = [(c, roster.class_of(c.account, c.realm, c.name)) for c in chars]
            plan.accounts.append(AccountPlan(install, account, classed))

            keys = [c.profile_key for c in chars]
            ops.add_layer(install, template.account, account, keys)

            for char, class_ in classed:
                ops.add_layer(install, template.common, char.path, None)
                if class_ is not None and class_ in template.classes:
                    ops.add_layer(install, template.classes[class_], char.path, None)

    plan.operations = ops.list()
    return plan
