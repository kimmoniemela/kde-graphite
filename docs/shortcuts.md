# Shortcuts

Super means the Windows key. These are the setup's bindings; KDE's nonconflicting
hardware and accessibility shortcuts remain available. Application names below
are the portable defaults; `settings.local.json` can override them.

| Keys | Action |
| --- | --- |
| Super+Enter | Terminal (Konsole) |
| Super+Space | KRunner |
| Super+E | Files (Dolphin) |
| Super+T | Text editor (KWrite) |
| Super+W | Firefox |
| Super+C / Calculator key | Calculator (KCalc) |
| Ctrl+Shift+Escape | Plasma System Monitor |
| Super+Z | System Settings |
| Super+X | System tray |
| Super+A | Notifications |
| Super+V | Clipboard |
| Super+period | Emoji picker |
| Super+P | Color picker; copies hex color |
| Super+Shift+W | Wallpaper settings |
| Print / Super+Print | Region / fullscreen screenshot |
| Super+Q | Close window |
| Super+Escape | Force-close selection |
| Super+Arrows | Focus tiled window |
| Super+Shift+Arrows | Reorder tiles |
| Super+Alt+Space | Toggle floating |
| Super+J | Rotate layout |
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
| Super+Ctrl+Wheel Up / Down | Previous / next workspace |
| Super+Shift+Wheel Up / Down | Move window to previous / next monitor |
| Super+Ctrl+Shift+Wheel Up / Down | Send window to previous / next workspace |
| Super+left / right mouse drag | Move / resize |
| Super+S | Show / hide scratchpad |
| Super+Shift+S | Send window to scratchpad |
| Super+L | Lock |
| Super+Alt+C | Session menu |
| Super+Plus / Minus | Zoom; keypad supported |

The scratchpad uses minimized floating windows, not a separate desktop. Its
membership lasts for the KDE session. Super+J rotates the whole tile layout;
it does not implement Hyprland's per-container split toggle.

Directional focus, tile movement, floating toggle and layout rotation belong
to Kröhnkite. They are inactive when tiling is suspended or the script is
disabled; KDE quick-tiling bindings are not restored automatically. Workspace,
launcher, maximize and fullscreen bindings remain available. See
[tiling](tiling.md) for enabling, suspending and disabling the script.

Each monitor has five independent KDE desktops. The bars label them 1–5 on
the primary display and 6–10 on the secondary; key 0 means workspace 10.
The display order comes from KDE settings at installation, or the explicit
`primary_output` and `secondary_output` overrides. With one connected display,
both number banks target its five workspaces; its bar shows 1–5.
