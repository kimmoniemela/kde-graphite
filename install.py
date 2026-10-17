#!/usr/bin/env python3
"""Install selected KDE settings; never install a copy of somebody's ~/.config."""
import argparse
import ast
import configparser
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import uuid

import theme

ROOT = Path(__file__).resolve().parent
SCRIPTS = ('krohnkite', 'kde-hypr-bridge', 'kde-hypr-launchers-v2', 'graphite-window-controls')
WHEEL = 'kwin_hypr_scroll_desktop'
KEYS = {
    'Terminal': 'Meta+Return', 'Files': 'Meta+E', 'Editor': 'Meta+T',
    'Calculator': 'Meta+C', 'CalculatorKey': 'Calculator', 'Browser': 'Meta+W',
    'Launcher': 'Meta+Space', 'Settings': 'Meta+Z', 'Emoji': 'Meta+.',
    'ProcessMonitor': 'Ctrl+Shift+Esc', 'SessionMenu': 'Meta+Alt+C',
    'Wallpaper': 'Meta+Shift+W', 'ColorPicker': 'Meta+P',
    'ScreenshotRegion': 'Print', 'ScreenshotFull': 'Meta+Print',
}


def run(*args):
    result = subprocess.run(args, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f'{args[0]} failed')
    return result.stdout.strip()


def dbus(dest, path, method, *args):
    return run('gdbus', 'call', '--session', '--dest', dest, '--object-path', path, '--method', method, *args)


def kwin(path, method, *args):
    return dbus('org.kde.KWin', path, method, *args)


def read_config(path):
    config = configparser.ConfigParser(interpolation=None, strict=False)
    config.optionxform = str
    config.read(path)
    return config


def merge_config(path, groups):
    config = read_config(path)
    for group, values in groups.items():
        if not config.has_section(group):
            config.add_section(group)
        config[group].update({key: str(value) for key, value in values.items()})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w') as handle:
        config.write(handle, space_around_delimiters=False)


def settings(path=None):
    result = json.loads((ROOT / 'settings.json').read_text())
    if path:
        local = json.loads(Path(path).read_text())
        result['applications'].update(local.pop('applications', {}))
        result.update(local)
    for name, argv in result['applications'].items():
        if not isinstance(argv, list) or not argv or not all(isinstance(s, str) and s for s in argv):
            raise ValueError(f'applications.{name} must be a nonempty argument array')
    if not 20 <= result['panel_height'] <= 64:
        raise ValueError('panel_height must be between 20 and 64')
    return result


