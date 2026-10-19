# Architecture and fresh-machine contract

Graphite is a minimal KDE Plasma theme and keyboard-driven desktop workflow.
It uses a small user-level configuration installer. The same source and commands
apply on supported KDE distributions. Historical Arch and Fedora audits document observations; they
do not define separate installation variants.

## Boundaries

| Component | Responsibility | Dependency boundary |
| --- | --- | --- |
| Appearance | Breeze palette, fonts, wallpaper, decorations, lock screen | Plasma 6 and installed Breeze; no application or build dependency |
| Workflow | Explicit workspace and app shortcuts | Plasma 6.7+ Wayland, PySide6/QtDBus and existing KDE runtime tools |
| Applications | Resolve desktop defaults at launch; select installed calculator/monitor | Missing optional apps skip their bindings; no package install |
| Panels | Replace/create top bars | Explicit `--panel`; validate widgets and task manager QML first |
| Wheel | Native KWin axis-shortcut plugin | Explicit build; installed development files; local KWin ABI |
| SDDM | System login theme | Separate root command, Qt 6 greeter/QML preflight and backup |

The desktop installer never invokes sudo, pip, a system package manager, or a
download command. It does not modify display modes, GPU configuration, shell
startup files, other desktop configuration or the selected default applications.
Runtime scripts are copied into the destination XDG data directory; they have
no dependency on keeping the source checkout in its original location.

## Preferences and capabilities

`settings.json` contains portable defaults. A local JSON file can override only
the needed values. `["@default"]` means resolve
the desktop preference; an empty array disables that app's shortcuts. Explicit
commands that are missing fail preflight. Optional auto-selected apps that are
missing produce a report and are omitted from generated handlers.

Terminal uses KDE's TerminalService / TerminalApplication preference. Browser
uses KDE's browser preference or its HTTPS MIME association. Files and editor
use the directory and text MIME associations when xdg-mime is available.
KDE launches desktop entries through kstart so field codes and activation are
handled by the desktop. Installed application fallbacks are used only when no
preference was obtained. Preferences are re-read on each shortcut activation.

Doctor checks required commands, session services, KWin version, Qt Python
imports, XKB, QML modules and Breeze assets before installation. QML locations
come from Qt's runtime, avoiding distribution-specific Qt development tools.
The installer detects display priority instead of shipping monitor names.

One or two monitors and five desktops per output are the supported workflow.
More monitors can use appearance only. Explicit disconnected output overrides
fail early. On unplug, workspace scripts fall back to available screens;
redocking and primary-display changes still need a physical-session test.

## Updates and recovery

Before mutation, each operation saves all files it may change. Backup
directories are private, manifests are written atomically, and each backup
records its predecessor. Configuration updates preserve unrelated text,
localized entries and nested groups. Locally locked KConfig entries fail rather
than silently pretending they were changed. Individual payload writes use
atomic replacement.

Only the workspace and launcher KWin scripts are managed. Third-party script
files, settings and enable states are preserved. Shortcut conflicts with
unmanaged KWin actions stop installation for resolution in System Settings;
Graphite does not reassign another script's bindings. Runtime payloads explicitly
include the maintained launch and keyboard-layout helpers. Workflow upgrades
back up and remove the two retired Graphite utility helpers and unregister their
actions; they do not remove or migrate any third-party scripts.

Desktop operations restore saved files automatically on failure, retaining the
failure backup for inspection and keeping the previous successful backup as
the restore target. Restore validates all saved source files before replacing
any destination. Repeated restore unwinds successive installations. Backups
restore entire touched files, including later edits; they are local recovery
records, not portable machine configuration.

Live D-Bus changes cannot be made atomic with filesystem changes. A new KDE
login is required after workflow updates, failure recovery or restore. KWin
script unload/reload is deliberately avoided because it previously caused a
compositor crash. This is file rollback, not a claim of a transactional desktop
session. Disk failure or process termination during mutation still requires
manual restore using the printed backup directory.

The GTK synchronizer is stopped before colors change to keep KDE styling from
spreading into other desktops. KDE's service is named kded6, but its module
autoload configuration still uses kded5rc in
[upstream KDED](https://github.com/KDE/kded/blob/master/src/kded.cpp).

## Verification and remaining release checks

The automated suite covers isolated fresh XDG homes, repeat installs, missing
dependencies and optional apps, failure after writes, restore history and
corrupt backups, configuration preservation, keyboard layouts, JavaScript
workspace behavior, and native theme import. Node and KPackage tools
enable their respective tests; the tests do not install them. GitHub checks
run portable Python and JavaScript tests and build the theme archive; tests
requiring a KDE runtime are skipped there.

The 2026-10-18 review also passes live read-only preflight on Plasma 6.8,
builds the wheel against the installed KWin headers, and imports the theme in
an isolated KPackage data directory. It does not reinstall the active desktop.

Before claiming a new distribution or Plasma version as graphically tested,
run this acceptance pass in a clean VM or spare account:

1. Run doctor and install without a local settings file, then log in again.
2. Check application defaults, workspace switch/move, Finnish/US keyboard
   layout changes, screen focus, scratchpad and native window controls.
3. Repeat install, then restore twice; verify the original desktop after login.
4. Test one screen, two screens, unplug/redock and changed display priority.
5. Exercise optional panels; test wheel with a physical
   mouse after login. Preview SDDM and test authentication in a recoverable VM.

Suggested next improvement: run that graphical acceptance pass in a disposable
Plasma VM before each release. Native plugin builds and unit tests cannot
establish that a fresh graphical login or real authentication works everywhere.
