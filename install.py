#!/usr/bin/env python3
"""Install selected KDE settings; never install a copy of somebody's ~/.config."""
import argparse
from contextlib import contextmanager
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
import tempfile
import uuid

import theme
import doctor
import applications

ROOT = Path(__file__).resolve().parent
SCRIPTS = ('kde-hypr-bridge', 'kde-hypr-launchers-v2')
RUNTIME_SCRIPTS = ('launch-app.py', 'workspace-keys.py')
# Upgrade cleanup applies only to these retired Graphite utilities.
RETIRED_UTILITIES = {'Wallpaper': 'wallpaper-settings.py', 'ColorPicker': 'pick-color.py'}
WHEEL = 'kwin_hypr_scroll_desktop'
KEYS = {
    'Terminal': 'Meta+Return', 'Files': 'Meta+E', 'Editor': 'Meta+T',
    'Calculator': 'Meta+C', 'CalculatorKey': 'Calculator', 'Browser': 'Meta+W',
    'Launcher': 'Meta+Space', 'Settings': 'Meta+Z', 'Emoji': 'Meta+.',
    'ProcessMonitor': 'Ctrl+Shift+Esc', 'SessionMenu': 'Meta+Alt+C',
    'ScreenshotRegion': 'Print', 'ScreenshotFull': 'Meta+Print',
}


def run(*args, timeout=20):
    try:
        result = subprocess.run(args, text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f'Command timed out: {args[0]}') from None
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f'{args[0]} failed')
    return result.stdout.strip()


def xdg_path(variable, default):
    path = Path(os.environ.get(variable) or default)
    if not path.is_absolute():
        raise ValueError(variable + ' must be an absolute path, or unset')
    return path


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
    """Change selected KConfig entries without rewriting unrelated text or groups."""
    remaining = {group: dict(values) for group, values in groups.items()}
    lines, current = [], None

    def append_missing(group):
        values = remaining.get(group, {})
        if values:
            if lines and not lines[-1].endswith('\n'):
                lines[-1] += '\n'
            lines.extend(f'{key}={value}\n' for key, value in values.items())
            values.clear()

    for line in (path.read_text().splitlines(keepends=True) if path.exists() else []):
        stripped = line.strip()
        if stripped.startswith('[') and stripped.endswith(']'):
            append_missing(current)
            current = stripped[1:-1]
            if current.endswith('][$i') and current[:-4] in groups:
                raise RuntimeError(f'KConfig group is locked: {path}: {current}')
        elif current in groups and '=' in line and not stripped.startswith(('#', ';')):
            key = line.split('=', 1)[0].strip()
            base = re.sub(r'\[\$[edi]+\]', '', key)
            if base in groups[current]:
                if '[$i]' in key:
                    raise RuntimeError(f'KConfig entry is locked: {path}: {key}')
                line = f'{base}={groups[current][base]}\n'
                remaining[current].pop(base, None)
        lines.append(line)
    append_missing(current)
    for group, values in remaining.items():
        if values:
            if lines and not lines[-1].endswith('\n'):
                lines[-1] += '\n'
            lines.append(f'\n[{group}]\n')
            append_missing(group)
    atomic_write(path, ''.join(lines).encode())


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        temporary_path.write_bytes(content)
        if path.exists():
            temporary_path.chmod(path.stat().st_mode & 0o777)
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def atomic_copy(source, target):
    """Replace a file without truncating a library mapped by a running process."""
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        shutil.copy2(source, temporary_path)
        temporary_path.replace(target)
    finally:
        temporary_path.unlink(missing_ok=True)


def retire_utilities(config, data):
    """Remove only Graphite's retired utility files and shortcut registrations."""
    for filename in RETIRED_UTILITIES.values():
        (data / 'kde-graphite/runtime' / filename).unlink(missing_ok=True)
    path = config / 'kglobalshortcutsrc'
    if not path.exists():
        return
    actions = {'KdeHyprLaunch' + name for name in RETIRED_UTILITIES}
    lines, group = [], None
    for line in path.read_text().splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith('[') and stripped.endswith(']'):
            group = stripped[1:-1]
        key = line.split('=', 1)[0].strip()
        name = re.sub(r'\[\$[edi]+\]', '', key)
        if group in ('kwin', 'kwin][$i') and name in actions:
            if '[$i]' in group or '[$i]' in key:
                raise RuntimeError(f'KConfig shortcut is locked: {path}: {key}')
            ids = json.dumps(['kwin', name, 'KWin', 'Graphite: ' + name])
            dbus('org.kde.kglobalaccel', '/kglobalaccel', 'org.kde.KGlobalAccel.setShortcut', ids, '[]', '4')
            continue
        lines.append(line)
    atomic_write(path, ''.join(lines).encode())


