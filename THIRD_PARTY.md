# Third-party code

## Kröhnkite

`vendor/krohnkite/` contains the source files from Kröhnkite 0.9.9.2,
release commit `1d7fd74`, with local changes:

- Resolve the current desktop separately for each output on KWin 6.7.
- Preserve floating or tiled state after temporary skip-pager transfers.
- Restore titlebar controls when a normal tiled window becomes floating,
  including windows that start floating and script reloads. Restore normal
  titlebars on script unload.
- Respect the configured border preference in maximized tile layouts.
- Leave default shortcuts unbound; the installer applies the selected mappings.
- Disconnect window/workspace signals on script destruction and ignore pending callbacks after shutdown.
- Ignore geometry and window-management callbacks after script shutdown.

The installer versions the QML entry point and imported JavaScript filenames
to avoid reusing cached module URLs. Script updates still require a new KDE
login; the installer does not unload/reload the running tiler.

Upstream: <https://codeberg.org/anametologin/Krohnkite>

Release archive: `krohnkite-0.9.9.2-1d7fd74.kwinscript`

SHA-256: `42f7f66531d366c74b5fc860381da3517ccb4cdccd1f80c122fcab6e9a8fcf7e`

License: MIT. Copyright notices are retained in the source files.

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
