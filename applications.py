"""Resolve desktop defaults and optional applications without installing anything."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

DEFAULT = ['@default']
CANDIDATES = {
    'Terminal': ['konsole', 'xterm'],
    'Files': ['dolphin', 'nautilus', 'thunar'],
    'Editor': ['kwrite', 'kate', 'gnome-text-editor', 'mousepad'],
    'Browser': ['firefox', 'chromium', 'google-chrome', 'falkon'],
    'Calculator': ['kcalc', 'gnome-calculator', 'qalculate-gtk'],
    'ProcessMonitor': ['plasma-systemmonitor', 'gnome-system-monitor'],
}


def query(*args):
    try:
        return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL, timeout=5).strip()
    except (OSError, subprocess.SubprocessError):
        return ''


def preference(key):
    return query('kreadconfig6', '--file', 'kdeglobals', '--group', 'General', '--key', key)


def desktop_command(service):
    """Let KDE expand Exec field codes and perform desktop activation."""
    filename = service if service.endswith('.desktop') else service + '.desktop'
    roots = [Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share')]
    roots += [Path(p) for p in (os.environ.get('XDG_DATA_DIRS') or '/usr/local/share:/usr/share').split(':') if p]
    if not any((root / 'applications' / filename).is_file() for root in roots):
        return None
    # kstart looks up a desktop entry name, without the .desktop suffix.
    return ['kstart', '--application', filename[:-len('.desktop')]]


def default_command(name):
    if name == 'Terminal':
        service = preference('TerminalService')
        if service:
            return desktop_command(service)
        command = shlex.split(preference('TerminalApplication'))
        if command:
            return command
    elif name == 'Browser':
        service = preference('BrowserApplication')
        if service:
            return shlex.split(service[1:]) if service.startswith('!') else desktop_command(service)
    mime = {'Browser': 'x-scheme-handler/https', 'Files': 'inode/directory', 'Editor': 'text/plain'}.get(name)
    if mime and shutil.which('xdg-mime'):
        service = query('xdg-mime', 'query', 'default', mime)
        if service:
            return desktop_command(service)
    return next(([app] for app in CANDIDATES[name] if shutil.which(app)), None)


def launchers(options, runtime):
    """Keep defaults dynamic; omit unavailable optional apps from shortcut handlers."""
    commands, warnings = {}, []
    for name, argv in options['applications'].items():
        if not argv:
            continue
        if argv == DEFAULT and not default_command(name):
            warnings.append(name + ': no installed application found; shortcut skipped.')
        else:
            commands[name] = argv
    if 'Calculator' in commands:
        commands['CalculatorKey'] = commands['Calculator']
    for name, argv in {
        'Launcher': ['krunner'], 'Settings': ['systemsettings'], 'Emoji': ['plasma-emojier'],
        'ScreenshotRegion': ['spectacle', '--region'], 'ScreenshotFull': ['spectacle', '--fullscreen'],
    }.items():
        if shutil.which(argv[0]):
            commands[name] = argv
        else:
            warnings.append(name + ': ' + argv[0] + ' is unavailable; shortcut skipped.')
    commands.update({
        'SessionMenu': ['gdbus', 'call', '--session', '--dest', 'org.kde.LogoutPrompt',
                        '--object-path', '/LogoutPrompt', '--method', 'org.kde.LogoutPrompt.promptAll'],
        'Wallpaper': [sys.executable, str(runtime / 'wallpaper-settings.py')],
    })
    if shutil.which('wl-copy'):
        commands['ColorPicker'] = [sys.executable, str(runtime / 'pick-color.py')]
    else:
        warnings.append('ColorPicker: wl-copy is unavailable; shortcut skipped.')
    return commands, warnings
