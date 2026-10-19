# Architecture

[README](../README.md) · [Configuration](configuration.md) · [Development](development.md)

KDE Graphite is a minimal KDE Plasma theming and keyboard-workflow project.
Plasma owns the desktop, KWin owns window management, and KGlobalAccel owns the
shortcut registry. Graphite installs appearance assets and the small extensions
needed for its monitor-aware workflow.

## Native Plasma integration

| Responsibility | Native implementation |
| --- | --- |
| Theme, colors and fonts | Plasma LookAndFeel package, KDE color scheme and font settings |
| Widgets and window decorations | Installed Breeze style, desktop theme, icons and decoration |
| Desktop and lock-screen backgrounds | Plasma image wallpaper and standard lock-screen components |
| Panels and workspace display | User-managed panels and native Pager |
| Standard window actions | Existing KWin close, maximize, fullscreen, switcher, screen-focus and zoom actions |
| Standard desktop selection | KWin `Switch to Desktop 1–5` on the focused monitor |
| Application/service actions | KGlobalAccel desktop actions, KRunner, settings, emoji and Spectacle |
| Clipboard and session controls | Existing Plasma and KDE actions |

No panel layout script or custom applet is shipped. The native Pager tracks
per-screen desktop selection but shares desktop names/indices; Graphite's
secondary number-key bank does not change those labels.

## Custom component inventory

| Component | Why it exists | Lifetime |
| --- | --- | --- |
| [install.py](../install.py), [theme.py](../theme.py), [doctor.py](../doctor.py) | Reproducible selected configuration, asset generation, preflight, packaging and recovery exceed native theme-package scope | Command invocation |
| [Workspace template](../templates/workspaces.js), installed as `kde-hypr-bridge` | Fixed monitor-number mapping, cross-monitor sends without following, clamped navigation, first empty desktop and scratchpad combine behavior absent from standard actions | One in-process KWin script |
| [Keyboard-layout helper](../scripts/workspace-keys.py) | Finnish/US shifted number symbols overlap between positions; a static union of aliases is ambiguous | One event-driven Python process per KDE session |
| [Application resolver](../scripts/launch-app.py) and [applications.py](../applications.py) | Resolve current KDE/MIME defaults and fallbacks at activation; native fixed commands cannot express every preference | Short-lived, followed by `exec` |
| Generated `org.kde.graphite.applications.desktop` | Expose configured application actions to native KGlobalAccel | Declarative service file |
| Generated keyboard-helper autostart entry | Start the single-instance layout helper through KDE-only XDG autostart | Declarative session entry |
| [Wallpaper template](../templates/wallpaper.js) and recovery script in `install.py` | Apply alternating per-screen images and restore saved desktop IDs without replacing panel layouts | One Plasma scripting call per operation |
| [XKB symbols](../assets/xkb/symbols/graphite) | Optional AltGr-to-Super mapping without swapping away the ordinary right Super key | Native keyboard configuration |
| [wheel/](../wheel) | Optional Super+wheel axis shortcuts with desktop-wide scope | One native KWin effect |
| [sddm/](../sddm) | Separate system login appearance and recovery | SDDM greeter; installer on demand |

Theme assets are native data, not a replacement desktop. Asset renderers under
[tools/](../tools) are development tools and are never copied into runtime.
The `hypr` substrings in script/effect IDs are retained identifiers; these
components run in KWin and do not require Hyprland.

## Installer responsibilities and boundaries

The default `theme` profile applies appearance. The explicit `install` profile
adds keyboard/workspace integration. Both share appearance generation in
`theme.configuration()` and `theme.payload()`.

The appearance profile merges selected values in `kdeglobals`, `kwinrc`,
`breezerc`, `plasmarc` and `kscreenlockerrc`, writes the selected-theme marker,
and installs the theme, named wallpapers and color scheme. It sets Breeze,
fonts, palette, titlebar buttons/borders, maximized titlebar visibility and
lock-screen presentation. It applies the two wallpaper variants through Plasma.

The workflow additionally sets five desktops, per-output desktop selection,
Graphite script/output preferences, native/global shortcuts and layout-helper
autostart. Opt-in AltGr configuration adds selected `kxkbrc` entries and XKB files.
Normal installation preserves the wheel setting unless `--with-wheel` requests
that an already discoverable effect be enabled.

KConfig merges preserve unrelated text, comments and localized values; locked
selected entries fail. Graphite does not set animation speed, disable desktop
effects, change focus policy or disable GTK synchronization. KDE's own GTK
integration may propagate appearance according to existing user preferences.
Desktop names, rows, user panels and independent scripts are retained.

