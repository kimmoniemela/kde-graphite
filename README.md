# Graphite

A KDE Plasma Global Theme: charcoal surfaces, muted sage, monospace type and
quiet Breeze decorations. An optional full setup adds top bars, keyboard
shortcuts, five independent workspaces per monitor and Kröhnkite tiling.

Graphite includes two static charcoal contour wallpapers. Appearance installation
applies them across connected displays and adds them to KDE's wallpaper picker.
The original SVGs and optional rendering tool are included in the repository;
installation uses the bundled 4K PNGs and needs no rendering tools.

![Graphite preview](theme/org.kde.graphite.desktop/contents/previews/preview.png)

Appearance requires Plasma 6. The full setup requires Plasma 6.7+ on Wayland,
with one or two monitors. Tested on Fedora 44 / Plasma 6.7.5. Other Plasma 6
versions and a clean Arch installation still need testing.

## Get the source

Use an account with access to the private repository. GitHub SSH authentication
must already be configured, or download the repository ZIP from GitHub.

```sh
git clone git@github.com:kimmoniemela/kde-graphite.git
cd kde-graphite
```

## Install the appearance

Start with a working KDE desktop with Breeze installed. Requires Python 3,
Fontconfig, GDBus, KDE configuration tools and KPackage tools. No compiler,
PySide6, wheel plugin or additional applications are required.

Run as the desktop user, inside KDE, without sudo:

```sh
python3 install.py doctor theme
python3 install.py theme --dry-run
python3 install.py theme
```

Running `python3 install.py` also installs appearance only. Graphite is selected
and appears in System Settings → Colors & Themes → Global Theme. Existing
panels, shortcuts, workspaces and tiling remain. Log out and back in to load
all fonts and the window-controls helper. The font falls back from FiraCode
Nerd Font Mono to Fira Code, then the system monospace font.

## Install the full desktop setup

Install the additional runtime dependencies. On Arch:

```sh
sudo pacman -S --needed pyside6 kscreen plasma5support wl-clipboard \
  konsole dolphin kwrite kcalc firefox plasma-systemmonitor \
  spectacle kdeplasma-addons ttf-fira-code
```

On Fedora KDE:

```sh
sudo dnf install python3-pyside6 kscreen plasma5support wl-clipboard \
  konsole dolphin kwrite kcalc firefox plasma-systemmonitor \
  spectacle kdeplasma-addons fira-code-fonts
```

KRunner and System Settings must be available. Then, from the target user's
Plasma Wayland session:

```sh
python3 install.py doctor install
python3 install.py install --dry-run
python3 install.py install
```

Log out and back into KDE, then run:

```sh
python3 install.py check
```

The full install replaces the contents of existing top bars or creates a top
bar per connected monitor. Other panels remain. Use `--no-panel` to retain the
panel layout. Script changes activate at the next login; the installer does
not unload and reload live KWin scripts.

The primary screen gets labels 1–5 and the secondary 6–10. Super+1–5 / Super+6–0
select those destinations; add Shift to move a window. Output names are detected
on each machine. See [shortcuts](docs/shortcuts.md).
Occupied workspaces have sage numbers and a small underline. The current
workspace is filled; empty workspace numbers are dimmed. Each bar tracks its
own monitor, including minimized windows.

## Local settings

Override only what differs on the destination machine:

```sh
cp settings.json settings.local.json
# Edit settings.local.json, then use it for both commands:
python3 install.py doctor install --settings settings.local.json
python3 install.py install --settings settings.local.json
```

Applications are argument arrays. Defaults use KDE applications and Firefox.
To use Kitty, set `"Terminal": ["kitty"]`. Empty output names follow KDE's
priority at installation. Clear old monitor names before moving to another
machine. The installed launchers keep using the destination machine's commands.

## Tiling

Kröhnkite is the only automatic tiler bundled with Graphite. The full installer
installs and enables a locally patched copy; appearance-only installation and
the native Global Theme package do not install it.

For ordinary floating window management:

```sh
python3 install.py tiling off
```

To resume automatic arrangement:

```sh
python3 install.py tiling on
```

These commands save the mode without unloading the script. Allow roughly half
a second for it to apply. Windows keep their last geometry when suspended;
enabling tiling arranges them again. All normal windows retain minimize,
maximize and close controls.

To disable the script itself, uncheck **Kröhnkite** in System Settings → Window
Management → KWin Scripts and apply. To use the CLI again, enable the script
there first. Workspace and application shortcuts remain independent; tiling
shortcuts are inactive while tiling is off. Super+Alt+Space toggles floating for
one window while tiling is active. See [tiling](docs/tiling.md) for configuration
and troubleshooting.

## Restore

```sh
python3 install.py restore --dry-run
python3 install.py restore
```

Touched files are backed up under `~/.local/state/kde-graphite/backups/`.
Restore uses the latest backup; pass a backup path to select another. Log out
and back in immediately after restoring. Backups are local to their machine.
XDG directory overrides are supported. Hyprland, Sway, i3, GNOME, GTK and shell
configuration are not copied or edited; KDE's GTK synchronization is disabled
before applying colors.

See [optional wheel shortcuts and theme packaging](docs/install-options.md),
[portability audit](docs/portability-audit.md), [setup history](docs/setup-history.md)
and [component list](docs/components.md).
