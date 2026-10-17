# Components

The appearance profile needs the Global Theme assets and the window-controls
script. The complete keyboard/tiling workflow uses the following components.

| Component | Purpose | Keep? |
| --- | --- | --- |
| `krohnkite` | Automatic tiling | Optional; disabling it must leave ordinary window management. |
| `kde-hypr-bridge` | Monitor-aware workspace switching, window moves and scratchpad | Yes, for the current 1–5 / 6–10 workspace model. |
| `kde-hypr-launchers-v2` | Application shortcuts | Yes, for the configured launch keys. |
| `graphite-window-controls` | Restore minimize, maximize and close controls on normal windows | Yes, for the requested window-button behavior. |
| `org.kde.graphite.workspaces` | Display each monitor's workspace numbers and selection | Yes, for matching bar labels and keyboard destinations. |
| `workspace-keys.py` | Adapt shifted number-row shortcuts to the active keyboard layout | Yes, for Super+Shift+number on layouts such as Finnish and US. |
| `launch-app.py`, `pick-color.py`, `wallpaper-settings.py` | Run application, color-picker and wallpaper shortcuts | Yes, for those bindings. |
| `kwin_hypr_scroll_desktop` | Super+wheel workspace actions | Optional native effect. |

The old `kde-hypr-launchers` script is superseded by v2. It is disabled in the
portable configuration and was removed from this machine after backing it up.
Names containing `hypr` are historical identifiers: these scripts run in KDE
and do not load or edit Hyprland configuration.

`workspace-keys.py` starts with the launcher script and watches KDE's layout
signals. It adds bindings for the shifted symbols produced by the active
number row, retaining the canonical Super+Shift+number bindings. When the layout
changes, old symbol bindings are released before new ones are assigned.

Kröhnkite disconnects workspace/window signals during destruction and rejects
pending callbacks after shutdown. Its suspended runtime mode also ignores move,
resize and geometry-enforcement callbacks. No companion workspace or launcher
script enforces window size.

Script updates take effect on a new KDE login. The current session can retain
old JavaScript callbacks; reloads of the shared QML engine have previously
crashed KWin. Log out and back in once after updating these files.