def settings(path=None):
    result = json.loads((ROOT / 'settings.json').read_text())
    if path:
        local = json.loads(Path(path).read_text())
        if not isinstance(local, dict):
            raise ValueError('settings must contain a JSON object')
        unknown = set(local) - set(result)
        if unknown:
            raise ValueError('Unknown settings: ' + ', '.join(sorted(unknown)))
        if not isinstance(local.get('applications', {}), dict):
            raise ValueError('applications must be an object of command arrays')
        unknown_apps = set(local.get('applications', {})) - set(result['applications'])
        if unknown_apps:
            raise ValueError('Unknown applications: ' + ', '.join(sorted(unknown_apps)))
        result['applications'].update(local.pop('applications', {}))
        result.update(local)
    for name, argv in result['applications'].items():
        if not isinstance(argv, list) or not all(isinstance(s, str) and s and '\x00' not in s for s in argv):
            raise ValueError(f'applications.{name} must be an argument array; use [] to disable it')
        if any(s.startswith('@') for s in argv) and argv != applications.DEFAULT:
            raise ValueError(f'applications.{name}: use ["@default"] or an explicit command array')
    if not isinstance(result['panel_height'], int) or not 20 <= result['panel_height'] <= 64:
        raise ValueError('panel_height must be between 20 and 64')
    if not all(isinstance(result[role], str) for role in ['primary_output', 'secondary_output']):
        raise ValueError('output names must be strings; use an empty string for automatic detection')
    if not isinstance(result['font'], str) or not result['font'] or any(c in result['font'] for c in ',\n\r'):
        raise ValueError('font must be a family name without commas or line breaks')
    if not isinstance(result['font_size'], (int, float)) or not 6 <= result['font_size'] <= 32:
        raise ValueError('font_size must be between 6 and 32')
    return result


def payload(options, data, panel=False):
    """Render portable templates for one user's XDG data directory."""
    files = theme.payload(options, data)
    runtime = data / 'kde-graphite/runtime'
    for name in RUNTIME_SCRIPTS:
        files[runtime / name] = (ROOT / 'scripts' / name).read_bytes()
    files[runtime / 'applications.py'] = (ROOT / 'applications.py').read_bytes()
    commands, _ = applications.launchers(options)
    files[runtime / 'launchers.json'] = (json.dumps(commands, indent=2) + '\n').encode()
    for source in ((ROOT / 'widgets').rglob('*') if panel else []):
        if source.is_file() and '__pycache__' not in source.parts:
            files[data / 'plasma/plasmoids' / source.relative_to(ROOT / 'widgets')] = source.read_bytes()
    scripts = data / 'kwin/scripts'
    for name, api, main in [('kde-hypr-bridge', 'javascript', 'code/main.js'),
                            ('kde-hypr-launchers-v2', 'declarativescript', 'ui/main.qml')]:
        metadata = {'KPackageStructure': 'KWin/Script', 'KPlugin': {'Id': name,
            'Name': 'Graphite workspaces' if api == 'javascript' else 'Graphite application shortcuts',
            'Version': '1.0', 'License': 'MIT'}, 'X-Plasma-API': api, 'X-Plasma-MainScript': main}
        files[scripts / name / 'metadata.json'] = (json.dumps(metadata, indent=2) + '\n').encode()
    files[scripts / 'kde-hypr-bridge/contents/code/main.js'] = (ROOT / 'templates/workspaces.js').read_bytes()
    qml = (ROOT / 'templates/launchers.qml').read_text()
    prefix = shlex.join([sys.executable, str(runtime / 'launch-app.py')])
    qml = qml.replace('@@WORKSPACE_KEYS_COMMAND@@', json.dumps(shlex.join([sys.executable, str(runtime / 'workspace-keys.py')])))
    handlers = []
    for name, sequence in KEYS.items():
        if name not in commands:
            continue
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
        self.path.mkdir(parents=True, mode=0o700)
        self.pointer = state / 'kde-graphite/latest-backup'
        self.previous = self.pointer.read_text() if self.pointer.exists() else ''
        (self.path / 'previous-backup').write_text(self.previous)
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
        atomic_write(self.path / 'manifest.json', (json.dumps(self.files, indent=2) + '\n').encode())


