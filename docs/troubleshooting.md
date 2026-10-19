# Troubleshooting and recovery

[README](../README.md) · [Configuration](configuration.md) · [Architecture](architecture.md)

Run desktop commands from the checkout as your normal user inside Plasma. Keep
the complete error message and the backup path printed by a failed operation.

## Start with the right check

| Situation | Command | What it checks |
| --- | --- | --- |
| Appearance prerequisites | `python3 install.py doctor theme` | Session, KWin version, GDBus, Fontconfig and runtime Breeze assets |
| Workflow prerequisites | `python3 install.py doctor install` | Above, plus Wayland, Python/Qt/XKB, keyboard/shortcut services, output roles and application availability |
| Workflow after a new login | `python3 install.py check` | Selected theme/package, managed script state, five desktops, expected shortcut keys/owners and layout-helper service |
| Wheel after a new login | `python3 install.py check --with-wheel` | Require the installed wheel effect to be loaded as well |
| Workflow without wheel verification | `python3 install.py check --without-wheel` | Skip the wheel check; does not disable or uninstall the effect |

Pass the same `--settings settings.local.json` to doctor that you use for
installation. Check reads installed state and does not accept a settings file.
It normally verifies wheel loading when the saved plugin flag is enabled.
For appearance-only use, doctor is the preflight: check can also inspect an
existing workflow and is not a comprehensive appearance or visual test.

`--dry-run` previews theme/install/wheel/build-theme/restore/check without
applying desktop changes. It is not a substitute for doctor. In particular,
restore/check dry runs return before validating a backup or querying live state.
Doctor is read-only even without that flag.

## Missing command, module or service

Install the reported dependency using your distribution's supported packages,
then rerun doctor. Graphite never does this automatically. Use the distribution
Python that can import PySide6; an isolated environment may hide installed Qt
modules. Appearance-only installation does not require PySide6 or XKB.

