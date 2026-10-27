import json
from pathlib import Path

from conftest import make_install, write

from wowcfg import config, roster
from wowcfg.config import Config


def acc(install: Path, account: str) -> Path:
    return install / "WTF" / "Account" / account


# --- apply --------------------------------------------------------------------


def test_apply_writes_everything_where_it_belongs(configured, cli):
    assert cli("char", "set", "lockito", "warlock").exit_code == 0

    r = cli("apply")
    assert r.exit_code == 0, r.output

    one = acc(configured, "ACCOUNTONE")
    assert (configured / "WTF" / "Config.wtf").read_text() == 'SET gxWindow "1"\n'
    assert (one / "bindings-cache.wtf").read_text() == "BINDINGS account\n"
    assert not (one / "README.md").exists()

    bt = (one / "SavedVariables" / "Bartender4.lua").read_text(encoding="utf-8")
    assert '["Lockito - Icecrown"] = "main"' in bt
    assert '["Healz - Icecrown"] = "main"' in bt
    assert "Lordaeron" not in bt  # solo personajes de esa cuenta

    lock = one / "Icecrown" / "Lockito"
    assert (lock / "macros-cache.txt").read_text() == "MACROS warlock\n"
    assert (lock / "SavedVariables" / "MSBT.lua").read_text() == "common\n"
    # la clase gana a common aunque ambas tengan el mismo archivo
    assert (lock / "SavedVariables" / "Shared.lua").read_text() == "from warlock\n"

    healz = one / "Icecrown" / "Healz"
    assert (healz / "SavedVariables" / "Shared.lua").read_text() == "from common\n"
    assert not (healz / "macros-cache.txt").exists()
    assert "sin clase registrada" in r.output


def test_apply_is_idempotent(configured, cli):
    assert cli("apply").exit_code == 0
    r = cli("apply")
    assert r.exit_code == 0
    assert "ya al día" in r.output
    assert len(list((configured.parent / "home" / "backups").iterdir())) == 1


def test_dry_run_writes_nothing(configured, cli):
    r = cli("apply", "--dry-run")
    assert r.exit_code == 0, r.output
    assert "nuevo" in r.output
    assert not (configured / "WTF" / "Config.wtf").exists()


def test_apply_single_account(configured, cli):
    assert cli("apply", "--account", "accounttwo").exit_code == 0
    assert (acc(configured, "ACCOUNTTWO") / "bindings-cache.wtf").exists()
    assert not (acc(configured, "ACCOUNTONE") / "bindings-cache.wtf").exists()
    assert cli("apply", "--account", "nope").exit_code == 1


def test_apply_refuses_while_wow_is_running(configured, cli, monkeypatch):
    from wowcfg import wow

    monkeypatch.setattr(wow, "is_wow_running", lambda: True)
    r = cli("apply")
    assert r.exit_code == 1
    assert "Cierra WoW" in r.output


def test_apply_skips_missing_install(configured, cli, tmp_path):
    cfg = config.load()
    cfg.paths.append(tmp_path / "gone")
    config.save(cfg)
    r = cli("apply")
    assert r.exit_code == 0
    assert "Se omite" in r.output


def test_unknown_class_folder_and_stray_files_are_reported(configured, tmpl, cli):
    write(tmpl / "character" / "warlok" / "x.lua", "")
    write(tmpl / "account" / "notes.txt", "")
    r = cli("apply", "--dry-run")
    assert "warlok" in r.output
    assert "notes.txt" in r.output


# --- backups ------------------------------------------------------------------


def test_restore_puts_back_originals_and_deletes_created(configured, cli):
    original = write(acc(configured, "ACCOUNTONE") / "bindings-cache.wtf", "MINE\n")
    cli("apply")
    assert original.read_text() == "BINDINGS account\n"

    r = cli("backup", "restore", "--yes")
    assert r.exit_code == 0, r.output
    assert original.read_text() == "MINE\n"
    assert not (configured / "WTF" / "Config.wtf").exists()


