# Arch / CachyOS audit — 18 October 2026

Scope: this project's theme, top bars, workspace/application shortcuts and the
requested Super+wheel binding. Preserve independent KWin scripts. No
package-manager installation, removal or update is part of this audit.

## Environment and findings

| Item | Evidence and result |
| --- | --- |
| Distribution | CachyOS, Arch based; local `/etc/os-release`. |
| Desktop | Plasma and KWin 6.8.0, Wayland; Qt and PySide6 6.12.0. |
| Qt tools | Arch installs `qtpaths` at `/usr/lib/qt6/bin/qtpaths`. Doctor now accepts this path as well as the distribution-suffixed commands. |
| Normal installer | Installs theme and shortcuts, retaining existing bars and independent KWin scripts. Replacing bars requires `--panel`. |
| Appearance installer | Needs no KWin scripts and leaves independent scripts and their preferences alone. |
| Native shortcuts | Minimal installation preserves unrelated navigation bindings and third-party script bindings. Native desktop-number actions are cleared only to avoid competing with Graphite's monitor-aware number keys. |
| Shortcut conflicts | Previously clearing a conflicting action removed all of its alternative shortcuts. Only the conflicting key is now released; other bindings remain. |
| Runtime dependencies | Existing application commands come from local settings. The default `kcalc` is absent; the local override already uses installed `gnome-calculator`. Missing commands cause preflight failure, never automatic installation. |
| Panels | Existing custom bars are retained. Widget installation and panel dependency checks happen only with `--panel`. |
| Wheel | Repository source already mapped Super+up to next and Super+down to previous, but no binary was installed on this machine. Added an explicit user-only build/install command, without downloads or sudo. Only those two wheel combinations are bound. |
| Native build | Removed unnecessary reliance on the full KWin CMake dependency graph. The effect compiles against installed KWin headers/library and Qt/KF libraries. The build passes with the existing packages, without ECM or Vulkan headers. |
| Binary upgrades | Replace the wheel binary atomically, avoiding overwriting a library currently mapped by KWin. New versions activate after login. KWin's versioned factory IID protects against incompatible plugins. |
| Live session safety | No compositor restart or live KWin script unload/reload. A fresh login is required after script/plugin updates. |

The installer contains no package-manager or download operation. Its subprocesses
invoke KDE tools and explicitly selected application commands. The wheel command
runs the checked-in CMake project with existing tools. Baloo, crash reporting,
portals, notification daemons and system packages are outside Graphite's installer.
The missing AppImage metadata library observed during desktop diagnosis is not a
Graphite dependency and is not required for theming or shortcuts.

## Verification and limits

All 28 automated tests pass. They cover isolated installation/restore, dry runs, Arch Qt discovery,
third-party script/panel preservation, shifted Finnish/US number keys, mocked monitor-aware
workspace behavior and native theme-package import. They do not install packages
or modify the live desktop. The native wheel effect builds on this machine and
its Qt plugin metadata is inspected before delivery.

The live `doctor install --settings settings.local.json` and post-install
`check --without-wheel` pass. Before/after checks confirm that the complete
third-party script file contents, settings, enabled state and shortcuts are unchanged;
the panel configuration file is also byte-for-byte unchanged. The user plugin
metadata reports `org.kde.kwin.EffectPluginFactory6.8.0`, matching installed KWin.
The plugin path is loaded at the next KDE login; interactive
wheel delivery needs that login and a physical mouse check. A fresh Arch VM,
monitor hot-plugging and every shortcut/application interaction are not covered.
No test suite can guarantee the absence of all desktop or upstream bugs.

KWin discovers native effects through Qt plugin paths and checks their factory
IID before instantiation; see the [KWin effect loader source](https://github.com/KDE/kwin/blob/Plasma/6.8/src/effect/effectloader.cpp).
KDE's standard [window mouse bindings](https://docs.kde.org/trunk_kf6/en/kwin/kcontrol/windowbehaviour/index.html)
move a window between desktops; the project effect provides the requested global
workspace switch instead.