def payload(options, data):
    """Render portable templates for one user's XDG data directory."""
    files = theme.payload(options, data)
    runtime = data / 'kde-graphite/runtime'
    for directory in ['assets/color-schemes', 'assets/konsole']:
        for source in (ROOT / directory).iterdir():
            files[data / Path(directory).name / source.name] = source.read_bytes()
    for source in (ROOT / 'scripts').glob('*.py'):
        files[runtime / source.name] = source.read_bytes()
    commands = dict(options['applications'])
    commands['CalculatorKey'] = commands['Calculator']
    commands.update({
        'Launcher': ['krunner'], 'Settings': ['systemsettings'], 'Emoji': ['plasma-emojier'],
        'SessionMenu': ['gdbus', 'call', '--session', '--dest', 'org.kde.LogoutPrompt',
                        '--object-path', '/LogoutPrompt', '--method', 'org.kde.LogoutPrompt.promptAll'],
        'Wallpaper': [sys.executable, str(runtime / 'wallpaper-settings.py')],
        'ColorPicker': [sys.executable, str(runtime / 'pick-color.py')],
        'ScreenshotRegion': ['spectacle', '--region'], 'ScreenshotFull': ['spectacle', '--fullscreen'],
    })
    files[runtime / 'launchers.json'] = (json.dumps(commands, indent=2) + '\n').encode()
    for source in (ROOT / 'widgets').rglob('*'):
        if source.is_file() and '__pycache__' not in source.parts:
            files[data / 'plasma/plasmoids' / source.relative_to(ROOT / 'widgets')] = source.read_bytes()
    scripts = data / 'kwin/scripts'
    for source in (ROOT / 'vendor/krohnkite').rglob('*'):
        if source.is_file():
            files[scripts / 'krohnkite' / source.relative_to(ROOT / 'vendor/krohnkite')] = source.read_bytes()
    # Qt caches imported JavaScript by URL for the lifetime of the session.
    # Version the entry point and imported module so updates work without logout.
    krohnkite = scripts / 'krohnkite'
    script = files[krohnkite / 'contents/code/script.js']
    main_qml = files[krohnkite / 'contents/ui/main.qml']
    version = hashlib.sha256(script + main_qml).hexdigest()[:12]
    files[krohnkite / f'contents/code/script-{version}.js'] = script
    files[krohnkite / f'contents/ui/main-{version}.qml'] = main_qml.replace(b'../code/script.js', f'../code/script-{version}.js'.encode())
    metadata_path = krohnkite / 'metadata.json'
    metadata = json.loads(files[metadata_path])
    metadata['X-Plasma-MainScript'] = f'ui/main-{version}.qml'
    files[metadata_path] = (json.dumps(metadata, indent=2) + '\n').encode()
    for name, api, main in [('kde-hypr-bridge', 'javascript', 'code/main.js'),
                            ('kde-hypr-launchers-v2', 'declarativescript', 'ui/main.qml')]:
        metadata = {'KPackageStructure': 'KWin/Script', 'KPlugin': {'Id': name,
            'Name': 'Graphite workspaces' if api == 'javascript' else 'Graphite application shortcuts',
            'Version': '1.0', 'License': 'MIT'}, 'X-Plasma-API': api, 'X-Plasma-MainScript': main}
        files[scripts / name / 'metadata.json'] = (json.dumps(metadata, indent=2) + '\n').encode()
    files[scripts / 'kde-hypr-bridge/contents/code/main.js'] = (ROOT / 'templates/workspaces.js').read_bytes()
    qml = (ROOT / 'templates/launchers.qml').read_text()
    prefix = shlex.join([sys.executable, str(runtime / 'launch-app.py')])
    handlers = []
    for name, sequence in KEYS.items():
        handlers.append('    ShortcutHandler { name: ' + json.dumps('KdeHyprLaunch' + name)
            + '; text: ' + json.dumps('Graphite: ' + name) + '; sequence: ' + json.dumps(sequence)
            + '; onActivated: runner.exec(' + json.dumps(name) + ') }')
    qml = qml.replace('@@COMMAND_PREFIX@@', json.dumps(prefix)).replace('@@SHORTCUT_HANDLERS@@', '\n'.join(handlers))
    files[scripts / 'kde-hypr-launchers-v2/contents/ui/main.qml'] = qml.encode()
    return files


class Backup:
    def __init__(self, state):
        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6]
        self.path = state / 'kde-graphite/backups' / stamp
        self.path.mkdir(parents=True)
        self.files = []

    def save(self, paths):
        known = {entry['path'] for entry in self.files}
        for path in paths:
            path = Path(path)
            if str(path) in known:
                continue
            if path.is_symlink():
                raise RuntimeError(f'Refusing to replace symlink: {path}')
            entry = {'path': str(path), 'existed': path.exists(), 'copy': str(len(self.files))}
            if path.exists():
                shutil.copy2(path, self.path / entry['copy'])
            self.files.append(entry)
            known.add(str(path))
            self.flush()

    def flush(self):
        (self.path / 'manifest.json').write_text(json.dumps(self.files, indent=2) + '\n')


def protected_hashes(config):
    # Exclude dconf: running applications can legitimately update its database.
    names = ['hypr', 'sway', 'i3', 'waybar', 'noctalia', 'gtk-3.0', 'gtk-4.0', 'qt5ct', 'qt6ct']
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
            for name in names for path in (config / name).rglob('*') if path.is_file()}


