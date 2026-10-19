# Configuration

[README](../README.md) · [Architecture](architecture.md) · [Troubleshooting](troubleshooting.md)

Commands below run from the repository root. Personal preferences belong in
`settings.local.json`, which Git ignores. It is optional: omitted values come
from [settings.json](../settings.json), and application entries merge individually.

```json
{
  "font": "Fira Code",
  "font_size": 10,
  "altgr_as_super": true,
  "primary_output": "",
  "secondary_output": "",
  "applications": {
    "Editor": ["kate"],
    "ProcessMonitor": []
  }
}
```

Apply personal preferences to the workflow with:

```sh
python3 install.py doctor install --settings settings.local.json
python3 install.py install --settings settings.local.json --dry-run
python3 install.py install --settings settings.local.json
```

Use `theme` instead of `install` for appearance only. Log out and back in after
applying changes. Always pass the settings file on later installations; it is not
automatically discovered or saved as the next invocation's defaults.

## Supported settings

| Setting | Default | Meaning |
| --- | --- | --- |
| `font` | `FiraCode Nerd Font Mono` | Installed UI and monospace font family; no commas or line breaks |
| `font_size` | `10` | Base size, 6–32; smaller/title fonts are derived from it |
| `altgr_as_super` | `false` | Opt-in additional Super key; full installation only |
| `primary_output` | `""` | Exact connected output name, or automatic selection |
| `secondary_output` | `""` | Exact connected output name, or automatic selection |
| `applications` | All six entries use `["@default"]` | Per-application command arrays, described below |

Setting and application names are case-sensitive. Missing fonts fall back to
Fira Code when installed, then `monospace`. No fonts are downloaded or installed.
Monitor and application preferences are unused by the appearance profile.

## Applications

Supported names are `Terminal`, `Files`, `Editor`, `Browser`, `Calculator` and
`ProcessMonitor`. Each accepts one of:

| Value | Behavior |
| --- | --- |
| `["@default"]` | Resolve the application when the shortcut is pressed |
| `["program", "argument"]` | Execute an explicit argument array; ordinary overrides use KDE directly |
| `[]` | Omit this application's action from the generated shortcut service |

Arguments are not shell commands. Pipes, redirections and environment assignments
are not interpreted as shell syntax. Explicit commands must exist before
installation; preflight reports missing executables.

[applications.py](../applications.py) resolves defaults in this order:

| Application | Selection |
| --- | --- |
| Terminal | KDE `TerminalService`, then legacy `TerminalApplication` if no service is set, then Konsole or xterm |
| Browser | KDE `BrowserApplication`, otherwise the HTTPS MIME default when `xdg-mime` is available, then an installed browser candidate |
| Files | `inode/directory` MIME default when available, then Dolphin, Nautilus or Thunar |
| Editor | `text/plain` MIME default when available, then KWrite, Kate, GNOME Text Editor or Mousepad |
| Calculator | KCalc, GNOME Calculator or Qalculate GTK |
| ProcessMonitor | Plasma System Monitor or GNOME System Monitor |

Browser fallback candidates are Firefox, Chromium, Google Chrome and Falkon.
A selected desktop service must have an installed application entry. If it is
missing, that action is omitted and reported at installation; it does not silently
replace an explicitly selected but missing desktop service. Install the desired
application and rerun installation to add an omitted action. An already installed
dynamic action follows later default changes without reinstalling.

Use KDE's Default Applications settings for terminal/browser selection and file
associations for MIME defaults. KDE expands desktop entries through `kstart`.
Calculator and process monitor use candidate selection, not a KDE default-app role.

## Keyboard shortcuts

