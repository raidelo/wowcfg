"""wowcfg: aplica una plantilla de configuración de WoW WotLK."""

__version__ = "1.0.0"


class WowcfgError(Exception):
    """Error esperado: se muestra al usuario sin traceback y sale con código 1."""