@contextmanager
def transaction(backup):
    """Recover saved files after any failed mutation; keep the failure backup."""
    atomic_write(backup.pointer, (str(backup.path) + '\n').encode())
    try:
        yield
    except BaseException:
        try:
            restore_files(backup.path)
            if backup.previous:
                atomic_write(backup.pointer, backup.previous.encode())
            else:
                backup.pointer.unlink(missing_ok=True)
        except Exception as rollback_error:
            print(f'Rollback failed: {rollback_error}. Restore manually from {backup.path}', file=sys.stderr)
        else:
            print(f'Installation failed; saved files restored. Backup: {backup.path}', file=sys.stderr)
            print('Log out and back in to reload any changed live KDE state.', file=sys.stderr)
        raise


def protected_hashes(config):
    # Exclude dconf: running applications can legitimately update its database.
    names = ['hypr', 'sway', 'i3', 'waybar', 'noctalia', 'gtk-3.0', 'gtk-4.0', 'qt5ct', 'qt6ct']
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
            for name in names for path in (config / name).rglob('*') if path.is_file()}


def shortcut_ids():
    return {('kwin', key): value for key, value in
            json.loads((ROOT / 'shortcuts.json').read_text()).items()}


def clear_conflicts(bindings):
    from PySide6.QtGui import QKeySequence
    base = ('org.kde.kglobalaccel', '/kglobalaccel')
    managed = set(shortcut_ids()) | {(c, n) for c, n, _ in workspace_shortcuts()}
    managed.update(('kwin', 'KdeHyprLaunch' + name) for name in KEYS)
    # These native defaults compete with Graphite's maximize and browser keys.
    native_defaults = {('kwin', 'Show Desktop'), ('kwin', 'Overview')}
    changes = {}
    for component, name, sequences in bindings:
        for sequence in sequences.split(';'):
            if not sequence:
                continue
            key = QKeySequence(sequence)[0].toCombined()
            reply = dbus(*base, 'org.kde.KGlobalAccel.action', str(key))
            owner = ast.literal_eval(re.sub(r'@as\s*', '', reply))[0]
            if owner and owner[:2] != [component, name]:
                if owner[0] == 'kwin' and tuple(owner[:2]) not in managed | native_defaults:
                    raise RuntimeError(f'{sequence} belongs to an unmanaged KWin action: {owner[1]}. '
                                       'Resolve the conflict in System Settings before installing.')
                reply = dbus(*base, 'org.kde.KGlobalAccel.shortcut', json.dumps(owner))
                current = ast.literal_eval(re.sub(r'@ai\s*', '', reply))[0]
                ids = json.dumps(owner)
                previous = changes.get(ids, current)
                changes[ids] = [code for code in previous if code != key]
    for ids, remaining in changes.items():
        dbus(*base, 'org.kde.KGlobalAccel.setShortcut', ids, json.dumps(remaining), '4')


def native_shortcuts():
    from PySide6.QtGui import QKeySequence
    for (component, name), sequences in shortcut_ids().items():
        keys = [QKeySequence(s)[0].toCombined() for s in sequences.split(';') if s]
        ids = json.dumps([component, name, 'KWin', name])
        dbus('org.kde.kglobalaccel', '/kglobalaccel', 'org.kde.KGlobalAccel.setShortcut', ids, json.dumps(keys), '4')


