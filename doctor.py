"""Read-only dependency checks for Graphite's two installation profiles."""
import importlib
import importlib.util
import ast
import ctypes.util
import json
import os
from pathlib import Path
import re
import shutil

import applications


def qml_import_path():
    from PySide6.QtCore import QLibraryInfo
    return Path(QLibraryInfo.path(QLibraryInfo.QmlImportsPath))


def problems(api, options, full=False, with_wheel=False, panel=False):
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
    if full and importlib.util.find_spec('PySide6') is not None:
        try:
            qml = qml_import_path()
            # org.kde.kwin is provided by KWin's engine, rather than a disk QML plugin.
            modules = ['org/kde/plasma/plasma5support']
            if panel:
                modules.append('org/kde/taskmanager')
            for module in modules:
                if not (qml / module / 'qmldir').is_file():
                    errors.append('Missing QML module: ' + module.replace('/', '.'))
        except (ImportError, RuntimeError, OSError) as error:
            errors.append('Cannot locate Qt QML modules: ' + str(error))
    if 'gdbus' not in missing:
        try:
            info = api.kwin('/KWin', 'org.kde.KWin.supportInformation')
            version = re.search(r'KWin version: (\d+)\.(\d+)', info)
            if not version or int(version[1]) != 6 or (full and int(version[2]) < 7):
                errors.append('Requires Plasma 6.7+ for the full setup, or Plasma 6 for appearance only.')
            for service, path, method in [
                ('org.kde.plasmashell', '/PlasmaShell', 'org.freedesktop.DBus.Peer.Ping'),
                ('org.kde.kded6', '/kded', 'org.freedesktop.DBus.Peer.Ping'),
            ]:
                api.dbus(service, path, method)
            if full:
                api.dbus('org.kde.kglobalaccel', '/kglobalaccel', 'org.freedesktop.DBus.Peer.Ping')
                api.dbus('org.kde.keyboard', '/Layouts', 'org.freedesktop.DBus.Peer.Ping')
                if panel:
                    reply = api.dbus('org.kde.plasmashell', '/PlasmaShell', 'org.kde.PlasmaShell.evaluateScript',
                                     'print(JSON.stringify(knownWidgetTypes));')
                    widgets = json.loads(ast.literal_eval(reply)[0])
                    for widget in ['org.kde.plasma.taskmanager', 'org.kde.plasma.panelspacer',
                                   'org.kde.plasma.systemtray', 'org.kde.plasma.digitalclock']:
                        if widget not in widgets:
                            errors.append('Missing Plasma widget: ' + widget)
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


def require(api, options, full=False, with_wheel=False, panel=False):
    errors = problems(api, options, full, with_wheel, panel)
    if errors:
        raise RuntimeError('Preflight failed; no changes made:\n  - ' + '\n  - '.join(errors))
    if full:
        report_optional(options)


def report_optional(options):
    commands, warnings = applications.launchers(options, Path('runtime'))
    for warning in warnings:
        print('Optional: ' + warning)
    return commands
