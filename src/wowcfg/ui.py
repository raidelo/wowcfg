"""Salida por consola.

Los mensajes se escapan siempre: pueden contener rutas o nombres con
corchetes que rich interpretaría como marcado.
"""

from rich.console import Console
from rich.markup import escape

console = Console(highlight=False)
err_console = Console(stderr=True, highlight=False)


def info(msg: str) -> None:
    console.print(escape(msg))


def success(msg: str) -> None:
    console.print(f"[green]{escape(msg)}[/green]")


def warn(msg: str) -> None:
    err_console.print(f"[bold yellow]aviso:[/bold yellow] {escape(msg)}")


def error(msg: str) -> None:
    err_console.print(f"[bold red]error:[/bold red] {escape(msg)}")
