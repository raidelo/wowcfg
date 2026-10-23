from enum import Enum

from pydantic import BaseModel, TypeAdapter, ValidationError

from wowcfg.constants import ROSTER_FILE
from wowcfg.ui import die


class Account(BaseModel):
    name: str
    realms: list[Realm]


class Realm(BaseModel):
    name: str
    characters: list[Character]


class Character(BaseModel):
    name: str
    class_: Class_


class Class_(Enum):
    DK = "dk"
    PALADIN = "paladin"
    WARRIOR = "warrior"
    SHAMAN = "shaman"
    HUNTER = "hunter"
    ROGUE = "rogue"
    DRUID = "druid"
    PRIEST = "priest"
    WARLOCK = "warlock"
    MAGE = "mage"


RosterAdapter = TypeAdapter(list[Account])


def load_roster() -> list[Account]:
    with ROSTER_FILE.open("r") as f:
        return RosterAdapter.validate_json(f.read())


def save_roster(mappings: list[Account]) -> None:
    with ROSTER_FILE.open("wb") as f:
        f.write(RosterAdapter.dump_json(mappings, indent=2))


_roster: list[Account] | None = None


def get_roster() -> list[Account]:
    global _roster
    if _roster is None:
        try:
            roster = load_roster()
        except FileNotFoundError:
            roster = []
        except ValidationError as e:
            die(str(e))

        _roster = roster
    return _roster


def set_character_class(
    class_mappings: list[Account],
    account: str,
    realm: str,
    character: str,
    class_: Class_,
) -> None:
    acc = next((a for a in class_mappings if a.name == account), None)
    if acc is None:
        acc = Account(name=account, realms=[])
        class_mappings.append(acc)

    rlm = next((r for r in acc.realms if r.name == realm), None)
    if rlm is None:
        rlm = Realm(name=realm, characters=[])
        acc.realms.append(rlm)

    char = next((c for c in rlm.characters if c.name == character), None)
    if char is None:
        rlm.characters.append(Character(name=character, class_=class_))
    else:
        char.class_ = class_


def get_character_class(
    roster: list[Account], account: str, realm: str, name: str
) -> Class_ | None:
    return next(
        (
            c.class_
            for acc in roster
            if acc.name == account
            for r in acc.realms
            if r.name == realm
            for c in r.characters
            if c.name == name
        ),
        None,
    )
