# Development

[README](../README.md) · [Architecture](architecture.md) · [Configuration](configuration.md)

Keep changes focused on Graphite's appearance and keyboard workflow. Use native
Plasma features where equivalent; retain custom code only for a demonstrated
workflow gap. Installation must preserve unrelated preferences, user panels and
independent KWin scripts. Do not introduce a new desktop, launcher framework or
background service to solve a native KDE task.

## Repository map

| Path | Responsibility |
| --- | --- |
| [install.py](../install.py), [doctor.py](../doctor.py) | CLI, workflow installation, checks, backups/recovery and wheel orchestration |
| [theme.py](../theme.py) | Shared appearance configuration, native assets and archive generation |
| [applications.py](../applications.py) | Dynamic defaults and application availability |
| [settings.json](../settings.json), [config.json](../config.json), [shortcuts.json](../shortcuts.json) | Personal-setting defaults, appearance fragments and native/application keys |
| [templates/](../templates), [scripts/](../scripts) | Generated KWin/wallpaper scripts and installed Python helpers |
| [theme/](../theme), [assets/](../assets) | Native Global Theme, wallpaper/previews, canonical palette and optional XKB symbols |
| [wheel/](../wheel) | Optional native axis-shortcut effect |
| [sddm/](../sddm) | Separate login theme and system installer |
| [tests/](../tests), [tools/](../tools) | Regression/integration tests and offline asset renderers |
| [.github/workflows/check.yml](../.github/workflows/check.yml) | Portable test and archive CI |

The canonical palette is in `assets/color-schemes/TerminalGraphite.colors`;
`theme.py` includes it when generating the package. Workspace keys originate in
`workspace_shortcuts()` in `install.py`; edit that table rather than adding
another shortcut registry. Inspect generated payloads as well as source changes.

## Local checks

Use Python 3.10+ from the repository root. No Python packaging/install step is
required. The standard-library tests run without a live desktop; optional tools
enable additional checks:

- Node runs the workspace/wallpaper JavaScript harnesses.
- PySide6 enables shortcut encoding and relevant Qt checks.
- `xkbcli` compiles Finnish/US keymaps for the AltGr regression.
- `kpackagetool6` enables isolated native theme import.

```sh
python3 -m unittest discover -s tests -v
python3 install.py build-theme
python3 -m compileall -q install.py theme.py doctor.py applications.py scripts sddm/install.py tests

git diff --check
```

Read skipped tests in the output; an ordinary portable run does not enable the
optional native shortcut test. CI tests Python 3.10 and 3.14 with Node and builds
the archive. It does not establish graphical compatibility on its runner OS.
Asset renderers use PySide6 QtGui; wallpaper rendering also uses QtSvg.
File-install tests use temporary directories and mocked desktop APIs; KPackage
import uses an isolated data directory and disconnected session bus.

### Native shortcut integration test

With installed Qt 6, KF6 GlobalAccel and KGlobalAccelD development files,
`dbus-run-session`, PySide6 and the normal runtime commands available:

```sh
cmake -S tests/native -B build/native-shortcuts
cmake --build build/native-shortcuts
GRAPHITE_NATIVE_SHORTCUT_HOST="$PWD/build/native-shortcuts/shortcut-host" python3 -m unittest discover -s tests -p test_native_shortcuts.py -v
```

The small C++ host uses private KDE API **only in tests**. It starts a private
D-Bus session and temporary HOME/XDG directories, then executes harmless recorder
programs through real KGlobalAccel/KIO. It checks repeat activation, changed KDE
defaults, quoting/multiline arguments, unusual executable names and API
registration. It does not access the user's live shortcut registry or press keys.

### Wheel build check

Build without installing or changing the session:

```sh
cmake -S wheel -B build/wheel -DCMAKE_BUILD_TYPE=Release
cmake --build build/wheel --parallel 2
```

