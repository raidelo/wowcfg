"""Reescritura de `profileKeys` en SavedVariables de addons con AceDB."""

import re

PROFILE_KEYS_RE = re.compile(r'(\["profileKeys"\]\s*=\s*\{)([^{}]*)(\})')


def _lua_string(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def assign_profile_keys(text: str, keys: list[str], profile: str) -> str:
    """Sustituye el contenido de cada tabla `profileKeys` para que contenga
    exactamente `keys`, todas apuntando a `profile`.

    Se respetan el salto de línea (CRLF/LF) y la sangría del archivo.
    Los archivos sin `profileKeys` se devuelven sin cambios.
    """
    nl = "\r\n" if "\r\n" in text else "\n"

    def repl(m: re.Match[str]) -> str:
        head, _body, close = m.groups()
        line_start = text.rfind("\n", 0, m.start()) + 1
        indent = re.match(r"[ \t]*", text[line_start : m.start()]).group(0)
        if not keys:
            return head + close
        entries = "".join(
            f"{nl}{indent}\t[{_lua_string(k)}] = {_lua_string(profile)}," for k in keys
        )
        return head + entries + nl + indent + close

    return PROFILE_KEYS_RE.sub(repl, text)
