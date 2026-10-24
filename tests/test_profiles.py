from conftest import ACCOUNT_SV

from wowcfg.profiles import assign_profile_keys


def test_fills_empty_table_with_crlf_and_indent():
    out = assign_profile_keys(
        ACCOUNT_SV, ["Lockito - Icecrown", "Healz - Icecrown"], "main"
    )
    assert (
        '\t["profileKeys"] = {\r\n'
        '\t\t["Lockito - Icecrown"] = "main",\r\n'
        '\t\t["Healz - Icecrown"] = "main",\r\n'
        "\t},"
    ) in out
    assert "\n" not in out.replace("\r\n", "")  # no mezcla LF suelto


def test_replaces_existing_keys():
    text = '\t["profileKeys"] = {\n\t\t["Old - Realm"] = "Default",\n\t},\n'
    out = assign_profile_keys(text, ["New - Realm"], "main")
    assert "Old" not in out
    assert '\t\t["New - Realm"] = "main",\n\t},' in out


def test_rewrites_every_table_and_ignores_files_without_it():
    text = (
        '["profileKeys"] = {}\n["namespaces"] = { ["x"] = { ["profileKeys"] = {} } }\n'
    )
    out = assign_profile_keys(text, ["A - R"], "main")
    assert out.count('["A - R"] = "main"') == 2
    assert (
        assign_profile_keys("WeakAurasSaved = {}\n", ["A - R"], "main")
        == "WeakAurasSaved = {}\n"
    )


def test_no_characters_leaves_table_empty():
    assert (
        assign_profile_keys('["profileKeys"] = {\n["x"] = "y",\n}', [], "main")
        == '["profileKeys"] = {}'
    )
