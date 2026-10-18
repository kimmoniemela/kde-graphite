# Optional installation components

## Workspace wheel shortcut

The repository includes a native KWin effect. Its only bindings are
Super+wheel up → next workspace and Super+wheel down → previous workspace on
the active monitor. The five-workspace range is clamped, not wrapped.

After installing the ordinary theme and shortcuts:

```sh
python3 install.py wheel --dry-run
python3 install.py wheel
```

Run as the desktop user without sudo. The command builds only the local `wheel/`
source, using installed CMake, a C++ compiler, Qt 6 and KF6 development files,
and KWin's installed headers/library. It does not install missing dependencies
or download source. The audited CachyOS system has all required tools already.

The binary goes under `$XDG_DATA_HOME/kde-graphite/wheel/qt6/plugins/` (default
`~/.local/share`). A small script under
`$XDG_CONFIG_HOME/plasma-workspace/env/graphite-wheel.sh` adds just that plugin
root to the KDE session's `QT_PLUGIN_PATH`, preserving any existing value.
The command backs up both files and `kwinrc`, then enables the effect for the
next login. Existing Kröhnkite settings and files remain unchanged.

Log out and back in, then run `python3 install.py check`. No compositor restart
is attempted in the active session. Rebuild after KWin upgrades. The plugin's
factory IID is compiled from the installed KWin headers; KWin rejects a binary
for an incompatible version. An already installed/discoverable plugin can be
explicitly enabled during normal installation with `--with-wheel`.

## Top bars

Normal installation retains existing bars. To explicitly create/rebuild them:

```sh
python3 install.py doctor install --panel --settings settings.local.json
python3 install.py install --panel --settings settings.local.json --dry-run
python3 install.py install --panel --settings settings.local.json
```

This replaces widgets on existing top bars and creates missing bars. Other
panels remain. `--no-panel` remains accepted as a compatibility alias for the
default behavior. Existing custom bars continue working without this option.

## Existing tiling

Normal installation neither installs nor configures Kröhnkite. Its saved state
and bindings remain. To deliberately install/configure the repository's bundled
copy, use `install --with-tiling`; see [tiling](tiling.md).

## Native Global Theme package

```sh
python3 install.py build-theme
```

Import `build/Graphite-1.0.0.tar.gz` with Global Theme → Install from File, or:

```sh
kpackagetool6 --type Plasma/LookAndFeel --install theme/org.kde.graphite.desktop
```

Use `--upgrade` for an existing package. The theme embeds its palette and two
wallpapers and references Breeze components. It installs no tiler, shortcuts,
custom pager or native effect. Leave **Desktop layout** unchecked to retain
panels. Selecting it builds a top bar per display, with the custom pager when
available and KDE's standard pager otherwise.

`python3 install.py theme` additionally backs up touched files and applies
lock-screen, decoration and visual effect preferences. It leaves tiler
preferences and scripts untouched. Wallpaper and preview rendering tools under
`tools/` are optional development tools; installation uses bundled PNG assets.

## Verification

```sh
python3 -m unittest discover -s tests
```

Node enables JavaScript behavior tests; KPackage tools enable isolated native
theme import. Neither is downloaded by the tests. Temporary XDG directories
isolate all test installations from the live desktop.