The [README tables](../README.md#keyboard-shortcuts) list the shipped bindings.
There are two sources:

- [shortcuts.json](../shortcuts.json): existing KDE action IDs under `native`, and
  application bindings under `applications`.
- `workspace_shortcuts()` in [install.py](../install.py): Graphite's monitor-aware
  actions. The installer inserts this table into the workspace JavaScript.

Personal settings support application commands, not arbitrary key mappings.
For a local source customization, edit the relevant table, then reinstall and
log in again. Semicolons separate alternative key sequences. `Meta` is Super.
Existing nonconflicting alternatives are retained, so changing a binding does
not necessarily remove the previous key. Remove unwanted alternatives in KDE's
Shortcuts settings. Native actions can also be adjusted there between installs;
a later Graphite installation ensures its configured keys are present again.

The layout helper manages shifted number-row aliases at login and on layout
changes. Rebinding those move actions in KDE alone may be overwritten by the
helper. Keep number-row changes consistent with
[scripts/workspace-keys.py](../scripts/workspace-keys.py); arbitrary remapping of
that workflow is a source modification, not a supported JSON preference.

Conflicts with unknown actions stop installation. Known native counterparts can
lose only the conflicting key; other alternatives remain. See
[conflict recovery](troubleshooting.md#shortcut-conflicts).

## Keyboard layouts and AltGr

Configure Finnish and/or US layouts and variants through KDE's keyboard settings.
Graphite reads the active layout and uses XKB to derive shifted number symbols;
it does not change layout selection or the layout-switching shortcut. The helper
updates aliases on KDE layout signals rather than polling. Other layouts are not
part of the verified keyboard scope.

`"altgr_as_super": true` maps right Alt to an extra Super key while retaining
both ordinary Super keys. This replaces AltGr's third-level character input,
including Finnish AltGr combinations. It is independent of Finnish/US support;
leave it off if those character combinations are needed.

Full installation adds the `graphite:altgr_super` XKB option and user rules/symbols
under `$XDG_CONFIG_HOME/xkb/`, preserving other options and layout selections.
The default `false` leaves current mappings untouched; it does **not** remove a
previously installed mapping. Restore the relevant backup to undo it. A new
Plasma login is required.

## Workspace behavior

Full installation sets five native desktops and enables independent per-output
selection. It preserves desktop names and rows. The number-key banks target
primary/secondary output roles; with one display both address the same desktops.
The secondary keys `6,7,8,9,0` address local desktops `1,2,3,4,5`.

Automatic roles use connected, enabled outputs ordered by KDE display priority.
Inspect output names with:

```sh
kscreen-doctor -j
```

Explicit names must match a connected output. Clear an override to `""` and
reinstall after changing displays or priority. More than two connected monitors
are rejected by full installation. Hot-plug behavior needs graphical testing.
There is no setting for another desktop count or wrapping: Graphite's relative
navigation clamps at the five-desktop boundaries.

Use Plasma's native Pager on user-managed panels. Desktop names are shared
across monitors, so the secondary key bank does not change Pager labels.
Scratchpad membership is session-local; showing it moves windows to the focused
output/desktop and hiding it restores keep-above changes Graphite made.

## Appearance sources

| Source | Used for |
| --- | --- |
| [config.json](../config.json) | Breeze decoration/titlebar styling and lock-screen presentation |
| [Canonical palette](../assets/color-schemes/TerminalGraphite.colors) | Installed color scheme and generated Global Theme palette |
| [Global Theme defaults](../theme/org.kde.graphite.desktop/contents/defaults) | Native standalone package defaults; fonts are generated by `theme.py` |
| [Wallpaper packages](../theme/org.kde.graphite.desktop/contents/wallpapers) | Two static contour images |
| [theme.py](../theme.py) | Shared appearance configuration for both installation profiles |

Use KDE settings for personal color, font, wallpaper and panel changes. Repeating
installation reapplies Graphite's selected appearance values. Source edits are
appropriate for maintaining a variant; `settings.local.json` accepts only the
preferences listed above. There is no arbitrary KConfig overlay or custom
wallpaper-path setting.

The optional wheel and SDDM integrations have separate installation commands;
neither is enabled by this personal-settings file. See the
[README](../README.md#installation) and [SDDM guide](../sddm/README.md).