def one_shot(code, data):
    path = data / 'kde-graphite/runtime/operation.js'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(code)
    name = 'graphite-operation-' + uuid.uuid4().hex
    index = ast.literal_eval(kwin('/Scripting', 'org.kde.kwin.Scripting.loadScript', str(path), name))[0]
    try:
        kwin(f'/Scripting/Script{index}', 'org.kde.kwin.Script.run')
    finally:
        kwin('/Scripting', 'org.kde.kwin.Scripting.unloadScript', name)


def restore_window_decorations(data):
    """Restore normal titlebars after unloading the tiler."""
    path = data / 'kde-graphite/runtime/restore-decorations.qml'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("""import QtQuick
import org.kde.kwin
Item {
    Component.onCompleted: {
        for (const window of Workspace.stackingOrder) {
            if (window.normalWindow && !window.specialWindow && !window.fullScreen)
                window.noBorder = false;
        }
    }
}
""")
    name = 'graphite-restore-decorations-' + uuid.uuid4().hex
    index = ast.literal_eval(kwin('/Scripting', 'org.kde.kwin.Scripting.loadDeclarativeScript', str(path), name))[0]
    try:
        kwin(f'/Scripting/Script{index}', 'org.kde.kwin.Script.run')
        import time
        # Declarative scripts load asynchronously; keep the helper alive through completion.
        time.sleep(1)
    finally:
        kwin('/Scripting', 'org.kde.kwin.Scripting.unloadScript', name)


def shortcut_ids():
    result = json.loads((ROOT / 'shortcuts.json').read_text())
    return {('kwin', key): value for key, value in result.items()}


def clear_conflicts(bindings):
    from PySide6.QtGui import QKeySequence
    base = ('org.kde.kglobalaccel', '/kglobalaccel')
    for component, name, sequences in bindings:
        for sequence in sequences.split(';'):
            if not sequence:
                continue
            key = QKeySequence(sequence)[0].toCombined()
            reply = dbus(*base, 'org.kde.KGlobalAccel.action', str(key))
            owner = ast.literal_eval(re.sub(r'@as\s*', '', reply))[0]
            if owner and owner[:2] != [component, name]:
                dbus(*base, 'org.kde.KGlobalAccel.setShortcut', json.dumps(owner), '[]', '4')


def native_shortcuts():
    from PySide6.QtGui import QKeySequence
    for (component, name), sequences in shortcut_ids().items():
        if name.startswith('Krohnkite'):
            continue  # Real QML handlers register these on script startup.
        keys = [QKeySequence(s)[0].toCombined() for s in sequences.split(';') if s]
        ids = json.dumps([component, name, 'KWin', name])
        dbus('org.kde.kglobalaccel', '/kglobalaccel', 'org.kde.KGlobalAccel.setShortcut', ids, json.dumps(keys), '4')


def workspace_shortcuts():
    return [('kwin', 'KdeHypr' + prefix + str(n), modifier + str(n % 10))
            for prefix, modifier in [('Desktop', 'Meta+'), ('SendDesktop', 'Meta+Shift+')]
            for n in range(1, 11)]


def set_workspace_shortcuts():
    from PySide6.QtGui import QKeySequence
    # Explicitly update saved bindings too, including upgrades from disabled actions.
    for component, name, sequence in workspace_shortcuts():
        ids = json.dumps([component, name, 'KWin', 'Graphite: ' + name])
        keys = [QKeySequence(sequence)[0].toCombined()]
        dbus('org.kde.kglobalaccel', '/kglobalaccel', 'org.kde.KGlobalAccel.setShortcut', ids, json.dumps(keys), '4')


def tray_ids():
    def strings(value):
        return [ast.literal_eval(m.group()) for m in re.finditer(r"'(?:[^'\\]|\\.)*'", value)]
    try:
        items = strings(dbus('org.kde.StatusNotifierWatcher', '/StatusNotifierWatcher',
            'org.freedesktop.DBus.Properties.Get', 'org.kde.StatusNotifierWatcher', 'RegisteredStatusNotifierItems'))
    except RuntimeError:
        return []
    result = []
    for item in items:
        service, _, path = item.partition('/')
        try:
            result += strings(dbus(service, '/' + path, 'org.freedesktop.DBus.Properties.Get', 'org.kde.StatusNotifierItem', 'Id'))
        except RuntimeError:
            pass
    return result