Installation does not download dependencies, invoke a package manager or use
sudo. Only the separate SDDM installer needs administrator access. Installed
runtime files use the destination XDG paths and do not depend on the checkout.
See [Troubleshooting](troubleshooting.md#installed-paths) for the path inventory.

## Shortcut architecture

[shortcuts.json](../shortcuts.json) defines native/action and application keys.
`workspace_shortcuts()` in `install.py` supplies the custom script's table, so
key sequences are not duplicated in its template.

KGlobalAccel registers and persists shortcuts through D-Bus. Explicit ordinary
application overrides execute directly through KDE. Dynamic actions use the
resolver; executable names containing `%` also use it because KIO treats that
executable token differently from argument field codes. Desktop Entry quoting
and repeated launches have isolated native integration tests.

Registration skips already satisfied bindings and retains extra aliases.
Conflict detection checks ownership before changes: unknown actions block the
operation; only known native counterparts or Graphite's own actions may lose a
conflicting key. Actual displaced owners are recorded for recovery. No separate
shortcut daemon or parallel registry is installed.

The layout helper starts through KDE-only XDG autostart and claims
`org.kde.GraphiteWorkspaceKeys` to prevent duplicate instances. It listens for
KDE layout signals, derives shifted symbols with XKB, checks alias ownership,
releases old aliases and assigns the current ones. It skips duplicate symbol
maps. GDBus subprocesses run on updates, not on a polling loop.

## Workspace integration

Plasma 6.7+ per-screen desktops supply the independent state. The bridge maps
primary/secondary keys to those same five native desktop objects, sends windows
across outputs and selects desktops through KWin scripting APIs. Native focused-
monitor numbered selection remains a KWin action. Custom relative navigation
clamps at 1/5; window sends do not follow the moved window. These semantics differ
from native relative actions that follow the destination and use KDE wrapping
preferences.

Output roles are resolved at installation from KDE display priority or explicit
names. At runtime the script falls back to available screens. Physical hot-plug
and display-priority transitions remain acceptance-test cases.

Scratchpad membership lasts only for the KWin script session. Showing moves its
windows to the focused screen/desktop, restores them and temporarily raises them.
Hiding minimizes them and undoes only keep-above changes made by Graphite. Native
window-rule configuration, titlebars and skip-pager flags are not changed.
Active unparented QTimers are kept reachable until their callbacks complete.

## Mouse-wheel integration

The optional `mwheelsetup` functionality is implemented by `wheel/` and the
`wheel` installer command. The effect registers Meta+wheel up/down and invokes
`KdeHyprWorkspaceNext` / `KdeHyprWorkspacePrev` through KGlobalAccel. It depends on
the installed Graphite workspace workflow; appearance installation is independent.

The build uses local CMake source, matching KWin headers/library, Qt 6 and KF6.
The user binary is replaced atomically, preserving a currently mapped inode.
A Plasma-session environment script adds its plugin root to `QT_PLUGIN_PATH`
while retaining existing entries. Plasma applications inherit that path; a
narrower portable replacement has not been verified. KWin's versioned plugin
factory IID makes rebuilding after KWin upgrades necessary.

## Recovery and upgrades

Before applying changes, the installer snapshots selected files and wallpaper
state. Unchanged bytes retain their files; repeated installation still creates
backup history. Selected KConfig keys and actual displaced shortcut owners are
recorded in the backup manifest. Wallpaper recovery uses desktop IDs through
Plasma scripting and never writes a whole panel configuration.

Restore validates backup sources and computes selected configuration recovery
before replacing files. It preserves later unrelated preferences; owned payload
files are recovered whole. Failure rollback also restores the previous backup
pointer. D-Bus state cannot be rolled back atomically with file state, so logout/
login is required. No live KWin script reload or plasmashell restart is performed.

Upgrade cleanup is limited to known retired Graphite launcher files/actions,
utilities and theme layout files. Installed legacy widgets are left intact for
user panels. Independent KWin scripts, including tilers, are not managed.
Older backups lack complete ownership metadata: known KWin/shortcut entries are
recovered conservatively, some native conflicts may need manual recovery, and
other legacy files still restore whole. Earlier effect/GTK/animation preferences
are not automatically reset because their current ownership cannot be inferred.

## Compatibility boundaries

Appearance preflight accepts KWin 6.x; the package declares Plasma 6.0 minimum.
The full workflow requires KWin 6.7+ on Wayland and one/two monitors. X11, fresh
installation on every eligible version and physical hot-plugging are unverified.
SDDM uses private Breeze/Plasma QML imports and has its own preflight. Wheel code
is coupled to the installed KWin ABI. No crash-stability or memory-saving claim
is made. See [validation scope](development.md#validation-scope).
