# Third-party code

## Kröhnkite

`vendor/krohnkite/` contains the source files from Kröhnkite 0.9.9.2,
release commit `1d7fd74`, with local changes:

- Resolve the current desktop separately for each output on KWin 6.7.
- Preserve floating or tiled state after temporary skip-pager transfers.
- Leave default shortcuts unbound; the installer applies the selected mappings.

Upstream: <https://codeberg.org/anametologin/Krohnkite>

Release archive: `krohnkite-0.9.9.2-1d7fd74.kwinscript`

SHA-256: `42f7f66531d366c74b5fc860381da3517ccb4cdccd1f80c122fcab6e9a8fcf7e`

License: MIT. Copyright notices are retained in the source files.

## Workspace wheel effect

`wheel/` derives from <https://github.com/R0h1tAnand/kwin-meta-scroll-switcher>.
Imported upstream commit: `7d48ebdf4a1ab97cc8d2136e6bdc437c98546658`.

It registers Super/Ctrl/Shift wheel shortcuts and dispatches them to the
workspace script. It does not replace KWin.

License: GPL-2.0-or-later; see `wheel/LICENSE`.

## Color scheme

`assets/color-schemes/TerminalGraphite.colors` is a modified KDE Breeze Dark
scheme. The original SPDX copyright and LGPL-2.0-or-later notices are retained.