def workspace_shortcuts():
    bindings = [('kwin', 'KdeHypr' + prefix + str(n), modifier + str(n % 10))
            for prefix, modifier in [('Desktop', 'Meta+'), ('SendDesktop', 'Meta+Shift+')]
            for n in range(1, 11)]
    bindings += [('kwin', 'KdeHyprLocalDesktop' + str(n), 'Meta+Ctrl+' + str(n)) for n in range(1, 6)]
    bindings += [('kwin', 'KdeHypr' + name, sequence) for name, sequence in {
        'WorkspaceNext': 'Meta+Ctrl+Right', 'WorkspacePrev': 'Meta+Ctrl+Left',
        'SendNext': 'Meta+Ctrl+Shift+Right', 'SendPrev': 'Meta+Ctrl+Shift+Left',
        'Empty': 'Meta+Ctrl+Down', 'ScratchSend': 'Meta+Shift+S', 'ScratchToggle': 'Meta+S',
    }.items()]
    return bindings


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


def preflight(options, with_wheel=False, panel=False):
    doctor.require(sys.modules[__name__], options, full=True, with_wheel=with_wheel, panel=panel)


def restart_shell():
    """Use the Plasma systemd unit where available; support non-systemd sessions."""
    if shutil.which('systemctl'):
        try:
            if run('systemctl', '--user', 'show', 'plasma-plasmashell.service', '--property=LoadState', '--value') == 'loaded':
                run('systemctl', '--user', 'restart', 'plasma-plasmashell.service')
                return
        except RuntimeError:
            pass
    # Plasma rereads the restored layout on the next login on other session managers.
    print('Log out and back in to reload the panel layout.')


def resolve_outputs(options):
    """Use KDE's display priority, with explicit names taking precedence."""
    options = dict(options)
    outputs = json.loads(run('kscreen-doctor', '-j'))['outputs']
    outputs = sorted((o for o in outputs if o['enabled'] and o['connected']), key=lambda o: o['priority'])
    if not options['primary_output'] and outputs:
        options['primary_output'] = outputs[0]['name']
    if not options['secondary_output']:
        options['secondary_output'] = next((o['name'] for o in outputs if o['name'] != options['primary_output']), options['primary_output'])
    connected = {o['name'] for o in outputs}
    for role in ['primary_output', 'secondary_output']:
        if options[role] not in connected:
            raise ValueError(f'{role} is not a connected output: {options[role]}. Clear the setting to detect it automatically.')
    if len(outputs) > 2:
        raise ValueError('The full setup supports one or two connected monitors. Use the theme profile for other layouts.')
    return options


def apply(options, config, data, state, with_wheel=False, panel=False):
    preflight(options, with_wheel, panel)
    options = resolve_outputs(options)
    families = run('fc-list', ':', 'family')
    if options['font'] not in families:
        options['font'] = 'Fira Code' if 'Fira Code' in families else 'monospace'
    files = payload(options, data, panel=panel)
    launchers = json.loads(files[data / 'kde-graphite/runtime/launchers.json'])
    fragments = json.loads((ROOT / 'config.json').read_text())
    # Preserve the wheel state unless explicitly enabling the native effect.
    fragments['kwinrc']['Plugins'].pop(WHEEL + 'Enabled', None)
    if with_wheel:
        fragments['kwinrc']['Plugins'][WHEEL + 'Enabled'] = 'true'
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
    retired = [data / 'kde-graphite/runtime' / name for name in RETIRED_UTILITIES.values()]
    backup = Backup(state)
    backup.save([config / name for name in set(fragments) | {'kglobalshortcutsrc', 'plasmashellrc',
        'plasma-org.kde.plasma.desktop-appletsrc'}] + [config / 'kdedefaults/package'] + retired + list(files))
    print(f'Backup: {backup.path}', flush=True)
    with transaction(backup):
        # Stop KDE's GTK synchronizer before changing any palette values.
        dbus('org.kde.kded6', '/kded', 'org.kde.kded6.setModuleAutoloading', 'gtkconfig', 'false')
        dbus('org.kde.kded6', '/kded', 'org.kde.kded6.unloadModule', 'gtkconfig')
        bindings = [(c, n, seq) for (c, n), seq in shortcut_ids().items()]
        bindings += [('kwin', 'KdeHyprLaunch' + name, seq) for name, seq in KEYS.items() if name in launchers]
        bindings += workspace_shortcuts()
        if panel:
            bindings += [('plasmashell', 'graphite-notifications', 'Meta+A'), ('plasmashell', 'graphite-tray', 'Meta+X')]
        clear_conflicts(bindings)
        for path, content in files.items():
            atomic_write(path, content)
        for name, groups in fragments.items():
            merge_config(config / name, groups)
        retire_utilities(config, data)
        (config / 'kdedefaults').mkdir(parents=True, exist_ok=True)
        (config / 'kdedefaults/package').write_text(theme.THEME_ID + '\n')
        shortcut_groups = {'kwin': {name: (seq.replace(';', '\\t') or 'none') + ',none,Graphite: ' + name
                                   for (component, name), seq in shortcut_ids().items()}}
        for name, sequence in KEYS.items():
            shortcut_groups['kwin']['KdeHyprLaunch' + name] = (sequence if name in launchers else 'none') + ',none,Graphite: ' + name
        for component, name, sequence in workspace_shortcuts():
            shortcut_groups['kwin'][name] = sequence + ',none,Graphite: ' + name
        merge_config(config / 'kglobalshortcutsrc', shortcut_groups)
        native_shortcuts()
        # Load the new scripts at the next login. Unload/reload cycles have crashed Qt's GC.
        dbus('org.kde.plasmashell', '/PlasmaShell', 'org.kde.PlasmaShell.evaluateScript', theme.wallpaper_script(data))
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
            restart_shell()
        if before != protected_hashes(config):
            raise RuntimeError(f'A protected desktop config changed during installation. Backup: {backup.path}')
        print('Installed. Log out and back into KDE to activate scripts, workspaces and shortcuts. Then run: python3 install.py check')


