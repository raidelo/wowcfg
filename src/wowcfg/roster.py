"""Clase de cada personaje (`characters.json`).

La clase no se puede deducir de `WTF/`, así que la registra el usuario.
Las búsquedas no distinguen mayúsculas porque WoW guarda las cuentas en
mayúsculas y es fácil escribirlas distinto.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from wowcfg import WowcfgError, storage


class Class_(StrEnum):
    DK = "dk"
    DRUID = "druid"
    HUNTER = "hunter"
    MAGE = "mage"
    PALADIN = "paladin"
    PRIEST = "priest"
    ROGUE = "rogue"
    SHAMAN = "shaman"
    WARLOCK = "warlock"
    WARRIOR = "warrior"


class Entry(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    account: str
    realm: str
    name: str
    class_: Class_ = Field(alias="class")

    def matches(self, account: str, realm: str, name: str) -> bool:
        return (
            self.account.casefold() == account.casefold()
            and self.realm.casefold() == realm.casefold()
            and self.name.casefold() == name.casefold()
        )


class Roster(BaseModel):
    characters: list[Entry] = Field(default_factory=list)

    def find(self, account: str, realm: str, name: str) -> Entry | None:
        return next(
            (e for e in self.characters if e.matches(account, realm, name)), None
        )

    def class_of(self, account: str, realm: str, name: str) -> Class_ | None:
        entry = self.find(account, realm, name)
        return entry.class_ if entry else None

    def set(self, account: str, realm: str, name: str, class_: Class_) -> None:
        entry = self.find(account, realm, name)
        if entry is None:
            self.characters.append(
                Entry(account=account, realm=realm, name=name, class_=class_)
            )
        else:
            entry.class_ = class_
        self.characters.sort(
            key=lambda e: (e.account.lower(), e.realm.lower(), e.name.lower())
        )

    def unset(self, account: str, realm: str, name: str) -> bool:
        entry = self.find(account, realm, name)
        if entry is None:
            return False
        self.characters.remove(entry)
        return True


def load() -> Roster:
    path = storage.roster_file()
    if not path.is_file():
        return Roster()
    try:
        return Roster.model_validate(storage.read_json(path))
    except (ValidationError, ValueError) as e:
        raise WowcfgError(f"{path} no es válido:\n{e}") from e


def save(roster: Roster) -> None:
    storage.write_json(
        storage.roster_file(), roster.model_dump(mode="json", by_alias=True)
    )
