# Components and dependencies

A minimal KDE Plasma theming and keyboard-workflow project.

| Remaining component | Purpose | Why custom code remains |
| --- | --- | --- |
| `install.py`, `theme.py`, `doctor.py` | Selected configuration, preflight, packaging and backups/restore | Reproducible installation/recovery is outside native theme-package scope; these are command-line tools, not resident services |
| Native Graphite LookAndFeel package, palette and two wallpaper packages | Appearance using Breeze, standard lock screen and image wallpaper | Theme assets are the project's appearance |
| `templates/workspaces.js` → `kde-hypr-bridge` | Fixed monitor-number banks, window sends, clamped navigation, empty desktop and scratchpad | Stock actions do not combine these semantics; no geometry enforcement |
| `scripts/workspace-keys.py` | Finnish/US shifted number aliases | Layout-specific symbols overlap; watches KDE signals rather than polling |
| `scripts/launch-app.py`, `applications.py` | Resolve current KDE defaults and execute them | Native fixed command entries cannot implement all dynamic preferences; explicit ordinary overrides bypass Python |
| Generated `org.kde.graphite.applications.desktop` | Native KGlobalAccel desktop actions | Declarative integration data, not a custom launcher process |
| Generated KDE-only autostart entry | Start the existing layout helper | Native XDG session integration replaces QML process launching |
| `templates/wallpaper.js` | Apply the two static images to desktop containments | Per-screen alternation and scoped restore need a small Plasma script; no panel operations |
| `assets/xkb/symbols/graphite` | Optional additional AltGr Super key | Avoid changing the original right Super key with a stock swap |
| `wheel/` | Optional native Super+wheel axis shortcuts | Global modifier+wheel scope; unchanged implementation |
| `sddm/graphite/`, `sddm/install.py` | Optional system login appearance | SDDM is separate from the desktop theme and needs administrator access |

Native Plasma now supplies all panels and Pager, application activation, KRunner,
screenshots, clipboard, session/lock controls, ordinary KWin actions and
focused-monitor numbered desktop selection. The Global Theme contains no layout
script. The old custom applet is not shipped; installed copies are not deleted
from user panels. Native Pager shares desktop labels between screens, so the
secondary keyboard bank's 6–10 labels are not displayed there.

## Runtime and build inventory

| Scope | Dependencies and overhead |
| --- | --- |
| Appearance installer | Python standard library, GDBus, Fontconfig, Plasma 6, installed Breeze assets |
| Workflow installer | Above plus kscreen-doctor and PySide6 QtGui for shortcut encoding; no QML module checks |
| Workspace runtime | One in-process KWin JavaScript script |
| Keyboard-layout runtime | One KDE-only, event-driven Python process using PySide6 QtCore/QtGui/QtDBus, libxkbcommon and GDBus |
| App activation | Existing KDE KGlobalAccel/KIO; short-lived default resolver uses kreadconfig6, kstart and optionally xdg-mime; no Python process retained after `exec` |
| Optional wheel build | CMake, C++20 compiler, installed KWin headers/library, Qt 6 Core/Gui/Widgets/Quick/DBus, KF6 CoreAddons and Config; headers require these dependencies |
| Optional wheel runtime | One native KWin effect, local KWin ABI and a Plasma-session Qt plugin path |
| Optional SDDM | Installed Qt 6 greeter and Breeze/Plasma QML modules, including private imports checked by its installer |
| Asset development | `tools/` renderers use PySide6 QtGui/QtSvg; never installed into the desktop runtime |
| Tests | Python unittest; Node for JavaScript; KPackage for native import; optional C++ native shortcut host with installed Qt/KGlobalAccelD development files and dbus-run-session |

Removed dependencies include the custom applet's TaskManager QML integration
and the launcher/widget Plasma5Support executable engines. The layout helper's
Python/Qt/XKB dependencies remain necessary. No persistent Python process was
eliminated; no memory reduction is claimed. Repository/package complexity and
resident QML were reduced without adding a daemon.

`hypr` in the remaining script/effect IDs is historical. Those components run
inside KWin and do not load or modify Hyprland. See the
[architecture review](architecture.md) for native-equivalence decisions,
configuration boundaries, upgrade cleanup and compatibility risks.
