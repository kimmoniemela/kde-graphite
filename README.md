# Graphite

A KDE Plasma Global Theme and desktop configuration. Charcoal surfaces, muted
sage accents, monospace type and an opaque top bar. The complete setup adds
five independent workspaces per monitor, keyboard shortcuts and optional
Kröhnkite tiling.

![Graphite preview](theme/org.kde.graphite.desktop/contents/previews/preview.png)

Tested on Fedora 44, Plasma 6.7.5, Wayland. Requires Plasma 6.7 or later in the
6.x series. Arch package instructions are provided; Arch has not been tested.

## Global Theme

From this repository, inside a KDE session:

```sh
python3 install.py theme --dry-run
python3 install.py theme
```

Graphite appears in System Settings → Colors & Themes → Global Theme. This
installs and selects its appearance, including the matching lock-screen settings.
Existing panels, workspaces, shortcuts and tiling stay in place. Requires
Python 3, Fontconfig, Breeze and the standard Plasma tools. Fira Code
is the fallback when FiraCode Nerd Font Mono is unavailable.

When applying Graphite from System Settings, leave **Desktop layout** unchecked
to retain your panels. Select it to create a top bar on each connected display.
The layout uses Graphite's numbered pager when the full setup is installed;
otherwise it uses KDE's standard pager.

For a package that can be imported with **Install from File**:

```sh
python3 install.py build-theme
```

Output: `build/Graphite-1.0.0.tar.gz`. The package embeds its palette and uses
Breeze components. The repository's `theme/org.kde.graphite.desktop/` directory
is also directly installable with `kpackagetool6 --type Plasma/LookAndFeel
--install /path/to/theme/org.kde.graphite.desktop`. A package-only import supplies
KDE's supported theme components; the `theme` command also applies the quiet
Breeze, effects and lock-screen preferences. Preview images are illustrations.

The full setup below includes the Global Theme. Tiling, workspace routing and
shortcut plugins belong to the installer.

## Dependencies

Start with a working Plasma Wayland session. On Arch:

```sh
sudo pacman -S --needed base-devel cmake extra-cmake-modules kwin pyside6 \
  kscreen plasma5support kitty nautilus firefox gnome-text-editor gnome-calculator \
  btop wl-clipboard ttf-fira-code
```

On Fedora:

```sh
sudo dnf install gcc-c++ cmake extra-cmake-modules kwin-devel \
  qt6-qtdeclarative-devel kf6-kcoreaddons-devel libepoxy-devel libdrm-devel \
  python3-pyside6 kscreen plasma5support kitty nautilus firefox gnome-text-editor \
  gnome-calculator btop wl-clipboard fira-code-fonts
```

KRunner, Spectacle, System Settings and the standard Plasma widgets must be
installed. The configured font is FiraCode Nerd Font Mono; the installer falls
back to Fira Code or the system monospace font.

## Install

Clone with an account that has access to this private repository:

```sh
git clone git@github.com:kimmoniemela/kde-graphite.git
cd kde-graphite
```

Build the wheel shortcut effect against the destination machine's KWin:

```sh
cmake -S wheel -B build/wheel -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr
cmake --build build/wheel --parallel
sudo cmake --install build/wheel
```

From the target user's KDE session, without sudo:

```sh
python3 install.py --dry-run
python3 install.py
```

Log out and back into KDE. Then check:

```sh
python3 install.py check
```

The installer merges selected KDE settings and configures one top bar per
connected monitor, labelled 1–5 on the primary and 6–10 on the secondary.
Existing top bars are reused; other panels remain.
It does not copy display modes, desktop UUIDs or widget IDs from another machine.
Hyprland, Sway, GNOME, GTK and shell configuration
are not installed or modified. KDE's GTK synchronization module is disabled
before applying the palette.

Rebuild the wheel effect after a KWin upgrade. To omit it, skip the build and
pass `--without-wheel` to install and check. Use `--no-panel` to retain the panel.

## Local settings

Copy `settings.json` to `settings.local.json`, edit it, and install with:

```sh
python3 install.py --settings settings.local.json
```

Application commands are argument arrays. `primary_output` and
`secondary_output` are optional output names. Empty values follow KDE's display
priority at installation. On a single monitor, both number-key groups select
that monitor.

The bars show 1–5 on the primary monitor and 6–10 on the secondary.
Super+1–5 and Super+6–0 select those destinations; add Shift to send a window.
Super+Ctrl+1–5 selects a workspace on the focused monitor. See [shortcuts](docs/shortcuts.md).

## Tiling

```sh
python3 install.py tiling off
python3 install.py tiling on
```

Alternatively, toggle Krohnkite in System Settings → Window Management → KWin
Scripts. Super+Alt+Space floats one window. Colors, launch shortcuts and
workspaces do not depend on tiling.

## Restore

Every installation backs up the files it touches under
`~/.local/state/kde-graphite/backups/` (or `$XDG_STATE_HOME`).

```sh
python3 install.py restore                 # latest backup
python3 install.py restore /path/to/backup # selected backup
```

Log out and back into KDE after restoring. The system-installed wheel plugin
is left in place but unloaded. Backups belong to the machine where they were
created; do not use them to install another machine.

## Sources and validation

Kröhnkite is pinned and included as source. See [THIRD_PARTY.md](THIRD_PARTY.md)
for its version, local patches and licenses. No theme-store downloads are
required by the installer.

```sh
python3 -m unittest discover -s tests
```

The existing desktop was tested for repeated terminal launches, launcher
reloads, tiling, floating, scratchpad and independent workspace switching. The
portable installer has been tested for rendering, config merging and backup
restoration; a clean-machine installation still needs testing.
