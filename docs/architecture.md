# Architecture

Graphite is a minimal KDE Plasma theming and keyboard-workflow project.
Native Plasma owns the desktop. Custom code supplies only the workflow gaps
listed below; it does not enforce window geometry or manage automatic tiling.

## Native functionality and retained extensions

| Behavior | Implementation and reason |
| --- | --- |
| Appearance | Native LookAndFeel package, color scheme, fonts, Breeze, image wallpapers and standard lock screen |
| Panels and workspace display | User-managed Plasma panels and native Pager; no Graphite containment creation or applets |
| Window close/maximize/fullscreen, screen focus, zoom | Existing KWin actions |
| KRunner, settings, emoji, screenshots, clipboard, session menu/lock | Existing KDE service/action registrations |
| Focused-monitor numbered desktops | Native KWin `Switch to Desktop 1–5` actions |
| Primary/secondary 1–0 banks and window sends | One small KWin JavaScript script; native numbered actions do not encode a fixed output role and cross-output moves |
| Relative navigation and sends | Same script; clamps at 1/5 and sends without following. Native relative window moves follow the destination and respect desktop wrapping preferences |
| First empty desktop and scratchpad | Same script; no equivalent native shortcut combines these behaviors |
| Shifted Finnish/US number row | One event-driven Python helper; layout-dependent symbols can map to different numbers, so a static union of aliases is ambiguous |
| Default applications | Short-lived Python resolver followed by `exec`; native command shortcuts cannot resolve all four KDE preferences afresh with arbitrary overrides |
| AltGr as an extra Super | Optional six-line XKB symbol definition; the stock right-Alt/right-Win swap also changes the ordinary right Super key |
| Super+wheel anywhere | Optional existing native KWin axis-shortcut effect; ordinary desktop/window wheel bindings have different scope |

The native wallpaper CLI sets one image for all desktops; the small wallpaper
script retains alternating per-screen images and scoped recovery.

