# Portability audit

Audited 2026-10-17, starting from commit `f5d57dd`. Scope: installing Graphite on
another user's machine without importing this machine's desktop configuration.
Changes below affect the repository and future installations. The audit did not
reinstall or change the current desktop.

Historical findings below cover the retained installer and appearance features.
Use the current README for installation steps.

## Findings and changes

| Priority | Finding | Resolution |
| --- | --- | --- |
| High | `restore --dry-run` restored files. | Dry runs return before any mutation. Regression tests cover dry runs. |
| High | Full install and restore unloaded/restarted live KWin scripts, despite the earlier Qt garbage-collector crash. | Full install and restore defer script changes until the next login. Appearance no longer explicitly starts all scripts. |
| High | Missing applications or QML modules could leave a partly installed desktop. | `doctor theme` / `doctor install` collect missing commands, services, Breeze assets, QML modules and widgets before installation. Full install checks connected output names before writing files. |
| Medium | The default command replaced the desktop layout and shortcuts. | The default command now applies appearance only. The full workflow requires the explicit `install` command. |
| Medium | The complete setup required compiling a native plugin and installing it as root. | The wheel effect is opt-in with `--with-wheel`; the ordinary full install needs runtime packages only. `check` reads the installed wheel setting. |
| Medium | Defaults required Kitty, Nautilus, GNOME Text Editor, GNOME Calculator and btop on a fresh KDE machine. | New defaults use Konsole, Dolphin, KWrite, KCalc, Plasma System Monitor and Firefox. Application overrides remain supported; this machine's launchers were not changed. |
| Medium | The full install retained any existing decoration plugin, even when applying Breeze preferences. | Explicitly select the Breeze decoration in the full profile too. |
| Medium | A stale monitor override was silently accepted; a third screen could display duplicate workspace labels. | Reject disconnected names and full setups with more than two screens before writing. Appearance remains independent of monitor count. |
| Medium | A failed install could leave the latest-backup pointer referring to an older operation. | Write the pointer after the new backup is complete, before desktop mutations. |
| Medium | The former panel mode assumed a systemd Plasma unit. | Current desktop operations require a new login and do not restart plasmashell. |
| Low | Retaining panels still cleared conflicting tray/notification shortcuts. | Leave those bindings alone when retaining panels. |
| Low | Installation, C++ build instructions and incident notes were mixed together. | Keep the primary README focused on appearance and full installation. Move optional packaging/build details to `install-options.md`; record the audit here. |

The theme and full setup still use selected KDE configuration merges, XDG
paths and local backups. No display modes, desktop UUIDs, widget IDs, usernames
or source-machine paths are embedded in the portable defaults. Hyprland,
Sway, i3, GNOME, GTK and shell files are excluded from installation. KDE's GTK
synchronization is disabled before changing colors.

## Verification

- 23 automated tests pass, including an isolated native KPackage import.
- A full install into empty temporary XDG directories retains unrelated KDE
  settings and protected desktop files. Restore recovers the original files.
- Missing-dependency preflight exits before creating destination files.
- Both appearance and full dry runs render without applying desktop changes.
- The live read-only appearance check passes on Fedora 44 / Plasma 6.7.5.
- The live full check passes with this machine's application overrides. With
  portable defaults, it reports the missing KCalc command as expected.
- The native theme archive builds successfully. Its package import is tested
  with a temporary HOME and disconnected session bus.

Package instructions were checked against local Fedora package ownership and
primary package metadata: [Arch PySide6](https://archlinux.org/packages/extra/x86_64/pyside6/),
[Arch KCalc](https://archlinux.org/packages/extra/x86_64/kcalc/),
[Fedora PySide6](https://packages.fedoraproject.org/pkgs/python-pyside6/python3-pyside6/).
The panel API follows [KDE's scripting documentation](https://develop.kde.org/docs/plasma/scripting/api/).

## Remaining validation and limits

- A fresh-machine graphical login has not been tested. Temporary-directory tests
  verify files and commands, not KWin startup, shortcut ownership or actual
  widgets in a second desktop session. A clean Plasma 6.7+ VM is the next test.
- Appearance installation has only been exercised on Plasma 6.7.5. Other Plasma
  6 versions are eligible for the appearance profile but remain unverified.
- The full setup supports one or two monitors. Output roles are selected at
  installation; docking, unplugging and changing the primary screen need a
  separate hot-plug test. Clear overrides and reinstall to resolve new roles.
- Restore recovers backed-up files and requires an immediate logout/login to
  replace running scripts and shortcut handlers. It is not an atomic rollback;
  later edits to backed-up files are replaced by their backed-up contents.
- The repository is private. A new machine needs GitHub access or a downloaded
  source archive. The generated Global Theme archive contains appearance assets;
  it is not an installer for the full desktop workflow.
- The optional wheel effect remains coupled to KWin's native plugin ABI and must
  be rebuilt on each machine and after KWin upgrades.
