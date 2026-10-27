from pathlib import Path

import pytest
from typer.testing import CliRunner

from wowcfg import config, wow
from wowcfg.cli import app
from wowcfg.config import Config

CRLF = "\r\n"

ACCOUNT_SV = CRLF.join(
    [
        "",
        "Bartender4DB = {",
        '\t["profileKeys"] = {},',
        '\t["profiles"] = {',
        '\t\t["main"] = {',
        '\t\t\t["buttonlock"] = true,',
        "\t\t},",
        "\t},",
        "}",
        "",
    ]
)


def write(p: Path, text: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(text.encode("utf-8"))
    return p


@pytest.fixture
def home(tmp_path, monkeypatch) -> Path:
    h = tmp_path / "home"
    monkeypatch.setenv("WOWCFG_HOME", str(h))
    monkeypatch.setattr(wow, "is_wow_running", lambda: False)
    return h


@pytest.fixture
def tmpl(home) -> Path:
    """Plantilla ya "descargada", con la misma forma que wow-config."""
    t = home / "template"
    write(t / "outer" / "Config.wtf", 'SET gxWindow "1"\n')
    write(t / "bindings-cache.wtf", "BINDINGS account\n")
    write(t / "macros-cache.txt", "MACROS account\n")
    write(t / "README.md", "# no copiar\n")
    write(t / "SavedVariables" / "Bartender4.lua", ACCOUNT_SV)
    write(t / "character" / "common" / "SavedVariables" / "MSBT.lua", "common\n")
    write(t / "character" / "common" / "SavedVariables" / "Shared.lua", "from common\n")
    write(t / "character" / "warlock" / "macros-cache.txt", "MACROS warlock\n")
    write(
        t / "character" / "warlock" / "SavedVariables" / "Shared.lua", "from warlock\n"
    )
    (t / ".git").mkdir()
    return t


def make_install(root: Path, chars: dict[str, dict[str, list[str]]]) -> Path:
    for account, realms in chars.items():
        (root / "WTF" / "Account" / account / "SavedVariables").mkdir(
            parents=True, exist_ok=True
        )
        for realm, names in realms.items():
            for n in names:
                (root / "WTF" / "Account" / account / realm / n).mkdir(
                    parents=True, exist_ok=True
                )
    return root


@pytest.fixture
def install(tmp_path) -> Path:
    return make_install(
        tmp_path / "wow",
        {
            "ACCOUNTONE": {"Icecrown": ["Lockito", "Healz"]},
            "ACCOUNTTWO": {"Lordaeron": ["Healz"]},
        },
    )


@pytest.fixture
def configured(home, tmpl, install) -> Path:
    config.save(Config(repo="https://example.invalid/repo", paths=[install]))
    return install


@pytest.fixture
def cli():
    runner = CliRunner()

    def run(*args: str, input: str | None = None):
        result = runner.invoke(app, list(args), input=input, catch_exceptions=True)
        return result

    return run