def preflight(with_wheel=True):
    if 'KDE' not in os.environ.get('XDG_CURRENT_DESKTOP', '').split(':') or not os.environ.get('WAYLAND_DISPLAY'):
        raise RuntimeError('Run this from a KDE Plasma Wayland session.')
    for executable in ['gdbus', 'kwriteconfig6', 'systemctl', 'fc-list', 'kscreen-doctor']:
        if not shutil.which(executable):
            raise RuntimeError(f'Missing executable: {executable}')
    from PySide6.QtGui import QKeySequence  # noqa: F401
    info = kwin('/KWin', 'org.kde.KWin.supportInformation')
    version = re.search(r'KWin version: (\d+)\.(\d+)', info)
    if not version or int(version[1]) != 6 or int(version[2]) < 7:
        raise RuntimeError('Requires KWin 6.7 or later in the Plasma 6 series.')
    if with_wheel and kwin('/Effects', 'org.kde.kwin.Effects.isEffectSupported', WHEEL) != '(true,)':
        raise RuntimeError('Build and install wheel/ first, or pass --without-wheel.')


def resolve_outputs(options):
    """Use KDE's display priority, with explicit names taking precedence."""
    options = dict(options)
    outputs = json.loads(run('kscreen-doctor', '-j'))['outputs']
    outputs = sorted((o for o in outputs if o['enabled'] and o['connected']), key=lambda o: o['priority'])
    if not options['primary_output'] and outputs:
        options['primary_output'] = outputs[0]['name']
    if not options['secondary_output']:
        options['secondary_output'] = next((o['name'] for o in outputs if o['name'] != options['primary_output']), options['primary_output'])
    return options


