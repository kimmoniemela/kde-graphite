# Tiling

Graphite uses Kröhnkite 0.9.9.2 with local patches for per-monitor desktops,
window controls and shutdown behavior. It runs inside KWin; KDE
remains the compositor and desktop. Source and provenance are in
[`vendor/krohnkite/`](../vendor/krohnkite/) and [THIRD_PARTY.md](../THIRD_PARTY.md).

`python3 install.py install --with-tiling` explicitly installs this copy and
enables its KWin script at the next KDE login. Normal `install`, `theme` and
Global Theme import do not install or configure it. Normal installation keeps
existing tiler files, settings, shortcuts and enabled state. Disable it in
KWin Scripts settings when you want floating windows.

## Controls

Open **System Settings → Window Management → KWin Scripts**:

- Check **Kröhnkite** and click **Apply** to enable automatic tiling.
- Uncheck **Kröhnkite** and click **Apply** for ordinary window management.

Disabling the script disconnects its window and workspace handlers. Windows
keep their last positions and sizes and can be moved, resized and maximized
normally. Enabling it arranges eligible windows again. KDE saves the checkbox
state across logins.

This is the only tiling control. There is no separate runtime mode, polling
helper, Python toggle or bar toggle. Settings saved by the former Python
control are removed only during an explicit `--with-tiling` upgrade.

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
is disabled. Maximize/restore (Super+D), fullscreen (Super+F),
closing (Super+Q), workspace moves and application launching remain separate.
All normal windows retain minimize, maximize/restore and close buttons,
including tiled windows. Fullscreen hides decorations normally.

Use Kröhnkite's configuration button in KWin Scripts for layout and floating
rules. Installer defaults are in [`config.json`](../config.json), under
`kwinrc` → `Script-krohnkite`; using `--with-tiling` reapplies those
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

For a read-only full-setup check:

```sh
python3 install.py check
```

This checks that Kröhnkite's loaded state matches its KWin Scripts setting,
plus the full setup's workspace and application bindings. It does not test
window geometry. If windows still arrange themselves with Kröhnkite unchecked,
confirm you clicked Apply and log out/back in to clear code from an older
installation. The current shutdown behavior is covered by automated callback
and geometry-guard tests; a settings-toggle test in a fresh graphical session
is still needed after this update.

Replacing this copy through Get New Scripts can overwrite Graphite's patches;
the behavior described here applies to the bundled version.
