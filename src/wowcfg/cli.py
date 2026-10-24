"""Interfaz de línea de comandos."""

import functools
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.table import Table

from wowcfg import WowcfgError, __version__, backup, config, roster, template, wow
from wowcfg.config import DEFAULT_REPO, Config, same_path
from wowcfg.plan import Plan
from wowcfg.plan import build as build_plan
from wowcfg.roster import Class_
from wowcfg.storage import template_dir
from wowcfg.ui import console, error, info, success, warn


class _App(typer.Typer):
    """Typer que convierte `WowcfgError` en un mensaje limpio y salida 1."""

    def command(self, *args: Any, **kwargs: Any) -> Callable:
        register = super().command(*args, **kwargs)

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*a: Any, **kw: Any) -> Any:
                try:
                    return func(*a, **kw)
                except WowcfgError as e:
                    error(str(e))
                    raise typer.Exit(1) from None

            register(wrapper)
            return func

        return decorator


app = _App(
    no_args_is_help=True,
    add_completion=False,
    help="Aplica una plantilla de configuración de WoW WotLK a todas tus cuentas y personajes.",
)
path_app = _App(no_args_is_help=True, help="Instalaciones de WoW registradas.")
char_app = _App(no_args_is_help=True, help="Clase de cada personaje.")
backup_app = _App(no_args_is_help=True, help="Copias de seguridad.")
app.add_typer(path_app, name="path")
app.add_typer(char_app, name="char")
app.add_typer(backup_app, name="backup")


# --- tipos reutilizables -----------------------------------------------------

RealmOpt = Annotated[
    str | None, typer.Option("--realm", "-r", help="Reino, si el nombre está repetido.")
]
AccountOpt = Annotated[
    str | None,
    typer.Option("--account", "-a", help="Cuenta, si el nombre está repetido."),
]
YesOpt = Annotated[bool, typer.Option("--yes", "-y", help="No pedir confirmación.")]


def _version(value: bool) -> None:
    if value:
        info(f"wowcfg {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            callback=_version,
            is_eager=True,
            help="Muestra la versión.",
        ),
    ] = False,
) -> None:
    pass


# --- utilidades ---------------------------------------------------------------


def _check_install(path: Path) -> str | None:
    """Devuelve un aviso si la ruta no parece una instalación usable."""
    if not path.is_dir():
        return "no existe"
    if not wow.wtf_dir(path).is_dir():
        return "no tiene carpeta WTF (¿has entrado al juego alguna vez?)"
    if not wow.accounts_dir(path).is_dir():
        return "no tiene WTF/Account (entra al juego una vez con cada cuenta)"
    return None


def _ensure_wow_closed() -> None:
    if wow.is_wow_running():
        raise WowcfgError("Cierra WoW primero: al salir sobrescribiría los cambios.")


def _ensure_template(cfg: Config, yes: bool) -> template.Template:
    if not template_dir().is_dir():
        if not yes and not typer.confirm(
            "La plantilla no está descargada. ¿Descargarla ahora?", default=True
        ):
            raise typer.Exit(1)
        _do_fetch(cfg)
    tmpl = template.load()
    for w in tmpl.warnings:
        warn(w)
    return tmpl


def _do_fetch(cfg: Config) -> None:
    with console.status(f"Descargando {cfg.repo}..."):
        commit = template.fetch(cfg.repo, cfg.ref)
    success(f"Plantilla actualizada: {commit}")


# --- comandos principales -----------------------------------------------------