def test_two_installs_do_not_overwrite_each_others_backups(home, tmpl, tmp_path, cli):
    a = make_install(tmp_path / "a", {"ACC": {"R": ["X"]}})
    b = make_install(tmp_path / "b", {"ACC": {"R": ["X"]}})
    write(a / "WTF" / "Config.wtf", "A\n")
    write(b / "WTF" / "Config.wtf", "B\n")
    config.save(Config(paths=[a, b]))

    assert cli("apply").exit_code == 0
    assert cli("backup", "restore", "-y").exit_code == 0
    assert (a / "WTF" / "Config.wtf").read_text() == "A\n"
    assert (b / "WTF" / "Config.wtf").read_text() == "B\n"


def test_backup_list(configured, cli):
    assert "No hay" in cli("backup", "list").output
    cli("apply")
    assert cli("backup", "list").exit_code == 0
    assert cli("backup", "restore", "nope", "-y").exit_code == 1


# --- char ---------------------------------------------------------------------


def test_char_set_is_case_insensitive_and_stores_real_names(configured, cli):
    r = cli("char", "set", "LOCKITO", "Warlock")
    assert r.exit_code == 0, r.output
    data = json.loads((configured.parent / "home" / "characters.json").read_text())
    assert data["characters"] == [
        {
            "account": "ACCOUNTONE",
            "realm": "Icecrown",
            "name": "Lockito",
            "class": "warlock",
        }
    ]


def test_char_set_ambiguous_name(configured, cli):
    r = cli("char", "set", "healz", "priest")
    assert r.exit_code == 1
    assert "varios personajes" in r.output
    assert cli("char", "set", "healz", "priest", "--realm", "lordaeron").exit_code == 0
    assert roster.load().class_of("ACCOUNTTWO", "Lordaeron", "Healz") == "priest"


def test_char_set_unknown(configured, cli):
    assert cli("char", "set", "ghost", "mage").exit_code == 1
    assert (
        cli(
            "char", "set", "ghost", "mage", "-r", "Icecrown", "-a", "ACCOUNTONE"
        ).exit_code
        == 0
    )
    assert cli("char", "set", "lockito", "wizard").exit_code == 2  # clase inválida


def test_char_list_and_unset(configured, cli):
    cli("char", "set", "lockito", "warlock")
    out = cli("char", "list", "--missing").output
    assert "Healz" in out and "Lockito" not in out

    assert cli("char", "unset", "lockito").exit_code == 0
    assert cli("char", "unset", "lockito").exit_code == 1
    assert "Lockito" in cli("char", "list", "--missing").output


# --- path / init --------------------------------------------------------------


def test_path_add_list_remove(home, tmp_path, cli):
    config.save(Config())
    wow_dir = make_install(tmp_path / "wow", {"A": {"R": ["X"]}})

    assert cli("path", "add", str(wow_dir)).exit_code == 0
    assert "ya estaba" in cli("path", "add", str(wow_dir)).output
    assert len(config.load().paths) == 1
    assert "ok" in cli("path", "list").output

    assert cli("path", "remove", "1").exit_code == 0
    assert config.load().paths == []
    assert cli("path", "remove", str(wow_dir)).exit_code == 1


def test_init_non_interactive(home, tmp_path, cli):
    wow_dir = make_install(tmp_path / "wow", {"A": {"R": ["X"]}})
    r = cli(
        "init",
        "--repo",
        "https://x/y",
        "--path",
        str(wow_dir),
        "--path",
        str(wow_dir),
        input="n\n",
    )
    assert r.exit_code == 0, r.output
    cfg = config.load()
    assert cfg.repo == "https://x/y" and cfg.paths == [wow_dir]

    # no sobrescribe sin confirmar
    r = cli("init", "--repo", "https://other", "--path", str(wow_dir), input="n\n")
    assert r.exit_code == 1
    assert config.load().repo == "https://x/y"


def test_commands_need_init(home, cli):
    r = cli("apply")
    assert r.exit_code == 1
    assert "wowcfg init" in r.output
