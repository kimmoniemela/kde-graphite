# Shortcuts

Super means the Windows key. These are the setup's bindings; KDE's nonconflicting
hardware and accessibility shortcuts remain available. App shortcuts use KDE
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
| Super+X | System tray |
| Super+A | Notifications |
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

The scratchpad keeps a session-local list of windows and uses native KWin
minimize/restore, keep-above and explicit workspace moves.

Super+wheel requires the explicit `python3 install.py wheel` command and a new
KDE login. Wheel up selects the next workspace, wheel down the previous one,
stopping at 1 and 5. No Ctrl/Shift wheel combinations are claimed by the effect.
Tray and notification bindings are configured only when top bars are rebuilt
with `--panel`; existing bar bindings are retained otherwise.

Each monitor has five independent KDE desktops. The bars label them 1–5 on
the primary display and 6–10 on the secondary; key 0 means workspace 10.
The display order comes from KDE settings at installation, or the explicit
`primary_output` and `secondary_output` overrides. With one connected display,
both number banks target its five workspaces; its bar shows 1–5.