@app.command()
def init(
    repo: Annotated[
        str | None, typer.Option(help="URL del repositorio con la plantilla.")
    ] = None,
    path: Annotated[
        list[Path] | None,
        typer.Option(
            file_okay=False,
            resolve_path=True,
            help="Carpeta del WoW. Se puede repetir.",
        ),
    ] = None,
    ref: Annotated[str | None, typer.Option(help="Rama o tag de la plantilla.")] = None,
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Sobrescribir sin preguntar.")
    ] = False,
) -> None:
    """Crea la configuración inicial."""
    if config.exists() and not force:
        typer.confirm("Ya existe una configuración. ¿Sobrescribirla?", abort=True)

    repo = repo or typer.prompt("Repositorio de la plantilla", default=DEFAULT_REPO)
    paths = path or [
        Path(typer.prompt("Carpeta del WoW (la que contiene Wow.exe)")).resolve()
    ]

    unique: list[Path] = []
    for p in paths:
        if not p.is_dir():
            raise WowcfgError(f"{p} no existe o no es una carpeta.")
        if problem := _check_install(p):
            warn(f"{p} {problem}.")
        if not any(same_path(p, u) for u in unique):
            unique.append(p)

    cfg = Config(repo=repo, ref=ref, paths=unique)
    config.save(cfg)
    success("Configuración guardada.")

    if typer.confirm("¿Descargar la plantilla ahora?", default=True):
        _do_fetch(cfg)


@app.command()
def fetch() -> None:
    """Descarga o actualiza la plantilla."""
    _do_fetch(config.load())


@app.command()
def apply(
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", "-n", help="Muestra qué cambiaría sin escribir nada."
        ),
    ] = False,
    path: Annotated[
        Path | None,
        typer.Option("--path", "-p", resolve_path=True, help="Solo esta instalación."),
    ] = None,
    account: Annotated[
        str | None, typer.Option("--account", "-a", help="Solo esta cuenta.")
    ] = None,
    yes: YesOpt = False,
) -> None:
    """Aplica la plantilla a todas las cuentas y personajes."""
    cfg = config.load()

    if path is not None:
        if not cfg.has_path(path):
            raise WowcfgError(
                f"{path} no está registrada. Añádela con `wowcfg path add`."
            )
        candidates = [p for p in cfg.paths if same_path(p, path)]
    else:
        candidates = cfg.paths
    if not candidates:
        raise WowcfgError(
            "No hay instalaciones registradas. Añade una con `wowcfg path add`."
        )

    installs = []
    for p in candidates:
        if not p.is_dir():
            warn(f"Se omite {p}: no existe.")
        elif not wow.wtf_dir(p).is_dir():
            warn(f"Se omite {p}: no tiene carpeta WTF.")
        else:
            installs.append(p)
    if not installs:
        raise WowcfgError("Ninguna instalación es válida.")

    if not dry_run:
        _ensure_wow_closed()

    tmpl = _ensure_template(cfg, yes)
    plan = build_plan(tmpl, roster.load(), installs, account)

    if account and not plan.accounts:
        raise WowcfgError(f"No se encontró la cuenta `{account}`.")

    _print_summary(plan)

    if dry_run:
        _print_dry_run(plan, cfg.profile)
        return

    result = backup.execute(plan, cfg.profile)
    if result.backup_id is None:
        success("Todo estaba ya al día. No se ha modificado nada.")
        return
    success(
        f"Listo: {result.written} archivo(s) escritos, {result.unchanged} ya estaban al día."
    )
    info(
        f"Copia de seguridad: {result.backup_id} (deshacer con `wowcfg backup restore`)"
    )


def _print_summary(plan: Plan) -> None:
    for acc in plan.accounts:
        info(f"{acc.account.name} ({acc.install}): {len(acc.characters)} personaje(s)")
    if not plan.accounts:
        warn(
            "No se encontró ninguna cuenta en WTF/Account; solo se aplicará Config.wtf."
        )
    unclassed = plan.unclassed
    if unclassed:
        warn(
            f"{len(unclassed)} personaje(s) sin clase registrada, solo reciben `common`: "
            + ", ".join(c.label for c in unclassed)
        )
        info(
            "  Regístralos con `wowcfg char set NOMBRE CLASE` (ver `wowcfg char list --missing`)."
        )


