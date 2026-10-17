# Graphite setup history

Updated 2026-10-17. This records the KDE changes made during this setup and the
final choices. Superseded choices are identified below.

## Scope

The starting request was a minimal, terminal-oriented KDE desktop with an
i3/Sway-style workflow: dark colors, little visual noise and no blur or RGB
styling. Changes were limited to KDE. Hyprland configuration was read to copy
bindings and was not edited. GNOME, Sway, i3, Waybar and Noctalia configuration
were excluded from the installer.

KDE's GTK configuration synchronizer was disabled before applying the palette
to avoid propagating KDE appearance settings to the other installed desktops.

## Appearance and top bars

- Charcoal background: `#111416`.
- Muted sage accent: `#a6b8a1`.
- Monospace UI font: FiraCode Nerd Font Mono. Installation falls back to
  Fira Code, then the system monospace font.
- Breeze widgets and dark icons.
- Opaque, nonfloating top bars, 28 pixels high.
- Compact workspace buttons and a text task list restricted to each monitor
  and its selected workspace.
- No pinned task launchers, audio badges, media tooltip controls or clock date.
- Visible tray items limited mainly to network, volume and battery; other items
  remain available in the overflow.
- Blur, contrast effects, decorative transitions and window shadows disabled.

The first quiet bar was on the external display. A matching bar was later
added to the laptop. The installer now creates a top bar on each connected
monitor and reuses existing top bars on subsequent runs.

## Tiling

Kröhnkite 0.9.9.2 was installed as a KDE-only tiler with six-pixel gaps.
Its source is pinned in `vendor/krohnkite/`; local changes support KWin 6.7's
independent per-monitor desktops and the requested decoration behavior.

The setup includes directional focus and tile movement, floating windows,
layout rotation, monitor moves and a scratchpad. The scratchpad uses minimized
floating windows; its membership lasts for the KDE session.

The wheel shortcut handler was built as a separate native KWin effect,
`kwin_hypr_scroll_desktop`. Its source is in `wheel/`. The original scroll
plugin was restored and disabled. Rebuild the new effect against the installed
KWin version after upgrades.

## Workspaces and monitor numbering

An initial ten-desktop arrangement was replaced because both bars displayed
all ten desktops. The final implementation uses **five native KDE desktops,
selected independently on each monitor**.

KDE shares desktop names across outputs. Graphite's workspace widget therefore
adds monitor-specific labels rather than creating ten global desktops:

| Display role | Bar labels | Select | Move active window |
| --- | --- | --- | --- |
| Primary | 1–5 | Super+1–5 | Super+Shift+1–5 |
| Secondary | 6–10 | Super+6–0 | Super+Shift+6–0 |

Key `0` means workspace 10. On this machine, the external `DVI-I-1` display is
primary and the laptop `eDP-1` display is secondary. New installations use
KDE's display priority; `primary_output` and `secondary_output` can override it.
With one monitor connected, both number groups address that monitor's five
desktops.

There was an intermediate mapping where Super+Shift+1–5 moved within the
current monitor. It was replaced with the table above so bar labels, switching
and window moves have the same destinations.

Moving a tiled window across monitors briefly suspends its tiling assignment,
then restores its previous state. This prevents the tiler from pulling it back
during KWin's output transfer.

## Shortcuts and application launching

Bindings were adapted from the existing Hyprland setup into KDE. The main
requested bindings are:

| Keys | Action |
| --- | --- |
| Super+Enter | Kitty |
| Super+Space | KRunner |
| Super+Q | Close active window |
| Super+Shift+number | Move window to the numbered workspace and monitor |
| Super+Wheel Up / Down | Next / previous workspace on the current monitor |
| Super+Alt+Space | Toggle floating |

Application shortcuts use real KWin QML shortcut handlers and a detached
launcher helper. The launcher uses distinct execution requests so repeated
presses can open additional windows. An earlier configuration that saved
bindings without working handlers was replaced.

