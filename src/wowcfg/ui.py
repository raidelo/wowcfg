import sys
from os import isatty
from typing import NoReturn


def die(msg: str) -> NoReturn:
    """Exits the app with the given error message."""
    e = "error:"
    if isatty(sys.stdout.fileno()):
        e = f"\x1b[1;31m{e}\x1b[0m"
    print(f"{e} {msg}")
    sys.exit(1)
