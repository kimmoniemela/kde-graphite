# Graphite SDDM theme

[Project README](../README.md) · [Troubleshooting](../docs/troubleshooting.md)

An optional charcoal-and-sage login theme derived from Plasma 6.8 Breeze. It uses
a static contour background and system monospace type while retaining Breeze's
login, session, user, keyboard and power controls. It does not change PAM,
autologin, users or the selected session.

<img src="graphite/preview.png" alt="Graphite login theme shown in the SDDM test greeter" width="800">

This existing preview was captured from the SDDM greeter in test mode. It is not
evidence of a real password-authentication test.

## Requirements

The theme was previewed with SDDM 0.21.0 and Plasma 6.8 on Arch-based CachyOS.
Other combinations are unverified. The separate installer checks for an installed
SDDM greeter and Qt 6 QML modules: QtQuick, Layouts, Controls, Qt5Compat graphical
effects, Plasma components/extras, Kirigami, the private keyboard indicator,
workspace keyboard layout and Breeze components.

These modules must already exist. No packages or fonts are installed. The theme
uses private Plasma/Breeze imports, so compatibility can change with updates.
The desktop theme does not require this integration or SDDM.

## Preview

From the checkout root, run inside the desktop without sudo:

```sh
sddm-greeter-qt6 --test-mode --theme "$PWD/sddm/graphite"
```

Some distributions name the Qt 6 binary `sddm-greeter` instead. Close the test
window to return to the desktop. Test mode does not authenticate a session or
select the theme for the real login screen.

## Installation

From the checkout root:

```sh
python3 sddm/install.py --dry-run
sudo python3 sddm/install.py
```

The dry run validates source files and greeter/QML prerequisites. Administrator
access is required only for the real system installation. It changes these
locations, backing up existing contents first:

| System path | Purpose |
| --- | --- |
| `/usr/share/sddm/themes/graphite` | Root-owned theme files, readable by SDDM |
| `/etc/sddm.conf.d/99-graphite.conf` | Select `Current=graphite` and system monospace font |
| `/var/lib/kde-graphite/sddm-backups/` | Private installation backups |

The wallpaper is included locally; SDDM does not need access to the user's home.
The packaged Breeze theme stays available. A higher-priority selection of another
theme in a drop-in or `/etc/sddm.conf`, or a custom `ThemeDir`, causes installation
to stop before changes. Review the conflicting preference rather than replacing
an entire SDDM configuration file.

No service is restarted. Graphite appears when SDDM next displays the login
screen. The normal desktop installer does not modify SDDM.

## Restore

Use the backup directory printed by the SDDM installer, replacing `BACKUP_NAME`:

```sh
sudo python3 sddm/install.py --restore /var/lib/kde-graphite/sddm-backups/BACKUP_NAME
```

Restore validates its manifest before replacing the two installation targets and
does not restart the display manager. Legacy backups without a manifest require
manual recovery. Desktop `install.py restore` handles different, per-user backups.
There is no SDDM restore dry-run mode: `--dry-run` always previews installation,
so do not combine it with `--restore` expecting recovery validation.

## Source and license

The QML and fallback avatar derive from the installed KDE Plasma 6.8 Breeze SDDM
theme, with original notices retained. The upstream source is the
[KDE Plasma Workspace SDDM theme](https://invent.kde.org/plasma/plasma-workspace/-/tree/Plasma/6.8/sddm-theme).
QML uses LGPL-2.0-or-later; see [the license](LICENSE.LGPL-2.0-or-later.txt).
The original Graphite wallpaper and installer use the repository's
[MIT license](../LICENSE). See [third-party notices](../THIRD_PARTY.md).
