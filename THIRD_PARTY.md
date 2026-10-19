# Third-party code

## Workspace wheel effect

`wheel/` derives from <https://github.com/R0h1tAnand/kwin-meta-scroll-switcher>.
Imported upstream commit: `7d48ebdf4a1ab97cc8d2136e6bdc437c98546658`.

It registers Super+wheel up/down and dispatches next/previous actions to the
workspace script. It does not replace KWin. Installation is explicit and uses
the local source and installed build tools, without downloading dependencies.

License: GPL-2.0-or-later; see `wheel/LICENSE`.

## Color scheme

`assets/color-schemes/TerminalGraphite.colors` is a modified KDE Breeze Dark
scheme. The original SPDX copyright and LGPL-2.0-or-later notices are retained.

## SDDM login theme

`sddm/graphite/` derives from the installed Plasma 6.8 KDE Breeze SDDM theme.
Its login controls, session/keyboard chooser and fallback avatar are retained;
Graphite adds its palette, static contour background and small wordmark.
Original QML copyright headers remain. See [source and license](sddm/README.md)
and `sddm/LICENSE.LGPL-2.0-or-later.txt`. The Graphite wallpaper is a project asset.