def check(with_wheel=None):
    config = xdg_path('XDG_CONFIG_HOME', Path.home() / '.config')
    data = xdg_path('XDG_DATA_HOME', Path.home() / '.local/share')
    if read_config(config / 'kdeglobals').get('KDE', 'LookAndFeelPackage', fallback='') != theme.THEME_ID:
        raise RuntimeError('Graphite is not selected as the Global Theme.')
    if not (data / 'plasma/look-and-feel' / theme.THEME_ID / 'metadata.json').is_file():
        raise RuntimeError('Graphite appearance package is missing. Re-run the installer.')
    plugins = read_config(config / 'kwinrc')
    if with_wheel is None:
        with_wheel = plugins.getboolean('Plugins', WHEEL + 'Enabled', fallback=False)
    for name in SCRIPTS:
        loaded = kwin('/Scripting', 'org.kde.kwin.Scripting.isScriptLoaded', name) == '(true,)'
        expected = plugins.getboolean('Plugins', name + 'Enabled', fallback=False)
        if loaded != expected:
            raise RuntimeError(f'Script state does not match configuration: {name}')
    if not plugins.getboolean('Plugins', 'kde-hypr-bridgeEnabled', fallback=False):
        print('Configured script states verified; workspace shortcuts are not installed.')
        return
    count = kwin('/VirtualDesktopManager', 'org.freedesktop.DBus.Properties.Get', 'org.kde.KWin.VirtualDesktopManager', 'count')
    if not re.search(r'\buint32 5\b', count):
        raise RuntimeError('Expected five native desktops')
    if with_wheel and kwin('/Effects', 'org.kde.kwin.Effects.isEffectLoaded', WHEEL) != '(true,)':
        raise RuntimeError('Workspace wheel effect is not loaded')
    from PySide6.QtGui import QKeySequence
    launchers = json.loads((data / 'kde-graphite/runtime/launchers.json').read_text())
    for name, sequence in KEYS.items():
        if name not in launchers:
            continue
        ids = json.dumps(['kwin', 'KdeHyprLaunch' + name, 'KWin', 'Graphite: ' + name])
        actual = dbus('org.kde.kglobalaccel', '/kglobalaccel', 'org.kde.KGlobalAccel.shortcut', ids)
        keys = ast.literal_eval(re.sub(r'@ai\s*', '', actual))[0]
        if QKeySequence(sequence)[0].toCombined() not in keys:
            raise RuntimeError(f'Shortcut is not registered: {sequence}')
    for component, name, sequence in workspace_shortcuts():
        key = QKeySequence(sequence)[0].toCombined()
        reply = dbus('org.kde.kglobalaccel', '/kglobalaccel', 'org.kde.KGlobalAccel.action', str(key))
        owner = ast.literal_eval(re.sub(r'@as\s*', '', reply))[0]
        if owner[:2] != [component, name]:
            raise RuntimeError(f'Workspace shortcut has the wrong handler: {sequence}')
    print(f'Scripts, five desktops, {len(launchers)} application shortcuts and {len(workspace_shortcuts())} workspace shortcuts verified.')


