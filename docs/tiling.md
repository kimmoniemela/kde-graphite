# Tiling

Graphite uses Kröhnkite 0.9.9.2 with local patches for per-monitor desktops,
window controls and shutdown/suspension behavior. It runs inside KWin; KDE
remains the compositor and desktop. Source and provenance are in
[`vendor/krohnkite/`](../vendor/krohnkite/) and [THIRD_PARTY.md](../THIRD_PARTY.md).

`python3 install.py install` installs this copy and enables its KWin script at
the next KDE login. `python3 install.py theme` and importing the Global Theme
archive do not install or enable it. A previously saved suspended mode is
retained by the full installer.

## Controls

Run from the repository, in the target user's KDE session, without sudo:

```sh
python3 install.py tiling off
python3 install.py tiling on
python3 install.py tiling toggle
```

`off` suspends automatic arrangement while keeping the script loaded. Windows
retain their last positions and sizes; they can then be moved, resized and
maximized normally. `on` arranges eligible windows again. The mode is saved in
`kwinrc` and survives logout/login. There is no tiling toggle on the bar.

| State | Automatic arrangement | Kröhnkite shortcuts |
| --- | --- | --- |
| Script enabled, runtime mode on | Active | Active |
| Script enabled, runtime mode off | Suspended | Inactive |
| Script disabled in KWin Scripts | Inactive | Unavailable |

To disable the script, open System Settings → Window Management → KWin Scripts,
uncheck **Kröhnkite**, and apply. Its shutdown handler disconnects window and
workspace signals. To resume, enable it there and apply, then run
`python3 install.py tiling on` if its saved runtime mode was off. The CLI changes
the runtime mode; it does not enable or load a disabled script.

The script polls its settings every 500 ms. CLI success confirms the saved mode
and whether KWin reports the script loaded; it is not an acknowledgement from
the arrangement engine. Allow roughly half a second before testing a move.

## Layout and shortcuts

The default is a tile layout with six-pixel gaps. Layouts are tracked per
monitor, desktop and activity. Calculator and utility windows float by default;
scratchpad windows use the skip-pager floating exception.

| Keys | Action while tiling is active |
| --- | --- |
| Super+Arrows | Focus a window |
| Super+Shift+Arrows | Move a tile, or move a floating window |
| Super+Alt+Space | Toggle the focused window between tiled and floating |
| Super+J | Rotate the layout |

These bindings do not switch to KDE's native quick-tiling actions when Kröhnkite
is suspended or disabled. Maximize/restore (Super+D), fullscreen (Super+F),
closing (Super+Q), workspace moves and application launching remain separate.
All normal windows retain minimize, maximize/restore and close buttons,
including tiled windows. Fullscreen hides decorations normally.

Use Kröhnkite's configuration button in KWin Scripts for layout and floating
rules. Installer defaults are in [`config.json`](../config.json), under
`kwinrc` → `Script-krohnkite`; rerunning the full installer reapplies those
listed defaults. [All shortcuts](shortcuts.md).

## Other Graphite components

Workspace routing, the workspace widget, launchers and the window-controls
helper remain active when Kröhnkite is off. They handle explicit workspace
actions, occupied-workspace indicators, application launching and titlebar
controls. They do not automatically tile or enforce window sizes. The optional
wheel effect dispatches workspace shortcuts. See [components](components.md).

## Troubleshooting

After installing or updating script files, log out and back into KDE before
testing. Running scripts can retain old code. Repeated live unload/reload cycles
were a suspected trigger for the recorded KWin crash; the installer defers
script changes until the next login.

For read-only checks:

```sh
python3 install.py check
python3 scripts/tiling-control.py status
```

`check` validates the full setup's configured shortcuts and loaded scripts;
it does not test window geometry. The status helper prints JSON:
`available` means an installed Kröhnkite package was found; `enabled` means
runtime mode is on and KWin reports the script loaded. It does not distinguish
an unloaded script from a deliberately suspended one when `enabled` is false.

If `tiling on` reports that KWin did not apply the requested mode, check that
Kröhnkite is enabled in KWin Scripts and that a new login has loaded the
installed version. The command may already have saved the requested mode.
Replacing this copy through Get New Scripts can overwrite Graphite's patches;
the behavior described here applies to the bundled version.
