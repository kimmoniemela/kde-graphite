# Shortcuts

Super means the Windows key. These are the setup's bindings; KDE's nonconflicting
hardware and accessibility shortcuts remain available. Native app shortcuts use KDE
defaults or installed alternatives; `settings.local.json` can override or
disable them. Missing optional apps skip their shortcut handlers.

| Keys | Action |
| --- | --- |
| Super+Enter | Default terminal emulator (KDE preference) |
| Super+Space | KRunner |
| Super+E | Default file manager |
| Super+T | Default text editor |
| Super+W | Default browser |
| Super+C / Calculator key | Installed calculator |
| Ctrl+Shift+Escape | Installed system monitor |
| Super+Z | System Settings |
| Super+X | System tray, if assigned in the native widget |
| Super+A | Notifications, if assigned in the native widget |
| Super+V | Clipboard |
| Super+period | Emoji picker |
| Print / Super+Print | Region / fullscreen screenshot |
| Super+Q | Close window |
| Super+Escape | Force-close selection |
| Super+D | Maximize / restore |
| Super+F | Fullscreen |
| Alt+Tab / Super+Tab | Window switcher |
| Super+1–5 | Primary monitor workspaces 1–5 |
| Super+6–0 | Secondary monitor workspaces 6–10 |
| Super+Shift+1–5 | Send window to primary monitor workspace 1–5 |
| Super+Shift+6–0 | Send window to secondary monitor workspace 6–10 |
| Super+Ctrl+1–5 | Workspace on focused monitor |
| Super+Ctrl+Left / Right | Previous / next workspace |
| Super+Ctrl+Shift+Left / Right | Send window to previous / next workspace |
| Super+Ctrl+Down | First empty workspace |
| Super+Alt+Left / Right | Focus monitor |
| Super+Wheel Up / Down | Next / previous workspace |
| Super+left / right mouse drag | Move / resize |
| Super+S | Show / hide scratchpad |
| Super+Shift+S | Send window to scratchpad |
| Super+L | Lock |
| Super+Alt+C | Session menu |
| Super+Plus / Minus | Zoom; keypad supported |

The scratchpad keeps a session-local list of windows. Sending hides them;
showing restores them on the focused output/desktop and temporarily raises them.
Hiding restores the keep-above state changed by Graphite. It leaves native
window rules, titlebars and pager visibility alone.

Super+wheel requires the explicit `python3 install.py wheel` command and a new
KDE login. Wheel up selects the next workspace, wheel down the previous one,
stopping at 1 and 5. No Ctrl/Shift wheel combinations are claimed by the effect.
Tray and notification shortcuts belong to native widgets. Graphite retains
existing assignments; use Plasma's widget configuration to assign them.

Each monitor has five independent KDE desktops. The keyboard banks address
them as 1–5 and 6–10; key 0 means workspace 10. Native Pager uses the same
desktop names/indices on both screens, without the secondary label offset.
The display order comes from KDE settings at installation, or the explicit
`primary_output` and `secondary_output` overrides. With one connected display,
both number banks target its five workspaces.

To use AltGr (right Alt) as another Super key, set `"altgr_as_super": true` in
`settings.local.json` and pass it to `install --settings settings.local.json`.
The normal left and right Super keys keep working. This replaces AltGr's
third-level character input, including Finnish AltGr combinations. Existing
layout selections and unrelated XKB options are retained. The mapping uses a
small user XKB option under `~/.config/xkb/`, with normal installer backups;
appearance-only installation does not change it. Log in again after installing.
The portable default is `false`, which leaves keyboard mappings untouched.

Native KWin actions provide close, maximize, fullscreen, window switching, zoom,
screen focus and Super+Ctrl+1–5. KRunner, Spectacle, settings, emoji, clipboard and
session controls use their existing KDE components. `shortcuts.json` is the
native/application key registry; the workspace binding table feeds the remaining
custom script. Nonconflicting alternative keys remain available. Conflicts with
unmanaged actions stop installation for resolution in KDE settings.