def _print_dry_run(plan: Plan, profile: str) -> None:
    table = Table(title="Simulación (no se ha escrito nada)", show_lines=False)
    table.add_column("Estado")
    table.add_column("Archivo", overflow="fold")
    table.add_column("Origen en la plantilla", style="dim", overflow="fold")
    root = template_dir()
    counts = {"nuevo": 0, "cambia": 0, "igual": 0}
    for op in plan.operations:
        if not op.dst.is_file():
            state, style = "nuevo", "green"
        elif op.changes(profile):
            state, style = "cambia", "yellow"
        else:
            state, style = "igual", "dim"
        counts[state] += 1
        if state == "igual":
            continue
        table.add_row(
            f"[{style}]{state}[/{style}]",
            op.dst.relative_to(op.install).as_posix(),
            op.src.relative_to(root).as_posix(),
        )
    if table.row_count:
        console.print(table)
    info(
        f"{counts['nuevo']} nuevo(s), {counts['cambia']} con cambios, {counts['igual']} sin cambios."
    )


# --- path ---------------------------------------------------------------------


@path_app.command("list")
def path_list() -> None:
    """Muestra las instalaciones registradas."""
    cfg = config.load()
    if not cfg.paths:
        info("No hay instalaciones registradas.")
        return
    table = Table()
    table.add_column("#", justify="right")
    table.add_column("Ruta")
    table.add_column("Cuentas", justify="right")
    table.add_column("Estado")
    for i, p in enumerate(cfg.paths, 1):
        problem = _check_install(p)
        table.add_row(
            str(i),
            str(p),
            str(len(wow.list_accounts(p))),
            f"[yellow]{problem}[/yellow]" if problem else "[green]ok[/green]",
        )
    console.print(table)


@path_app.command("add")
def path_add(
    path: Annotated[
        Path,
        typer.Argument(
            exists=True, file_okay=False, resolve_path=True, help="Carpeta del WoW."
        ),
    ],
) -> None:
    """Registra una instalación de WoW."""
    cfg = config.load()
    if cfg.has_path(path):
        info(f"{path} ya estaba registrada.")
        return
    if problem := _check_install(path):
        warn(f"{path} {problem}.")
    cfg.paths.append(path)
    config.save(cfg)
    success(f"Añadida {path}")


@path_app.command("remove")
def path_remove(
    target: Annotated[
        str, typer.Argument(metavar="PATH", help="Ruta, o su número en `path list`.")
    ],
) -> None:
    """Deja de usar una instalación (no borra nada del disco)."""
    cfg = config.load()
    if target.isdigit() and 1 <= int(target) <= len(cfg.paths):
        removed = cfg.paths.pop(int(target) - 1)
    else:
        match = next((p for p in cfg.paths if same_path(p, Path(target))), None)
        if match is None:
            raise WowcfgError(f"{target} no está registrada.")
        cfg.paths.remove(match)
        removed = match
    config.save(cfg)
    success(f"Eliminada {removed}")


# --- char ---------------------------------------------------------------------


@char_app.command("list")
def char_list(
    missing: Annotated[
        bool, typer.Option("--missing", "-m", help="Solo los que no tienen clase.")
    ] = False,
    account: AccountOpt = None,
) -> None:
    """Lista los personajes encontrados en WTF y su clase."""
    cfg = config.load()
    r = roster.load()
    chars = wow.scan(cfg.paths)
    if account:
        chars = [c for c in chars if c.account.casefold() == account.casefold()]

    table = Table()
    for col in ("Cuenta", "Reino", "Personaje", "Clase"):
        table.add_column(col)
    seen = set()
    for c in chars:
        key = (c.account.casefold(), c.realm.casefold(), c.name.casefold())
        if key in seen:  # mismo personaje en dos instalaciones
            continue
        seen.add(key)
        cls = r.class_of(c.account, c.realm, c.name)
        if missing and cls is not None:
            continue
        table.add_row(
            c.account, c.realm, c.name, cls.value if cls else "[yellow]—[/yellow]"
        )

    if table.row_count:
        console.print(table)
    elif missing:
        success("Todos los personajes tienen clase.")
    else:
        info("No se encontraron personajes.")


def _resolve(
    candidates: list[tuple[str, str, str]],
    name: str,
    realm: str | None,
    account: str | None,
) -> list[tuple[str, str, str]]:
    """Filtra (cuenta, reino, nombre) sin distinguir mayúsculas y quita duplicados."""
    out: dict[tuple[str, str, str], tuple[str, str, str]] = {}
    for acc, rlm, nm in candidates:
        if nm.casefold() != name.casefold():
            continue
        if realm and rlm.casefold() != realm.casefold():
            continue
        if account and acc.casefold() != account.casefold():
            continue
        out.setdefault((acc.casefold(), rlm.casefold(), nm.casefold()), (acc, rlm, nm))
    return list(out.values())


