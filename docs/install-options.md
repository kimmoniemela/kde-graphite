# Installation and maintenance

Run desktop commands as the normal user in KDE. Appearance supports Plasma 6;
the full keyboard workflow requires Plasma 6.7+ on Wayland and one/two monitors.

| Command/option | Behavior |
| --- | --- |
| `theme` (default) | Native Graphite appearance and wallpapers; preserve panels/workflow |
| `install` | Appearance, native shortcuts and essential workspace helpers |
| `--settings FILE` | Overrides for theme/install and doctor; dynamic defaults use `["@default"]`, disabled applications use `[]` |
| `doctor theme` / `doctor install` | Read-only runtime preflight |
| `check` | Verify selected theme, managed script, five desktops, shortcut registrations and layout-helper service after login |
| `--with-wheel` | On install, enable an already discoverable wheel effect; on doctor/check, require it |
| `--without-wheel` | On check, skip effect verification; normal installation preserves its existing state |
| `wheel` | Build/install only the optional local native wheel effect |
| `build-theme [FILE]` | Write a standalone Global Theme archive |
| `restore [BACKUP]` | Restore the latest or specified local backup |
| `--dry-run` | Preview theme/install/wheel/build-theme/restore/check without changing desktop state |

There are no panel creation flags. Plasma's own panel editor and Pager remain
under user control. Configure the Pager on each display to show that screen's
windows if desired. Desktop names are shared, so both Pagers use the same labels;
Graphite's primary/secondary number-key banks remain 1–5 and 6–0.
System tray and notification widget shortcuts remain whatever the user configured.

## Wheel (mwheelsetup)

After installing the workspace workflow:

```sh
python3 install.py wheel --dry-run
python3 install.py wheel
```

This preserves the existing `wheel/` implementation: Super+wheel up selects the
next workspace, down selects the previous, on the active monitor, clamping at
1 and 5. No Ctrl/Shift wheel combinations are claimed.

The command builds local source with installed CMake, C++, Qt/KF6 development
files and KWin headers/library. No source or dependencies are downloaded.
The binary goes under `$XDG_DATA_HOME/kde-graphite/wheel/qt6/plugins/`. The
Plasma-only `$XDG_CONFIG_HOME/plasma-workspace/env/graphite-wheel.sh` adds this
root to `QT_PLUGIN_PATH` and retains existing entries. That variable is inherited
by Plasma applications; a narrower portable mechanism has not been verified.
The optional effect is independent of appearance installation.

The plugin, environment entry and enable setting are backed up. Identical files
are not replaced; changed libraries are replaced atomically rather than truncated
while mapped. Log out/in to activate updates and run `check`. KWin checks the
compiled factory IID; rebuild on each machine and after KWin upgrades. No
compositor restart, sudo or system package operation is used.

## Standalone Global Theme

```sh
python3 install.py build-theme
kpackagetool6 --type Plasma/LookAndFeel --install build/Graphite-1.0.0.tar.gz
```

Use `--upgrade` for an existing package. Import through Global Theme → Install
from File if preferred. The archive embeds its palette, font/Breeze defaults,
previews and both wallpaper images. It installs no workspace helpers, effects,
shortcuts or panel layout. The regular `theme` command additionally installs
named wallpaper packages, applies alternating images automatically and saves
recovery state. Native archive import alone does not perform that per-screen
wallpaper application or lock-screen configuration.

## Upgrades and removal

Repeat the same command/settings file after updating the checkout. Old local
`panel_height` preferences are ignored for compatibility. Upgrades disable only
Graphite's former launcher scripts when present, retire their known files and
shortcut actions, remove retired Graphite utilities that still exist, and remove
the old theme layout scripts. They never touch third-party KWin scripts.

Installed Graphite widgets stay intact when a user panel references them. Use
Plasma's editor to replace one with Pager before removing its installed package.
There is no automatic panel migration and no unrequested visual redesign.

Use `restore --dry-run` and `restore` to undo the latest operation, or pass an
explicit backup directory. Repeated restore follows prior operations. Full panel
layouts are never restored, including when reading an older backup. Desktop
wallpapers are restored through Plasma. New KConfig backups recover selected
entries and actual conflicting shortcut owners, preserving later unrelated
preferences. Owned payload files are recovered whole. Older backups lack complete
ownership metadata: known KWin/shortcut entries are restored conservatively, and
unrecorded legacy native bindings may need manual recovery. Other legacy files
still replace later edits.
Log out/in immediately after recovery. There is no blanket uninstall/reset;
restore the relevant installation backup to recover previous selected settings.
Use KDE's package tools to remove an unselected standalone theme if desired.
SDDM has its own [installation and restoration](../sddm/README.md).

## Verification

```sh
python3 -m unittest discover -s tests -v
python3 install.py build-theme
```

Node enables the workspace/wallpaper scripting tests; KPackage tools enable
isolated import. No tests download packages. All file-install tests use temporary
XDG directories.

For the optional real KGlobalAccel/KIO execution test, with its development files
already installed:

```sh
cmake -S tests/native -B build/native-shortcuts
cmake --build build/native-shortcuts
GRAPHITE_NATIVE_SHORTCUT_HOST="$PWD/build/native-shortcuts/shortcut-host" python3 -m unittest discover -s tests -p test_native_shortcuts.py -v
```

The host uses private KDE API **only in tests**, creates its own D-Bus session,
and launches harmless recorder programs under temporary XDG homes. It checks
repeated activation, changed default preferences, quoted/multiline arguments,
unusual executable names and native API registration. It does not press real
keys, use the live registry or claim graphical acceptance.
