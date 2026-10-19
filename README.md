# KDE Graphite

**A minimal KDE Plasma theming and keyboard-workflow project.**

Graphite brings a consistent charcoal-and-sage appearance and a monitor-aware
keyboard workflow to an existing Plasma desktop. It is for people who want quick
application access and predictable workspace keys while keeping KDE's native
window management, panels and settings.

**Native Plasma first:** Graphite uses Breeze, KGlobalAccel and KWin actions,
adding small integrations only where its workflow needs them.

[Installation](#installation) · [Shortcuts](#keyboard-shortcuts) ·
[Configuration](docs/configuration.md) · [Troubleshooting](docs/troubleshooting.md) ·
[Architecture](docs/architecture.md) · [Development](docs/development.md)

## Appearance preview

<img src="theme/org.kde.graphite.desktop/contents/previews/preview.png" alt="Illustration of Graphite's charcoal surfaces, muted sage accents and monospace typography" width="960">

This existing project image is an **illustration, not a desktop screenshot**.
Its panel layout and example applications are not installed by Graphite. Your
Plasma panels remain under your control.

## Features

| Area | Included |
| --- | --- |
| Appearance | Native Graphite Global Theme, color scheme, monospace fonts, Breeze widgets/decorations and two contour wallpapers; matching lock-screen styling |
| Keyboard workflow | Application and window shortcuts, dynamic KDE default applications, explicit application overrides and shortcut conflict checks |
| Workspaces | Five independent desktops per monitor, fixed primary/secondary number-key banks, window sending, clamped navigation and a session-local scratchpad |
| Keyboard layouts | Finnish/US shifted number-row handling; optional AltGr as an additional Super key |
| Mouse wheel | Optional native KWin effect for Super+wheel workspace switching; requires a local build and a new login |

## Requirements

| Profile | Requirements |
| --- | --- |
| Appearance | Plasma/KWin **6.x**, Python **3.10+**, `gdbus`, `fc-list`, and installed Breeze style, decoration, desktop-theme and dark-icon assets |
| Full workflow | Above, plus Plasma **6.7+ on Wayland**, one or two connected monitors, `kscreen-doctor`, PySide6 (`QtCore`, `QtGui`, `QtDBus`) and `libxkbcommon` |
| Default applications | `kreadconfig6` and `kstart` for the relevant KDE defaults; `xdg-mime` enables MIME-based selection; applications must already be installed |
| Optional wheel | CMake, a C++20 compiler, matching KWin development headers/library, Qt 6 Core/Gui/Widgets/Quick/DBus, KF6 CoreAddons and Config development files |
| Optional login theme | SDDM with the Qt 6 and Plasma Breeze QML modules checked by its [separate installer](sddm/README.md) |

Run inside Plasma as your normal desktop user. Doctor checks commands, services,
versions and required runtime assets; Graphite does not install dependencies.
Appearance preflight does not require Wayland, but X11 behavior is unverified.
More than two monitors can use the appearance profile only.

Earlier revisions had local checks on Fedora 44 / Plasma 6.7.5 and CachyOS
(Arch-based) / Plasma 6.8.0. These observations are not clean-install certification
of the current workflow. No distribution-wide support guarantee is claimed;
the current validation scope is described in [Development](docs/development.md#validation-scope).

## Installation

Obtain a source checkout, then run all commands from its root:

```sh
git clone https://github.com/kimmoniemela/kde-graphite.git
cd kde-graphite
```

### Standard installation

Apply appearance, shortcuts and the workspace workflow:

```sh
python3 install.py doctor install
python3 install.py install --dry-run
python3 install.py install
```

**Log out and back into Plasma**, then run `python3 install.py check`.
The desktop installer needs no sudo and performs no downloads or package installs.
It preserves existing panels and independent KWin scripts.

### Appearance only

```sh
python3 install.py doctor theme
python3 install.py theme --dry-run
python3 install.py theme
```

Log out and back in to apply all appearance settings. This profile does not
install workspace helpers or change shortcuts. Running `python3 install.py`
without a command also selects this profile.

### Optional mouse wheel

After installing the workspace workflow and the build dependencies above:

```sh
python3 install.py wheel --dry-run
python3 install.py wheel
```

Log out and back in, then run `python3 install.py check --with-wheel`.
Super+wheel up selects the next desktop; down selects the previous one, on the
focused monitor. Navigation stops at desktops 1 and 5. Rebuild after KWin upgrades.
See [wheel compatibility](docs/architecture.md#mouse-wheel-integration).

### Optional SDDM login theme

SDDM installation is separate and changes system files:

```sh
python3 sddm/install.py --dry-run
sudo python3 sddm/install.py
```

No display manager is restarted. Read the [SDDM guide](sddm/README.md) for
prerequisites, previewing and its separate recovery procedure.

## Keyboard shortcuts

Super is KDE's Meta modifier, usually the Windows key. These are the defaults in
[shortcuts.json](shortcuts.json) and the workspace table in [install.py](install.py).
Application shortcuts are installed only when the application/service is available
and enabled. Nonconflicting existing alternatives remain available.

### Applications and session

| Shortcut | Action | Context |
| --- | --- | --- |
| Super+Enter | Default terminal | KDE preference or override |
| Super+E | Default file manager | MIME default or override |
| Super+T | Default text editor | MIME default or override |
| Super+W | Default browser | KDE/MIME default or override |
| Super+C; Calculator key | Calculator | Installed candidate or override |
| Ctrl+Shift+Escape | System monitor | Installed candidate or override |
| Super+Space | KRunner | Native KDE service |
| Super+Z | System Settings | Native KDE service |
| Super+period | Emoji picker | Native KDE service |
| Super+V | Clipboard popup at pointer | Plasma clipboard action |
| Print; Super+Print | Region screenshot; full-screen screenshot | Spectacle actions |
| Super+L | Lock session | Native KDE action |
| Super+Alt+C | Log out / show logout prompt | Native KDE action |

### Windows

| Shortcut | Action | Context |
| --- | --- | --- |
| Super+Q | Close | Active window |
| Super+D | Maximize/restore | Active window |
| Super+F | Toggle fullscreen | Active window |
| Super+Escape | Select a window to force-close | Native KWin action |
| Alt+Tab; Super+Tab | Window switcher | Native KWin action |
| Super+Alt+Left/Right | Focus screen to the left/right | Native KWin action |
| Super+Plus/Minus | Zoom in/out | Native KWin actions; keypad supported |
| Super+Shift+S | Add window to scratchpad and hide scratchpad | Active window |
| Super+S | Show/hide scratchpad | Show on focused monitor/desktop |

### Workspaces

| Shortcut | Action | Monitor/context |
| --- | --- | --- |
| Super+1–5 | Select desktop 1–5 | Primary monitor |
| Super+6,7,8,9,0 | Select desktop 1,2,3,4,5 | Secondary monitor |
| Super+Shift+1–5 | Send window to desktop 1–5 | Primary monitor; do not follow |
| Super+Shift+6,7,8,9,0 | Send window to desktop 1,2,3,4,5 | Secondary monitor; do not follow |
| Super+Ctrl+1–5 | Select desktop 1–5 | Focused monitor; native KWin actions |
| Super+Ctrl+Left/Right | Previous/next desktop | Focused monitor; stop at boundaries |
| Super+Ctrl+Shift+Left/Right | Send window to previous/next desktop | Active window; do not follow |
| Super+Ctrl+Down | First empty desktop | Focused monitor; ignores minimized windows |
| Super+wheel up/down | Next/previous desktop | Focused monitor; optional effect |

With one monitor, both number-key banks target its five desktops. Native Pager
uses shared desktop names/numbers on both screens; the secondary key bank does
not create five additional global desktops.

The layout helper reads the active Finnish/US layout and updates shifted
number-row aliases, so window sending follows the physical number positions.
Configure layouts in KDE; Graphite does not select them. See
[keyboard configuration](docs/configuration.md#keyboard-layouts-and-altgr).

## Configuration

Create an optional, Git-ignored `settings.local.json`, then pass
`--settings settings.local.json` to doctor and installation. For example:

```json
{
  "font": "Fira Code",
  "font_size": 10,
  "applications": {
    "Editor": ["kate"],
    "ProcessMonitor": []
  }
}
```

The [configuration guide](docs/configuration.md) covers every setting, dynamic
application defaults, AltGr, monitor selection, shortcut customization and
appearance files. Use Plasma's native panel editor and Pager for workspace display.

## Maintenance and recovery

Update with `git pull --ff-only`, then repeat the appropriate doctor and
installation commands with the same settings file. A new login activates changes.
Use `python3 install.py check` after installing the workflow; doctor is the
preflight for appearance-only installations.

Every installation saves a local backup under
`${XDG_STATE_HOME:-$HOME/.local/state}/kde-graphite/backups/`. To undo the latest
operation:

```sh
python3 install.py restore --dry-run
python3 install.py restore
```

Restore also accepts a backup directory. Log out and back in immediately after
recovery. There is no blanket uninstall/reset command; use the relevant backups.
For recovery limits and common failures, see [Troubleshooting](docs/troubleshooting.md).
Standalone theme packaging and contributor checks are in [Development](docs/development.md).

## Project scope

Graphite uses native Plasma components wherever practical. It does not replace
KWin, bundle automatic tiling or install another desktop environment. Its full
workflow runs one KWin script and one event-driven keyboard-layout helper;
application-default resolution is short-lived. The wheel effect is optional.

Configuration changes are limited to appearance and the documented workflow.
Unrelated KDE preferences, user panels and independent scripts are preserved;
known shortcut conflicts and recovery limitations are explained in the guides.
No claim is made that desktop crashes or compatibility problems can be eliminated.

## Contributing and license

See [Development](docs/development.md) for the repository map, checks and
contribution workflow. Project code is [MIT-licensed](LICENSE), with separately
licensed KDE-derived assets, SDDM components and wheel code listed in
[third-party notices](THIRD_PARTY.md).
