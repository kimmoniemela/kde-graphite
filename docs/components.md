# Components

The normal installer applies the theme and shortcuts. It neither installs nor
configures Kröhnkite and retains existing top bars.

| Component | Purpose | Installation |
| --- | --- | --- |
| Graphite Global Theme, palette and wallpaper packages | Appearance using KDE's Breeze components | `theme` or `install` |
| `kde-hypr-bridge` | Monitor-aware workspace switching, explicit window moves and scratchpad shortcuts | `install` |
| `kde-hypr-launchers-v2` | Application shortcut handlers | `install` |
| `workspace-keys.py` | Adapt shifted number-row shortcuts to the active Finnish/US XKB layout | `install` |
| `launch-app.py`, `pick-color.py`, `wallpaper-settings.py` | Run configured application, color-picker and wallpaper shortcuts | `install` |
| `applications.py` | Resolve KDE defaults and available optional apps | Copied with workflow runtime; no separate dependency |
| `org.kde.graphite.workspaces` | Workspace labels and occupied-state indicators on each bar | Explicit `install --panel`; existing widgets remain otherwise |
| `krohnkite` | Automatic tiling | Existing setup preserved; installing/configuring the bundled copy requires `--with-tiling` |
| `graphite-window-controls` | Keep normal titlebar controls when using the bundled tiler | Installed only with `--with-tiling`; existing helper preserved |
| `kwin_hypr_scroll_desktop` | Super+wheel up/down workspace shortcuts | Explicit `wheel` build/install command |

Names containing `hypr` are historical identifiers. These scripts run inside
KDE and do not load Hyprland or edit its configuration. The superseded
`kde-hypr-launchers` is disabled; the v2 launcher is the supported handler.

`workspace-keys.py` starts with the launcher script and watches KDE keyboard
layout signals. Old shifted-symbol bindings are released before assigning the
new layout's symbols. It is the only persistent Python helper installed by the
shortcut profile. The other helpers run only when a shortcut is used.

Workspace and launcher scripts act on explicit shortcuts. They do not enforce
window geometry or implement automatic tiling. Kröhnkite's existing enable/
disable behavior remains controlled by KWin Scripts settings.

Script updates activate at a new KDE login. The installer avoids live KWin
script unload/reload cycles because these previously triggered a compositor
crash. The optional native wheel effect also needs a login after initial
installation and a rebuild after KWin upgrades.
