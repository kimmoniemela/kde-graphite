# Graphite setup history

Originally recorded 2026-10-17; revised 2026-10-19 to retain the useful appearance
and workflow decisions. Use the [README](../README.md) for current installation.

The original goal was a quiet, keyboard-driven KDE desktop with charcoal
(`#111416`), muted sage (`#a6b8a1`), monospace type, Breeze widgets/decorations
and original static contour wallpapers. Changes were scoped to KDE; configuration
for Hyprland and other desktops was not imported as machine defaults.

The appearance became a native Global Theme, `org.kde.graphite.desktop`, with
its palette, fonts, previews and two wallpaper variants. Previews are illustrative
renders. The standard lock screen uses the matching charcoal background and
monospace clock without replacing authentication settings.

An early ten-global-desktop arrangement was replaced with five native desktops
selected independently on each output. Primary number keys address 1–5 and
secondary keys address 6–0; Shift moves to the corresponding output/desktop.
Both banks target the same five desktops with one connected monitor. KDE display
priority chooses output roles unless overridden in local preferences.

The native wheel effect, `kwin_hypr_scroll_desktop`, remains an explicit local
build with a per-user installation and backups. It clamps Super+wheel navigation
at the five-workspace boundaries. Rebuild against the installed KWin after upgrades.

On 19 October the architecture was narrowed to native Plasma integration:
user-managed panels/Pager, native application actions and native ordinary KWin
shortcuts. Custom code remains only for monitor-number routing, send-without-follow,
clamped navigation, scratchpad, dynamic defaults and layout-specific aliases.
The event-driven layout helper now starts through KDE-only XDG autostart.
The optional AltGr mapping remains an opt-in XKB setting.

Past script reloads were suspected in a recorded Qt QML garbage-collector crash.
Installation and restore therefore use files/native APIs and require a new login,
without restarting KWin scripts or plasmashell. No claim is made that custom or
upstream crashes can be eliminated.

See [architecture](architecture.md) for current boundaries and validation limits,
[components](components.md) for the dependency/runtime inventory, and
[third-party licenses](../THIRD_PARTY.md). Historical Fedora/Arch observations
are evidence for their recorded versions, not graphical verification of later
refactors or clean-machine installations.