def apply(options, config, data, state, with_wheel=True, panel=True):
    preflight(with_wheel)
    options = resolve_outputs(options)
    families = run('fc-list', ':', 'family')
    if options['font'] not in families:
        options['font'] = 'Fira Code' if 'Fira Code' in families else 'monospace'
    files = payload(options, data)
    fragments = json.loads((ROOT / 'config.json').read_text())
    fragments['kwinrc']['Plugins'][WHEEL + 'Enabled'] = str(with_wheel).lower()
    fragments['kwinrc']['Script-kde-hypr-bridge'] = {
        'PrimaryOutput': options['primary_output'], 'SecondaryOutput': options['secondary_output']}
    palette = read_config(ROOT / 'assets/color-schemes/TerminalGraphite.colors')
    fragments['kdeglobals'] = {group: dict(palette[group]) for group in palette.sections() if group != 'General'}
    fonts = theme.font_values(options)
    fragments['kdeglobals'].update({'General': {'ColorScheme': 'TerminalGraphite', **fonts['General']},
        'KDE': {'LookAndFeelPackage': theme.THEME_ID, 'widgetStyle': 'Breeze', 'AnimationDurationFactor': '0'}, 'Icons': {'Theme': 'breeze-dark'}})
    fragments['kdeglobals']['WM'].update(fonts['WM'])
    fragments['kwinrc']['Desktops'] = {'Number': '5', 'Rows': '1', **{f'Name_{n}': str(n) for n in range(1, 6)}}
    fragments['plasmarc'] = {'Theme': {'name': 'default'}}
    before = protected_hashes(config)
    backup = Backup(state)
    backup.save([config / name for name in set(fragments) | {'kglobalshortcutsrc', 'plasmashellrc',
        'plasma-org.kde.plasma.desktop-appletsrc'}] + [config / 'kdedefaults/package'] + list(files))
    print(f'Backup: {backup.path}', flush=True)
    # Stop KDE's GTK synchronizer before changing any palette values.
    dbus('org.kde.kded6', '/kded', 'org.kde.kded6.setModuleAutoloading', 'gtkconfig', 'false')
    dbus('org.kde.kded6', '/kded', 'org.kde.kded6.unloadModule', 'gtkconfig')
    for name in SCRIPTS:
        kwin('/Scripting', 'org.kde.kwin.Scripting.unloadScript', name)
    bindings = [(c, n, seq) for (c, n), seq in shortcut_ids().items()]
    bindings += [('kwin', 'KdeHyprLaunch' + name, seq) for name, seq in KEYS.items()]
    bindings += workspace_shortcuts()
    bindings += [('plasmashell', 'graphite-notifications', 'Meta+A'), ('plasmashell', 'graphite-tray', 'Meta+X')]
    clear_conflicts(bindings)
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    for name, groups in fragments.items():
        merge_config(config / name, groups)
    (config / 'kdedefaults').mkdir(parents=True, exist_ok=True)
    (config / 'kdedefaults/package').write_text(theme.THEME_ID + '\n')
    shortcut_groups = {'kwin': {name: (seq.replace(';', '\\t') or 'none') + ',none,Graphite: ' + name
                               for (component, name), seq in shortcut_ids().items()}}
    merge_config(config / 'kglobalshortcutsrc', shortcut_groups)
    native_shortcuts()
    one_shot((ROOT / 'templates/five-desktops.js').read_text(), data)
    kwin('/KWin', 'org.kde.KWin.reconfigure')
    kwin('/Scripting', 'org.kde.kwin.Scripting.start')
    set_workspace_shortcuts()
    if with_wheel:
        if kwin('/Effects', 'org.kde.kwin.Effects.isEffectLoaded', WHEEL) != '(true,)':
            assert kwin('/Effects', 'org.kde.kwin.Effects.loadEffect', WHEEL) == '(true,)'
    if panel:
        script = (ROOT / 'templates/panel.js').read_text().replace('@@PANEL_HEIGHT@@', str(options['panel_height']))
        script = script.replace('@@APPLICATION_TRAY_IDS@@', json.dumps(tray_ids()))
        script = script.replace('@@PRIMARY_OUTPUT@@', json.dumps(options['primary_output']))
        result = dbus('org.kde.plasmashell', '/PlasmaShell', 'org.kde.PlasmaShell.evaluateScript', script)
        if any(error in result for error in ['Error:', 'TypeError', 'ReferenceError']):
            raise RuntimeError(result)
        import time
        time.sleep(1)
        applets = config / 'plasma-org.kde.plasma.desktop-appletsrc'
        current = read_config(applets)
        notification_shortcut = 'Meta+A'
        for section in current.sections():
            if current[section].get('plugin') == 'org.kde.plasma.notifications':
                merge_config(applets, {section + '][Shortcuts': {'global': notification_shortcut}})
                notification_shortcut = ''
        run('systemctl', '--user', 'restart', 'plasma-plasmashell.service')
    if before != protected_hashes(config):
        raise RuntimeError(f'A protected desktop config changed during installation. Backup: {backup.path}')
    (state / 'kde-graphite/latest-backup').write_text(str(backup.path) + '\n')
    check(with_wheel)
    print('Installed. Log out and back into KDE to reload fonts and remaining settings.')


def check(with_wheel=True):
    for name in SCRIPTS:
        loaded = kwin('/Scripting', 'org.kde.kwin.Scripting.isScriptLoaded', name) == '(true,)'
        expected = True  # The tiler stays loaded while its runtime mode is off.
        if loaded != expected:
            raise RuntimeError(f'Script state does not match configuration: {name}')
    count = kwin('/VirtualDesktopManager', 'org.freedesktop.DBus.Properties.Get', 'org.kde.KWin.VirtualDesktopManager', 'count')
    if 'uint32 5' not in count:
        raise RuntimeError('Expected five native desktops')
    if with_wheel and kwin('/Effects', 'org.kde.kwin.Effects.isEffectLoaded', WHEEL) != '(true,)':
        raise RuntimeError('Workspace wheel effect is not loaded')
    from PySide6.QtGui import QKeySequence
    for name, sequence in KEYS.items():
        ids = json.dumps(['kwin', 'KdeHyprLaunch' + name, 'KWin', 'Graphite: ' + name])
        actual = dbus('org.kde.kglobalaccel', '/kglobalaccel', 'org.kde.KGlobalAccel.shortcut', ids)
        if str(QKeySequence(sequence)[0].toCombined()) not in actual:
            raise RuntimeError(f'Shortcut is not registered: {sequence}')
    for component, name, sequence in workspace_shortcuts():
        key = QKeySequence(sequence)[0].toCombined()
        reply = dbus('org.kde.kglobalaccel', '/kglobalaccel', 'org.kde.KGlobalAccel.action', str(key))
        owner = ast.literal_eval(re.sub(r'@as\s*', '', reply))[0]
        if owner[:2] != [component, name]:
            raise RuntimeError(f'Workspace shortcut has the wrong handler: {sequence}')
    print('Scripts, five desktops, 15 application shortcuts and 20 workspace shortcuts verified.')