The full mapping is in [shortcuts.md](shortcuts.md). Application commands can
be changed in `settings.local.json` without editing Hyprland.

## Window controls: final preference

The first appearance pass hid tiled titlebars and left only a close button on
decorated windows. This was later changed to the standard minimize,
maximize/restore and close buttons.

The final preference is **controls on all normal windows, including tiled
windows**. It supersedes the earlier preference for borderless tiles.

- Titlebar button order is `IAX`: minimize, maximize/restore, close.
- Maximized windows retain their titlebars.
- Kröhnkite's `noTileBorder` and `soleWindowNoBorders` settings are disabled.
- A KDE window-control script watches newly opened windows and restores their
  controls. The behavior applies to new Kitty and Konsole windows as well as
  existing windows.
- The tiler restores normal controls when it is unloaded.
- True fullscreen windows retain normal fullscreen behavior.

Kitty's shared configuration and GNOME's decoration settings were not changed.
The fix belongs to KDE, so it does not change terminal styling in another DE.

## Lock screen

The standard Plasma lock screen uses the matching solid charcoal background,
monospace clock and no media controls. Authentication and session security
settings were not replaced.

## Repository and Global Theme

The project was collected in the private `kimmoniemela/kde-graphite` repository.
It contains selected configuration, portable templates, scripts, licensed
third-party source, installation code and tests. Machine backups and diagnostic
screenshots are not part of the repository.

The appearance was packaged as **Graphite**, a Plasma Global Theme with ID
`org.kde.graphite.desktop`. It includes its palette, font defaults, Breeze
component choices, titlebar layout and preview images. Previews are generated
illustrations, not screenshots of personal applications.

Graphite appears in System Settings → Colors & Themes → Global Theme. Its
optional desktop layout creates top bars and uses Graphite's workspace widget
when the full setup is installed; otherwise it uses KDE's native pager.

The Global Theme and complete desktop setup live in the same repository.
The complete installer supplies workspace routing, launch bindings, tiling and
the wheel effect that a Global Theme package alone does not install.

## Files and installation

| Location | Purpose |
| --- | --- |
| `~/kde-graphite/` | Project source and documentation |
| `~/.config/` | Selected KDE settings |
| `~/.local/share/plasma/look-and-feel/org.kde.graphite.desktop/` | Installed Global Theme |
| `~/.local/share/plasma/plasmoids/` | Graphite workspace widget |
| `~/.local/share/kwin/scripts/` | Tiler, workspace, launcher and window-control scripts |
| `~/.local/share/kde-graphite/runtime/` | Generated runtime helpers |
| `~/.local/state/kde-graphite/backups/` | Local installation backups |
| `~/.local/share/kde-terminal-rice/` | Earlier setup helpers and diagnostics on this machine |

Use the current [README](../README.md) for dependencies and installation steps.
The relevant commands, run from the project directory, are:

```sh
python3 install.py theme --dry-run # preview appearance-only installation
python3 install.py theme           # install Graphite without replacing panels
python3 install.py --dry-run       # preview the complete setup
python3 install.py                 # install the complete setup
python3 install.py build-theme     # build build/Graphite-1.0.0.tar.gz
python3 install.py tiling off
python3 install.py tiling on
python3 install.py check
python3 install.py restore         # restore the latest installation backup
```

Build and install `wheel/` first for the complete setup, or use
`--without-wheel`. Restore backups only on the machine where they were made.
Do not copy the whole `~/.config` directory to install another machine.

## Validation

Validation covered package import through KDE's package tools, portable file
rendering, configuration merging, backup restoration, repeated application
launches, both monitor workspace banks, cross-monitor moves and window controls.
New Kitty and Konsole windows were checked after the final controls change.

The desktop was tested on Fedora 44 with Plasma 6.7.5 on Wayland. Arch package
instructions are documented; a clean-machine Arch installation still needs
verification. See [THIRD_PARTY.md](../THIRD_PARTY.md) for source versions and
licenses.