def _ambiguous(matches: list[tuple[str, str, str]]) -> WowcfgError:
    lines = "\n".join(f"  {n} - {r} (cuenta {a})" for a, r, n in matches)
    return WowcfgError(
        f"Hay varios personajes con ese nombre:\n{lines}\nUsa --realm y/o --account."
    )


@char_app.command("set")
def char_set(
    name: Annotated[str, typer.Argument(metavar="NAME", help="Nombre del personaje.")],
    class_: Annotated[
        Class_, typer.Argument(metavar="CLASS", case_sensitive=False, help="Clase.")
    ],
    realm: RealmOpt = None,
    account: AccountOpt = None,
) -> None:
    """Asigna la clase de un personaje."""
    cfg = config.load()
    found = [(c.account, c.realm, c.name) for c in wow.scan(cfg.paths)]
    matches = _resolve(found, name, realm, account)

    if not matches:
        if realm and account:
            warn(
                f"{name} - {realm} ({account}) no está en WTF; se registra igualmente."
            )
            matches = [(account, realm, name)]
        else:
            raise WowcfgError(
                f"No se encontró `{name}` en ninguna instalación. "
                "Si aún no ha entrado al juego, indica --realm y --account para registrarlo igualmente."
            )
    if len(matches) > 1:
        raise _ambiguous(matches)

    acc, rlm, nm = matches[0]
    r = roster.load()
    r.set(acc, rlm, nm, class_)
    roster.save(r)
    success(f"{nm} - {rlm} ({acc}): {class_.value}")


@char_app.command("unset")
def char_unset(
    name: Annotated[str, typer.Argument(metavar="NAME", help="Nombre del personaje.")],
    realm: RealmOpt = None,
    account: AccountOpt = None,
) -> None:
    """Quita la clase registrada de un personaje."""
    r = roster.load()
    matches = _resolve(
        [(e.account, e.realm, e.name) for e in r.characters], name, realm, account
    )
    if not matches:
        raise WowcfgError(f"`{name}` no tiene clase registrada.")
    if len(matches) > 1:
        raise _ambiguous(matches)
    acc, rlm, nm = matches[0]
    r.unset(acc, rlm, nm)
    roster.save(r)
    success(f"{nm} - {rlm} ({acc}): sin clase")


# --- backup -------------------------------------------------------------------


@backup_app.command("list")
def backup_list() -> None:
    """Muestra las copias de seguridad, de la más reciente a la más antigua."""
    backups = backup.list_backups()
    if not backups:
        info("No hay copias de seguridad.")
        return
    table = Table()
    for col in ("ID", "Fecha", "Archivos", "Instalaciones"):
        table.add_column(col)
    for m in backups:
        table.add_row(
            m.id,
            m.created.strftime("%Y-%m-%d %H:%M"),
            str(len(m.entries)),
            "\n".join(str(p) for p in m.installs),
        )
    console.print(table)


@backup_app.command("restore")
def backup_restore(
    backup_id: Annotated[
        str | None,
        typer.Argument(metavar="ID", help="Copia a restaurar. Por defecto, la última."),
    ] = None,
    yes: YesOpt = False,
) -> None:
    """Deshace un `apply`: restaura los archivos y borra los que creó."""
    m = backup.get(backup_id)
    created = sum(e.backup is None for e in m.entries)
    info(
        f"Copia {m.id} ({m.created:%Y-%m-%d %H:%M}): {len(m.entries) - created} archivo(s) a restaurar, "
        f"{created} a borrar."
    )
    if not yes:
        typer.confirm("¿Continuar?", abort=True)
    _ensure_wow_closed()
    restored, deleted = backup.restore(m)
    success(f"Restaurados {restored}, borrados {deleted}.")


# --- entrada ------------------------------------------------------------------


def main() -> None:
    app()