The native Pager tracks the current desktop by screen and can filter windows by
screen. It uses shared desktop names/indices, so it does not reproduce the old
secondary 6–10 labels or custom occupancy styling. The keyboard mapping remains
unchanged. Add/configure Pager through Plasma; existing panels are never edited.
See KDE's [Pager model](https://github.com/KDE/plasma-desktop/blob/Plasma/6.8/applets/pager/pagermodel.cpp)
and [Pager UI](https://github.com/KDE/plasma-desktop/blob/Plasma/6.8/applets/pager/qml/main.qml).

The workspace script uses the documented
[KWin scripting API](https://develop.kde.org/docs/plasma/kwin/api/).
Native output-default desktop selection and relative-move behavior were checked
against [virtual desktops](https://github.com/KDE/kwin/blob/Plasma/6.8/src/virtualdesktops.cpp)
and [window actions](https://github.com/KDE/kwin/blob/Plasma/6.8/src/useractions.cpp).
One/two-monitor routing, single-screen fallback, independent selections and
send-without-follow behavior have JavaScript regression coverage.

## Shortcut ownership and runtime

`shortcuts.json` defines native and application bindings. `workspace_shortcuts()`
defines the remaining custom actions and feeds the generated workspace script;
the template no longer duplicates their key sequences.

KGlobalAccel owns a generated desktop-action service. Explicit command arrays
launch through KDE directly. Dynamic defaults use `launch-app.py` and
`applications.py`; the resolver replaces its own process with the selected
command. A resolver fallback handles executable names containing `%`, which
KIO does not expand like ordinary argument field codes. Quoted arguments,
repeated launches, preference changes and this fallback are tested against the
real native shortcut host on a private D-Bus session.

Stock actions are bound to their existing components, rather than wrapped in a
KWin launcher. KGlobalAccel persists its own configuration through D-Bus; Graphite
does not encode the version-dependent service-group layout. Existing alternative
keys are retained. Unknown conflicting actions stop the operation; only known
native counterparts and Graphite's own previous actions can lose a conflicting
key. Other alternatives stay intact. Layout aliases also check ownership before
changing bindings. This is one shortcut registry, not a second launcher framework.
See [KDE's service action implementation](https://github.com/KDE/kglobalacceld/blob/Plasma/6.8/src/kserviceactioncomponent.cpp).

The layout helper starts through native XDG autostart, only in KDE. It listens to
layout signals, has a single-instance D-Bus name and ignores duplicate symbol
maps. It does not poll. Its short GDBus calls occur only on layout changes;
replacing those with typed QtDBus calls remains an opportunity requiring tests.
No new background service was added. One persistent Python layout process remains;
the resident launcher QML and custom applet are no longer installed. Memory savings
have not been measured, and an existing user panel may still run its old widget.

Scratchpad membership lasts for the session. Sending hides the scratchpad;
showing moves its windows to the focused output/desktop and temporarily raises
them. Hiding restores keep-above changes Graphite made, preserving preexisting
keep-above state and honoring KWin's effective window-rule values. No titlebar,
skip-pager, tiler or window-rule configuration is changed.

## Configuration boundary

The installer changes the selected palette, UI fonts, Breeze style/icons and
window decoration appearance, titlebar buttons, maximized titlebar visibility,
static wallpapers and lock-screen presentation. The workflow additionally sets
five desktops and per-output desktop selection, its script/output preferences,
shortcuts and KDE-only keyboard-helper autostart. Existing desktop names and
rows are preserved. Optional AltGr and wheel setup are separate opt-ins.

Graphite no longer disables effects, sets animation duration, changes focus
policy, unloads GTK synchronization, or writes its autoload preference. Earlier
values are not automatically reset: their current ownership is unknowable.
Change those preferences in KDE settings or restore an appropriate backup.
KDE's own GTK integration can still propagate appearance according to the user's
preferences; Graphite does not write GTK or other desktops' configuration itself.

Narrow, text-preserving KConfig merges retain comments, localized values and
unrelated groups; locked entries fail. Native D-Bus APIs handle shortcut
registration and Plasma wallpaper changes. Wallpaper backup/restore uses desktop
IDs through Plasma scripting and never writes whole containment files. A failed
wallpaper snapshot aborts before applying changes.

The desktop installer never invokes sudo, a package manager or a download.
Missing explicit override commands fail preflight. Missing optional defaults or
native shortcut services are reported. Runtime files use destination XDG paths
and do not depend on retaining the source checkout.

## Updates, recovery and compatibility

Identical file contents retain their inode and timestamp. Already satisfied
shortcut bindings retain aliases and skip registration. The installer lets KGlobalAccel's debounced
writes settle after shortcut changes and before failure recovery. Each operation still
creates a private recovery record; this deliberate backup history is not a
runtime configuration change.

Backups validate all source files and compute scoped recovery before replacing
any destination. New KConfig records identify only the selected entries and any
actual native shortcut owners displaced by conflicts. Restore recovers raw entries,
including KConfig expansion flags, while retaining later unrelated preferences.
Failure restores selected settings/files and the previous successful backup pointer. Native
D-Bus changes cannot be rolled back atomically with files; logout/login is required
after installation or recovery. Neither KWin scripts nor plasmashell are restarted.
Old backups containing whole panel files restore desktop wallpapers only, leaving
current panels intact. Legacy KWin/shortcut backups infer only known Graphite
entries, preserving third-party script settings. Older records cannot identify
every displaced native shortcut owner, so those unrecorded legacy bindings may
need manual recovery. Other legacy files and Graphite-owned payload files are
restored whole, replacing later edits to those files.

Upgrade cleanup is limited to known Graphite launcher files/actions, retired
utility files that actually exist, and the old Global Theme layout scripts. The
latter must be removed so an upgraded theme cannot expose a panel-reset layout.
Installed custom widgets are retained for panels that reference them; replace
them manually before removing their installed package. Third-party KWin scripts,
including existing tilers, are never inspected, modified or reloaded.

Appearance supports Plasma 6; the workflow needs Plasma 6.7+ Wayland's per-screen
desktops. Output roles come from KDE priority or explicit overrides. More than two
screens can use appearance only. Unplug/redock and display-priority changes still
need physical-session acceptance tests.

The optional wheel source/build remains unchanged. KWin discovers native effects
through Qt plugin paths and validates its versioned factory IID. The existing
Plasma-session-only `QT_PLUGIN_PATH` entry remains: no portable, verified per-KWin
user-plugin path was found. A systemd-only override would exclude supported
non-systemd sessions. This environment is inherited by Plasma applications, so
it remains an isolated optional compatibility boundary. Rebuild after KWin upgrades.
See the [native effect loader](https://github.com/KDE/kwin/blob/Plasma/6.8/src/effect/effectloader.cpp).
SDDM retains its separate preflight and private Breeze QML compatibility boundary.

## Validation limits

Portable tests cover generation, configuration preservation, restores, repeated
installs, failure recovery, keyboard layouts, routing and scratchpad state.
Optional native tests cover real KGlobalAccel/KIO execution in temporary XDG
homes on a private bus. KPackage import and wheel builds are additional checks.
These do not establish graphical startup, physical mouse delivery, hot-plugging,
SDDM authentication or crash stability. Test a fresh Plasma account/VM, both
monitor configurations, layout switching, repeated install/restore and physical
wheel input before claiming a release graphically verified.