Use the [README prerequisites](../README.md#requirements). Build against the
installed KWin ABI. A successful build is not proof of effect loading or wheel
input delivery. No system installation is necessary for this check.

## Standalone Global Theme archive

`python3 install.py build-theme` writes `build/Graphite-1.0.0.tar.gz`. An explicit
destination is also supported. Build and import with KDE's native package tool:

```sh
python3 install.py build-theme build/Graphite-local.tar.gz
kpackagetool6 --type Plasma/LookAndFeel --install build/Graphite-local.tar.gz
```

The import command installs into the current user's KDE data directory; use a
test account for manual development. Use `--upgrade` instead of `--install` when
the package already exists. The automated test performs an isolated import.

The archive contains palette, font/Breeze defaults, previews and both images.
Its default font is Fira Code; `--settings` is not accepted by `build-theme`.
It has no panel layout, workflow helpers, shortcuts or native effect. Native
import alone does not perform the regular installer's alternating wallpaper
application, lock-screen configuration or backup procedure.

## CLI reference

Installation examples live in the [README](../README.md#installation); recovery
and verification behavior are in [Troubleshooting](troubleshooting.md).

| Command/option | Meaning |
| --- | --- |
| `theme` or no command | Apply appearance only |
| `install` | Appearance, shortcuts and workspace workflow |
| `wheel` | Build/install the optional local effect; requires the workflow |
| `build-theme [FILE]` | Build a native archive, optionally at FILE |
| `doctor [theme\|install]` | Read-only prerequisites; omitted profile means theme |
| `check` | Inspect installed state after login |
| `restore [BACKUP]` | Restore latest or selected backup |
| `--settings FILE` | Local preferences for theme/install/doctor |
| `--dry-run` | Preview mutation commands and check; doctor remains read-only |
| `--with-wheel` | Enable an already discoverable effect on install; require it for doctor install/check |
| `--without-wheel` | Skip wheel verification on check; installation leaves existing state intact |

Wheel verification flags apply only to install, doctor install and check. The
SDDM CLI is separate; see its [guide](../sddm/README.md). Use
`python3 install.py --help` and `python3 sddm/install.py --help` to inspect parsers.

## Validation scope

The architecture cleanup was checked with portable regressions, an isolated real
native shortcut test, native KPackage import and a local wheel build. Those tests
cover single/dual-monitor routing models, Finnish/US aliases, scratchpad state,
repeated installation, failure rollback, selected-key recovery and preservation
of panels/third-party configuration. They do not establish graphical startup,
every application interaction, physical mouse input, hot-plugging, SDDM password
authentication or crash stability.

Historical local checks used Fedora 44 / Plasma 6.7.5 and CachyOS / Plasma 6.8.0.
These were earlier revisions, not clean-machine graphical validation of the
current architecture. Version gates are implementation requirements, not a
claim that all eligible versions/distributions have been tested. Appearance
accepts KWin 6.x; full workflow requires 6.7+ Wayland. X11 remains unverified.

For a graphical acceptance pass, use a fresh Plasma account/VM and record the
commit, distribution, KWin/Qt versions, session type and actual results. Exercise:

1. Both installation profiles, appearance, native panels and unrelated settings.
2. Application defaults/overrides, optional missing apps and conflict handling.
3. Single/dual-monitor number banks, independent selection, window sends, screen
   focus, relative limits, empty desktop and scratchpad show/hide state.
4. Finnish/US layout changes, shifted number keys and optional AltGr mapping.
5. Wheel loading/input after login and after rebuilding for a KWin update.
6. Repeated installation, restore, new login and monitor disconnect/reconnect.
7. Optional SDDM preview, selection and real authentication/recovery separately.

Record build, registration and graphical evidence separately. Do not report
untested paths as passing or infer a crash fix from the absence of warnings.

## Contributing

Read [AGENTS.md](../AGENTS.md) and the affected subsystem before editing. Keep
patches focused, preserve installation safety, add meaningful regression coverage
for behavior changes, and update the corresponding guide when a command, setting
or key changes. Inspect the full diff and run checks appropriate to the patch.
The project workflow requires completed changes to be committed and pushed.

When reporting a problem or proposing a change, include a reproducible trigger
and the environment details listed in [Troubleshooting](troubleshooting.md#reporting-a-problem).
Retain upstream notices in derived files and consult [THIRD_PARTY.md](../THIRD_PARTY.md)
before changing licensed assets. Generated archives and local preferences stay
out of Git; image previews must identify whether they are illustrations or captures.