def install_wheel(config, data, state):
    """Build only this project's wheel effect, using installed build tools."""
    if os.geteuid() == 0:
        raise RuntimeError('Run as the desktop user, without sudo.')
    plugins = read_config(config / 'kwinrc')
    if not plugins.getboolean('Plugins', 'kde-hypr-bridgeEnabled', fallback=False):
        raise RuntimeError('Install the Graphite workspace shortcuts before the wheel effect.')
    for command in ['cmake', 'c++']:
        if not shutil.which(command):
            raise RuntimeError('Missing build tool: ' + command + '. No packages were installed.')
    build = ROOT / 'build/wheel'
    run('cmake', '-S', str(ROOT / 'wheel'), '-B', str(build), '-DCMAKE_BUILD_TYPE=Release', timeout=120)
    run('cmake', '--build', str(build), '--parallel', '2', timeout=180)
    plugin_root = data / 'kde-graphite/wheel/qt6/plugins'
    plugin = plugin_root / 'kwin/effects/plugins' / (WHEEL + '.so')
    environment = config / 'plasma-workspace/env/graphite-wheel.sh'
    backup = Backup(state)
    backup.save([plugin, environment, config / 'kwinrc'])
    with transaction(backup):
        plugin.parent.mkdir(parents=True, exist_ok=True)
        # Keep a currently mapped plugin intact; activate the new inode at login.
        atomic_copy(build / (WHEEL + '.so'), plugin)
        environment.parent.mkdir(parents=True, exist_ok=True)
        environment.write_text('# Graphite workspace-wheel effect; Plasma session only.\n'
                               'export QT_PLUGIN_PATH=' + shlex.quote(str(plugin_root)) +
                               '${QT_PLUGIN_PATH:+:"$QT_PLUGIN_PATH"}\n')
        merge_config(config / 'kwinrc', {'Plugins': {WHEEL + 'Enabled': 'true'}})
        print(f'Backup: {backup.path}')
        print('Installed the project wheel effect for this user. No system packages were installed.')
        print('Super+wheel up: next workspace; Super+wheel down: previous workspace.')
        print('Log out and back into KDE to load the user plugin path. Then run: python3 install.py check')


def restore(path):
    restore_files(path)
    pointer = path.parent.parent / 'latest-backup'
    if pointer.exists() and pointer.read_text().strip() == str(path):
        previous = path / 'previous-backup'
        if previous.is_file() and previous.read_text().strip():
            atomic_write(pointer, previous.read_bytes())
        else:
            pointer.unlink()
    restart_shell()
    print('Settings restored. Log out and back into KDE to reload all shortcut registrations.')


