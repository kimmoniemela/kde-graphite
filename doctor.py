"""Read-only dependency checks for Graphite's two installation profiles."""
import importlib
import importlib.util
import json
import ctypes.util
import os
from pathlib import Path
import re
import shutil

import applications


def problems(api, options, full=False, with_wheel=False):
    errors = []
    if os.geteuid() == 0:
        errors.append('Run as the desktop user, without sudo.')
    if 'KDE' not in os.environ.get('XDG_CURRENT_DESKTOP', '').split(':'):
        errors.append('Run inside a KDE Plasma session.')
    if full and not os.environ.get('WAYLAND_DISPLAY'):
        errors.append('The full setup requires a Plasma Wayland session.')
    commands = ['gdbus', 'fc-list']
    if full:
        commands.append('kscreen-doctor')
        if any(options['applications'][name] == applications.DEFAULT for name in ['Terminal', 'Browser']):
            commands.append('kreadconfig6')
        if any(options['applications'][name] == applications.DEFAULT for name in ['Terminal', 'Browser', 'Files', 'Editor']):
            commands.append('kstart')
        commands += [argv[0] for argv in options['applications'].values() if argv and argv != applications.DEFAULT]
        if not ctypes.util.find_library('xkbcommon'):
            errors.append('Missing runtime library: libxkbcommon (keyboard layout shortcuts).')
        if importlib.util.find_spec('PySide6') is None:
            errors.append('Missing Python module: PySide6 (use the distribution Python and packages).')
        else:
            try:
                for module in ['QtGui', 'QtCore', 'QtDBus']:
                    importlib.import_module('PySide6.' + module)
            except (ImportError, OSError) as error:
                errors.append('Cannot load PySide6 runtime: ' + str(error))
    missing = sorted({name for name in commands if not shutil.which(name)})
    errors += ['Missing command: ' + name for name in missing]
    if 'gdbus' not in missing:
        try:
            info = api.kwin('/KWin', 'org.kde.KWin.supportInformation')
            version = re.search(r'KWin version: (\d+)\.(\d+)', info)
            if not version or int(version[1]) != 6 or (full and int(version[2]) < 7):
                errors.append('Requires Plasma 6.7+ for the full setup, or Plasma 6 for appearance only.')
            api.dbus('org.kde.plasmashell', '/PlasmaShell', 'org.freedesktop.DBus.Peer.Ping')
            if full:
                api.dbus('org.kde.kglobalaccel', '/kglobalaccel', 'org.freedesktop.DBus.Peer.Ping')
                api.dbus('org.kde.keyboard', '/Layouts', 'org.freedesktop.DBus.Peer.Ping')
            if with_wheel and api.kwin('/Effects', 'org.kde.kwin.Effects.isEffectSupported', api.WHEEL) != '(true,)':
                errors.append('Wheel plugin unavailable: install wheel/ or omit --with-wheel.')
        except (RuntimeError, OSError, ValueError, SyntaxError) as error:
            errors.append('Desktop service unavailable: ' + str(error))
    data_roots = [Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share')]
    data_roots += [Path(p) for p in (os.environ.get('XDG_DATA_DIRS') or '/usr/local/share:/usr/share').split(':') if p]
    for relative in ['plasma/desktoptheme/default/metadata.json', 'icons/breeze-dark/index.theme']:
        if not any((root / relative).is_file() for root in data_roots):
            errors.append('Missing Breeze asset: ' + relative)
    return errors


def require(api, options, full=False, with_wheel=False):
    errors = problems(api, options, full, with_wheel)
    if errors:
        raise RuntimeError('Preflight failed; no changes made:\n  - ' + '\n  - '.join(errors))


def report_optional(options):
    commands, warnings = applications.launchers(options)
    for component in json.loads((Path(__file__).parent / 'shortcuts.json').read_text())['native']:
        if component.endswith('.desktop') and not applications.service_path(component):
            warnings.append(component + ': native shortcut service unavailable; bindings skipped.')
    for warning in warnings:
        print('Optional: ' + warning)
    return commands
