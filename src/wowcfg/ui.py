import sys
from typing import NoReturn


def die(msg: str) -> NoReturn:
    """Exits the app with the given error message."""
    print(f"ERROR: {msg}")
    sys.exit(1)