def restore_files(path):
    entries = json.loads((path / 'manifest.json').read_text())
    # Validate the complete backup before replacing the first destination.
    for entry in entries:
        target = Path(entry['path'])
        source = path / entry['copy']
        if not target.is_absolute() or target.is_symlink():
            raise RuntimeError('Unsafe restore destination: ' + str(target))
        if entry['existed'] and (source.parent != path or not source.is_file() or source.is_symlink()):
            raise RuntimeError('Missing or unsafe backup file: ' + str(source))
    for entry in entries:
        target = Path(entry['path'])
        if entry['existed']:
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_copy(path / entry['copy'], target)
        elif target.exists():
            target.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', nargs='?', default='theme', choices=['install', 'theme', 'wheel', 'build-theme', 'check', 'restore', 'doctor'])
    parser.add_argument('value', nargs='?')
    parser.add_argument('--settings', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    wheel = parser.add_mutually_exclusive_group()
    wheel.add_argument('--with-wheel', action='store_true', help='Enable the separately compiled workspace wheel plugin')
    wheel.add_argument('--without-wheel', action='store_true', help='Skip wheel verification; installation preserves existing wheel state')
    panels = parser.add_mutually_exclusive_group()
    panels.add_argument('--panel', action='store_true', help='Create or replace top bars; existing bars are retained by default')
    panels.add_argument('--no-panel', action='store_true', help='Compatibility alias: retain existing bars')
    args = parser.parse_args()
    if args.value and args.command not in ['doctor', 'build-theme', 'restore']:
        parser.error('Unexpected argument for ' + args.command + ': ' + args.value)
    if args.command not in ['install', 'doctor'] and (args.panel or args.no_panel):
        parser.error('--panel and --no-panel apply only to install or doctor install')
    if args.command not in ['install', 'doctor', 'check'] and (args.with_wheel or args.without_wheel):
        parser.error('Wheel verification flags apply only to install, doctor install or check')
    if args.command == 'doctor' and args.value != 'install' and (args.panel or args.no_panel or args.with_wheel or args.without_wheel):
        parser.error('Workflow flags require doctor install')
    if args.settings and args.command not in ['install', 'theme', 'doctor']:
        parser.error('--settings applies only to install, theme or doctor')
    home = Path.home()
    config = xdg_path('XDG_CONFIG_HOME', home / '.config')
    data = xdg_path('XDG_DATA_HOME', home / '.local/share')
    state = xdg_path('XDG_STATE_HOME', home / '.local/state')
    if args.command == 'doctor':
        if args.value not in [None, 'theme', 'install']:
            parser.error('Use: install.py doctor theme|install')
        errors = doctor.problems(sys.modules[__name__], settings(args.settings), full=args.value == 'install', with_wheel=args.with_wheel, panel=args.panel)
        if not errors and args.value == 'install':
            resolve_outputs(settings(args.settings))
        if errors:
            raise RuntimeError('Doctor found:\n  - ' + '\n  - '.join(errors))
        if args.value == 'install':
            doctor.report_optional(settings(args.settings))
        print('Ready for ' + ('theme and shortcuts installation.' if args.value == 'install' else 'appearance installation.'))
        return
    if args.dry_run and args.command in ['restore', 'check']:
        print('Would run ' + args.command + (' ' + args.value if args.value else '') + '. No changes made.')
        return
    if args.command == 'install':
        options = settings(args.settings)
        if args.dry_run:
            print(f'Would install {len(payload(options, data, panel=args.panel))} asset/script files under {data}.')
            print(f'Would merge theme and shortcut settings under {config}; use five desktops per output.')
            print('Would ' + ('replace/create top bars.' if args.panel else 'retain existing bars.'))
            print('Would remove retired Graphite utility helpers and shortcut registrations, with backups.')
            print('Would back up touched files and leave other desktop configs unchanged. No changes made.')
        else:
            apply(options, config, data, state, args.with_wheel, args.panel)
    elif args.command == 'wheel':
        if args.dry_run:
            print(f'Would build the project wheel effect using installed tools; copy it under {data / "kde-graphite/wheel"}.')
            print(f'Would add its Plasma-only plugin path under {config / "plasma-workspace/env"} and enable the effect.')
            print('Would back up touched files. No packages installed. No changes made.')
        else:
            install_wheel(config, data, state)
    elif args.command == 'theme':
        options = settings(args.settings)
        if args.dry_run:
            print(f'Would install Graphite under {data / "plasma/look-and-feel" / theme.THEME_ID}.')
            print('Would apply appearance and lock-screen settings; retain panels, workspaces, shortcuts and KWin scripts.')
        else:
            theme.install_theme(options, config, data, state, sys.modules[__name__])
    elif args.command == 'build-theme':
        destination = Path(args.value) if args.value else ROOT / 'build/Graphite-1.0.0.tar.gz'
        if args.dry_run:
            print(f'Would build {destination}.')
        else:
            print(theme.build_archive(destination))
    elif args.command == 'check':
        check(True if args.with_wheel else False if args.without_wheel else None)
    elif args.command == 'restore':
        pointer = state / 'kde-graphite/latest-backup'
        if not args.value and not pointer.is_file():
            raise RuntimeError('No installation backup found. Pass a backup directory explicitly if it was moved.')
        path = Path(args.value).resolve() if args.value else Path(pointer.read_text().strip())
        restore(path)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, OSError, configparser.Error) as error:
        print(f'Error: {error}', file=sys.stderr)
        sys.exit(1)
