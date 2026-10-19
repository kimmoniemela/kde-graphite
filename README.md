# Graphite

A minimal KDE Plasma theming and keyboard-workflow project.

Charcoal surfaces, muted sage, monospace fonts, Breeze decorations and contour
wallpapers. Plasma provides the panels, Pager, application activation, global
shortcuts, window management and independent virtual desktops.

![Illustrative Graphite preview](theme/org.kde.graphite.desktop/contents/previews/preview.png)

## Install

Run from this checkout as your normal user inside Plasma:

```sh
python3 install.py doctor install
python3 install.py install --dry-run
python3 install.py install
```

Log out and back into KDE, then run `python3 install.py check`. Installation
never downloads software, runs a package manager, or requires sudo.

The workflow supports Plasma **6.7+ on Wayland**, one or two monitors and
Python 3.10+. It needs PySide6 (QtCore, QtGui, QtDBus), libxkbcommon, Fontconfig,
GDBus, kscreen-doctor, and KDE's existing shortcut services. Default-application
resolution also uses kreadconfig6 and kstart, and xdg-mime when available.
No custom applet, Plasma5Support executable engine or Qt development tools are
needed. Doctor checks the installed runtime before making changes.

## Appearance only

```sh
python3 install.py doctor theme
python3 install.py theme --dry-run
python3 install.py theme
```

The default command, `python3 install.py`, also applies appearance only.
This profile supports Plasma 6 with Python 3.10+, Fontconfig, GDBus and Breeze;
it does not require PySide6 or any workflow helpers. Missing fonts fall back to
Fira Code or the system monospace family.

Both profiles apply Graphite's palette, fonts, Breeze styling, wallpaper and
lock-screen appearance. They preserve existing panels, desktop effects,
animation speed, focus policy, GTK integration preferences and third-party
KWin scripts. They do not reset earlier user or Graphite settings to assumed
defaults. [Exact scope and recovery](docs/architecture.md).

## Keyboard workflow

Super+1–5 selects the primary monitor's five desktops; Super+6–0 selects the
secondary monitor's five desktops. Add Shift to move a window without following
it. With one screen, both number banks address the same five desktops.
Super+Ctrl+1–5 uses KWin's native desktop actions on the focused monitor.
Finnish and US shifted number rows are supported.

Application shortcuts use native KGlobalAccel desktop actions. KDE's default
terminal, browser, file manager and editor are resolved when their shortcuts
are pressed. Explicit overrides launch directly when possible. Missing optional
applications are reported and omitted. Unmanaged shortcut conflicts stop
installation instead of replacing another script's bindings.
[All shortcuts](docs/shortcuts.md).

No local settings file is required. To change a command or disable a shortcut,
create `settings.local.json`:

```json
{
  "applications": {
    "Editor": ["kate"],
    "ProcessMonitor": []
  }
}
```

Pass `--settings settings.local.json` to doctor and install. Omitted values use
portable defaults; `["@default"]` selects dynamic resolution. This file is
ignored by Git. Empty output names enable monitor detection from KDE's display
priority; avoid transferring machine-specific monitor names.

The optional `"altgr_as_super": true` makes AltGr another Super key, retaining
the ordinary Super keys. It replaces AltGr's character-modifier function;
see [keyboard details](docs/shortcuts.md).

## Panels and optional components

Use Plasma's own panel editing and **Pager** widget. Graphite never creates,
resets or replaces panels. Native Pager uses the same desktop names/numbers on
both monitors; the secondary keyboard bank still uses 6–0. Existing installed
Graphite widgets remain intact until you replace them manually in Plasma.
The previews illustrate appearance, not an automatically installed panel layout.

- `python3 install.py wheel`: build/install the optional native Super+wheel
  workspace effect using existing CMake, Qt/KF6 and KWin development files.
  Rebuild after KWin upgrades; log in again to activate it. No packages installed.
- `python3 install.py build-theme`: build a standalone native Global Theme archive.
- [SDDM login theme](sddm/README.md): separate, explicit system installation with
  its own preflight, administrator access and backups.

[Optional installation details](docs/install-options.md).

## Updates and recovery

Update the checkout and repeat the same installation command. Unchanged payload
and configuration files are not replaced. Each operation keeps a private backup
under `$XDG_STATE_HOME/kde-graphite/backups/` (default `~/.local/state`).

```sh
python3 install.py restore --dry-run
python3 install.py restore
```

Restore accepts an explicit backup directory, or unwinds the latest operation
and then its predecessors. Selected KConfig entries are restored while later unrelated preferences are
retained; Graphite-owned payload files are recovered as whole files. Wallpapers
are restored through Plasma without restoring panel layouts. This
also protects panels when reading older whole-containment backups. Log out and
back in after recovery. Backups are machine-specific.

Upgrades retire Graphite's old launcher script and obsolete utility bindings,
with backups, but leave independently installed scripts and panel widgets alone.
There is no blanket uninstall/reset command; use the relevant backup to undo an
installation. XDG directory overrides are supported.

See [architecture and limitations](docs/architecture.md),
[component/dependency inventory](docs/components.md), and
[validation instructions](docs/install-options.md#verification).
