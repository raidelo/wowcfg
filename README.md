# wowcfg

Aplica una plantilla de configuración de addons de WoW WotLK (3.3.5) a
todas las cuentas y personajes de una o varias instalaciones, con copia de
seguridad de todo lo que toca.

La plantilla vive en un repositorio git aparte (por defecto
[raidelo/wow-config](https://github.com/raidelo/wow-config)).

## Instalación

Necesitas Python 3.11+ y `git`.

```sh
uv tool install git+https://github.com/raidelo/wowcfg
```

## Uso rápido

```sh
wowcfg init                       # pregunta el repo y la carpeta del WoW, y descarga la plantilla
wowcfg char list --missing        # personajes que aún no tienen clase
wowcfg char set Lockito warlock   # asigna la clase (no distingue mayúsculas)
wowcfg apply --dry-run            # muestra qué cambiaría
wowcfg apply                      # aplica (con WoW cerrado)
wowcfg backup restore             # deshace el último apply
```

## Comandos

| Comando                                                     | Qué hace                                                                     |
| ----------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `init [--repo URL] [--path DIR]... [--ref REF] [--force]`   | Crea la configuración. Pregunta lo que falte.                                |
| `fetch`                                                     | Clona o actualiza la plantilla.                                              |
| `apply [--dry-run] [--path DIR] [--account NOMBRE] [--yes]` | Aplica la plantilla.                                                         |
| `path list` / `path add DIR` / `path remove DIR\|N`         | Gestiona las instalaciones de WoW.                                           |
| `char list [--missing] [--account A]`                       | Personajes encontrados en `WTF` y su clase.                                  |
| `char set NOMBRE CLASE [--realm R] [--account A]`           | Asigna la clase. Reino y cuenta solo hacen falta si el nombre está repetido. |
| `char unset NOMBRE [--realm R] [--account A]`               | Quita la clase registrada.                                                   |
| `backup list` / `backup restore [ID] [--yes]`               | Lista o restaura copias de seguridad.                                        |

Clases válidas: `dk`, `druid`, `hunter`, `mage`, `paladin`, `priest`,
`rogue`, `shaman`, `warlock`, `warrior`.

## Qué hace `apply`

Para cada instalación registrada:

| En la plantilla                             | Destino                                                                                                                               |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `outer/Config.wtf`                          | `WTF/Config.wtf`                                                                                                                      |
| `SavedVariables/*.lua`                      | `WTF/Account/<cuenta>/SavedVariables/`, con `profileKeys` reescrito para que todos los personajes de esa cuenta usen el perfil `main` |
| `bindings-cache.wtf`, `macros-cache.txt`, … | `WTF/Account/<cuenta>/`                                                                                                               |
| `character/common/`                         | cada personaje                                                                                                                        |
| `character/<clase>/`                        | personajes de esa clase; se aplica después de `common`, así que gana si ambos tienen el mismo archivo                                 |

Dentro de `character/<x>/`, los `.lua` de `SavedVariables/` van a la
carpeta `SavedVariables` del personaje y los archivos sueltos a la carpeta
del personaje.

Solo se copian archivos sueltos que WoW reconoce (`bindings-cache.wtf`,
`macros-cache.txt`, `chat-cache.txt`, `layout-local.txt`, `AddOns.txt`,
`config-cache.wtf`). El resto se ignora con un aviso, así un README del
repositorio de plantilla nunca acaba dentro de `WTF/`.

Detalles:

- Se niega a ejecutarse con WoW abierto, porque el juego sobrescribe los
  SavedVariables al salir.
- Los personajes sin clase registrada reciben solo `common` y se avisa.
- Los personajes creados después de un `apply` no están en `profileKeys`
  y usarán el perfil por defecto del addon hasta el siguiente `apply`.
- Los archivos que ya tienen el contenido correcto no se tocan; si no
  cambia nada, no se crea copia de seguridad.

## Copias de seguridad

Cada `apply` que modifica algo crea `backups/<fecha>/` con un manifiesto de
los archivos tocados. `backup restore` devuelve cada uno a su estado
anterior y borra los que `apply` creó. Las copias de distintas
instalaciones van separadas.

## Dónde guarda sus datos

En el directorio de aplicación del sistema: `%APPDATA%\wowcfg` en Windows,
`~/.config/wowcfg` en Linux y `~/Library/Application Support/wowcfg` en
macOS. Se puede cambiar con la variable de entorno `WOWCFG_HOME`.

- `config.json`: repositorio, rama/tag, perfil e instalaciones.
- `characters.json`: clase de cada personaje.
- `template/`: clon de la plantilla.
- `backups/`: copias de seguridad.

El perfil asignado en `profileKeys` es `main`; se puede cambiar con el
campo `profile` de `config.json`.

## Desarrollo

```sh
uv sync
uv run pytest
```
