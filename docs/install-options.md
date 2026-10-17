# Optional installation components

## Workspace wheel shortcuts

The default full install works without a compiler or root access. Super+wheel
requires a native effect compiled against the destination machine's KWin.

Build dependencies on Arch:

```sh
sudo pacman -S --needed base-devel cmake extra-cmake-modules kwin
```

On Fedora:

```sh
sudo dnf install gcc-c++ cmake extra-cmake-modules kwin-devel \
  qt6-qtdeclarative-devel kf6-kcoreaddons-devel libepoxy-devel libdrm-devel
```

Build from the repository root:

```sh
cmake -S wheel -B build/wheel -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr
cmake --build build/wheel --parallel
sudo cmake --install build/wheel
python3 install.py doctor install --with-wheel
python3 install.py install --with-wheel
```

Log out and back in, then run `python3 install.py check`. The check reads the
installed wheel setting; repeating the flag is unnecessary. Rebuild after KWin
upgrades. Restoring a backup retains the system-installed binary, but restores
its earlier enabled/disabled setting. `--without-wheel` remains accepted for
older installation commands.

## Native Global Theme package

```sh
python3 install.py build-theme
```

Import `build/Graphite-1.0.0.tar.gz` with Global Theme → Install from File, or
install the source package directly:

```sh
kpackagetool6 --type Plasma/LookAndFeel --install theme/org.kde.graphite.desktop
```

For an existing package, use `--upgrade` instead of `--install`. The native
package embeds its colors and references standard Breeze components. It does
not install Kröhnkite, shortcuts, the custom pager, or the wheel effect.

Leave **Desktop layout** unchecked to keep existing panels. Selecting it builds
one top bar per display. It uses the custom numbered pager when the full setup
is installed and KDE's standard pager otherwise.

`python3 install.py theme` is the supported route for the complete Graphite
appearance: it also applies lock-screen, quiet-decoration and effect settings,
backs up touched files and disables KDE's GTK synchronization before applying
colors. Native package import alone does not perform those extra steps. The
preview images are illustrations.

## Verification

```sh
python3 -m unittest discover -s tests
```

Node is needed for the JavaScript behavior tests. KPackage tools enable the
isolated native theme-import test. Neither is downloaded by the test suite.
The tests use temporary XDG directories and do not reinstall the live desktop.
