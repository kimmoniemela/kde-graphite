# Third-party notices

Graphite's original code and assets use the [MIT license](LICENSE). The derived
components below retain their upstream notices and separate licenses.

## Workspace wheel effect

[wheel/](wheel) derives from
[R0h1tAnand/kwin-meta-scroll-switcher](https://github.com/R0h1tAnand/kwin-meta-scroll-switcher),
imported at commit `7d48ebdf4a1ab97cc8d2136e6bdc437c98546658`.
It registers Super+wheel up/down and dispatches workspace actions to the Graphite
KWin script. See [wheel/LICENSE](wheel/LICENSE), GPL-2.0-or-later.

## Color scheme

[TerminalGraphite.colors](assets/color-schemes/TerminalGraphite.colors) is a
modified KDE Breeze Dark scheme. Its original SPDX copyright and
LGPL-2.0-or-later notices remain in the source and packaged palette. The license
text is included under [assets/LICENSES/](assets/LICENSES/LGPL-2.0.txt) and in the
[Global Theme package](theme/org.kde.graphite.desktop/LICENSES/LGPL-2.0.txt).

## SDDM login theme

[sddm/graphite/](sddm/graphite) derives from the KDE Plasma 6.8 Breeze SDDM theme.
Original QML copyright headers remain. Its controls and fallback avatar are
retained; Graphite supplies its palette, static contour background and wordmark.
See the [SDDM source notes](sddm/README.md#source-and-license) and
[LGPL-2.0-or-later license](sddm/LICENSE.LGPL-2.0-or-later.txt).
The original Graphite wallpaper and installer use the project's MIT license.