A missing optional application/native shortcut service is reported and its
binding is skipped. Install it and repeat workflow installation to add the action.
Missing explicit application overrides fail preflight. For a missing selected
desktop entry, fix KDE's default application or choose an explicit override;
see [application resolution](configuration.md#applications).

D-Bus or display connection errors can mean the command is running outside the
active Plasma session or inside a restricted environment. Run it in that
session's terminal, without sudo. Do not restart the compositor to work around
an installer preflight error.

## Shortcut conflicts

If a key belongs to an unmanaged action, installation stops rather than stealing
it. Resolve the assignment in KDE System Settings → Shortcuts, or change the
Graphite source binding deliberately before reinstalling. Existing known native
counterparts may lose the overlapping key, but retain other alternatives.

After installation, log out and back in. If check reports a missing native
shortcut service or autostart entry, ensure the current checkout was installed
successfully and then start a new Plasma session. A successful check proves
registrations and service state, not every application's interactive behavior.

If shifted Finnish/US window sends fail, check the configured layout/variant,
look for a layout-alias conflict, and verify the helper after login. Its diagnostic
prefix is `Graphite workspace move keys`. The helper owns those aliases; changing
them only in KDE settings may not persist across layout changes.

## Wrong monitor or workspace labels

Inspect `kscreen-doctor -j` and compare the names with local output overrides.
Clear stale overrides or correct them, then rerun doctor and install. Automatic
roles follow KDE display priority at installation. The full workflow supports
one or two connected displays; use appearance only for more.

Native Pager shares desktop names/indices between screens. Seeing 1–5 on both
monitors is expected: secondary keys 6–0 select those five desktops on the second
monitor. With one monitor, both key banks target the same desktops. Set Pager's
window filtering in its native widget configuration if needed.

## Wheel does not switch desktops

The wheel effect requires the Graphite workflow, matching build dependencies and
a new Plasma login. The `wheel` command builds and installs it; `--with-wheel`
on ordinary install only enables an already discoverable effect and never builds
it. Use the [README wheel procedure](../README.md#optional-mouse-wheel).

Rebuild after a KWin upgrade. If doctor/check still rejects the effect, retain
the build error and KWin version for a report. The plugin uses a Plasma-session
Qt plugin path; it is not loaded merely by opening a new terminal. Only
Super+wheel up/down is registered. Physical input delivery needs testing in the
actual session even when effect loading passes.

## Appearance differs from the preview

The README image is illustrative. Graphite does not install its example panel
layout, applications or window arrangement. Use Plasma's panel editor and Pager.
Fonts must already be installed; a missing family falls back to Fira Code or
monospace. Existing desktop effects and GTK integration preferences are retained.

A standalone Global Theme archive supplies native appearance defaults and images.
It does not perform the installer's alternating wallpaper application, lock-screen
configuration or backup procedure. Use the appearance profile for that behavior.

## Restore and removal

Every desktop installation prints a backup path. The latest-backup pointer lives
under the state directory described below. `restore` without a directory undoes
the latest operation and advances the pointer to its predecessor; repeated calls
can unwind earlier installations.

The README shows latest-operation recovery. To select a particular backup:

```sh
python3 install.py restore "/absolute/path/to/backup"
```

Replace the example path with an actual backup directory. Log out and back into
Plasma immediately afterward. Backups belong to the machine/XDG paths where
they were created; they are not a portable configuration distribution.

New backups restore selected KConfig entries and recorded conflicting shortcut
owners, preserving later unrelated settings. Graphite-owned payload files
restore whole, replacing later edits to them. Wallpapers restore only for saved
desktop IDs; panels are not restored or reset. Older records lack complete
shortcut ownership metadata and may require manual recovery of native bindings;
other legacy files can still replace later edits in full.

On failure, the installer attempts rollback and prints whether it succeeded.
If rollback fails, keep the indicated backup and recover explicitly before
continuing. File restoration and live D-Bus state are not atomic, which is why a
new login is required even after automatic rollback.

There is no blanket uninstall/reset command. Restore the relevant installation
backups to recover prior state and remove files those installations created.
For an archive-only installation, select another Global Theme and use KDE's
package-management UI to remove Graphite. Optional SDDM has its own
[system backup and restore procedure](../sddm/README.md#restore).

## Installed paths

Defaults below follow XDG. Overrides must be absolute; empty/unset variables use
the defaults. These installed paths are not additional files in the checkout.

| Location | Contents |
| --- | --- |
| `${XDG_CONFIG_HOME:-$HOME/.config}` | Selected KDE settings and `kdedefaults/package`; workflow `autostart/org.kde.graphite.workspace-keys.desktop`; optional `xkb/` rules and `plasma-workspace/env/graphite-wheel.sh` |
| `${XDG_DATA_HOME:-$HOME/.local/share}/plasma/look-and-feel/org.kde.graphite.desktop` | Native theme package |
| Data directory: `wallpapers/GraphiteContours`, `wallpapers/GraphiteContoursAlternate`, `color-schemes/TerminalGraphite.colors` | Native wallpaper and palette packages |
| Data directory: `kwin/scripts/kde-hypr-bridge` | Generated workspace script |
| Data directory: `kglobalaccel/org.kde.graphite.applications.desktop` | Native application shortcut service |
| Data directory: `kde-graphite/runtime` | Application/layout Python helpers, `applications.py` and `launchers.json` |
| Data directory: `kde-graphite/wheel/qt6/plugins` | Optional native wheel plugin root |
| `${XDG_STATE_HOME:-$HOME/.local/state}/kde-graphite` | `backups/` and `latest-backup` |

Upgrades remove only known retired Graphite files/actions. Previously installed
Graphite widgets are retained for existing panels; replace them manually with
Pager before removing their installed package. Earlier unrelated preference
values are not reset to guessed defaults.

## Reporting a problem

Include the Graphite commit, distribution, Plasma/KWin version, session type,
monitor count, relevant settings without private data, exact command/error and
whether a new login occurred. Distinguish preflight, registration/build results
and graphical behavior. For suspected crashes include relevant journal/backtrace
excerpts; a log warning alone does not establish its cause.