def restore(path):
    for name in SCRIPTS:
        kwin('/Scripting', 'org.kde.kwin.Scripting.unloadScript', name)
    kwin('/Effects', 'org.kde.kwin.Effects.unloadEffect', WHEEL)
    run('systemctl', '--user', 'stop', 'plasma-plasmashell.service')
    try:
        restore_files(path)
    finally:
        run('systemctl', '--user', 'start', 'plasma-plasmashell.service')
    kwin('/KWin', 'org.kde.KWin.reconfigure')
    print('Settings restored. Log out and back into KDE to reload all shortcut registrations.')


def restore_files(path):
    for entry in json.loads((path / 'manifest.json').read_text()):
        target = Path(entry['path'])
        if entry['existed']:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path / entry['copy'], target)
        elif target.exists():
            target.unlink()


def tiling_control():
    import importlib.util
    spec = importlib.util.spec_from_file_location('graphite_tiling', ROOT / 'scripts/tiling-control.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', nargs='?', default='install', choices=['install', 'theme', 'build-theme', 'check', 'restore', 'tiling'])
    parser.add_argument('value', nargs='?')
    parser.add_argument('--settings', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--without-wheel', action='store_true')
    parser.add_argument('--no-panel', action='store_true')
    args = parser.parse_args()
    home = Path.home()
    config = Path(os.environ.get('XDG_CONFIG_HOME', home / '.config'))
    data = Path(os.environ.get('XDG_DATA_HOME', home / '.local/share'))
    state = Path(os.environ.get('XDG_STATE_HOME', home / '.local/state'))
    if args.command == 'install':
        options = settings(args.settings)
        if args.dry_run:
            print(f'Would install {len(payload(options, data))} asset/script files under {data}.')
            print(f'Would merge selected KDE settings under {config}; configure a top bar per connected monitor; use five desktops per output.')
            print('Would back up touched files and leave other desktop configs unchanged. No changes made.')
        else:
            apply(options, config, data, state, not args.without_wheel, not args.no_panel)
    elif args.command == 'theme':
        options = settings(args.settings)
        if args.dry_run:
            print(f'Would install Graphite under {data / "plasma/look-and-feel" / theme.THEME_ID}.')
            print('Would apply appearance and lock-screen settings; retain panels, workspaces, shortcuts and tiling.')
        else:
            theme.install_theme(options, config, data, state, sys.modules[__name__])
    elif args.command == 'build-theme':
        destination = Path(args.value) if args.value else ROOT / 'build/Graphite-1.0.0.tar.gz'
        if args.dry_run:
            print(f'Would build {destination}.')
        else:
            print(theme.build_archive(destination))
    elif args.command == 'check':
        check(not args.without_wheel)
    elif args.command == 'restore':
        path = Path(args.value) if args.value else Path((state / 'kde-graphite/latest-backup').read_text().strip())
        restore(path)
    else:
        if args.value not in ['on', 'off', 'toggle']:
            parser.error('Use: install.py tiling on|off|toggle')
        active = tiling_control().change(args.value)
        if not active:
            restore_window_decorations(data)
        print('Automatic tiling ' + ('on' if active else 'off') + '.')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, OSError) as error:
        print(f'Error: {error}', file=sys.stderr)
        sys.exit(1)
