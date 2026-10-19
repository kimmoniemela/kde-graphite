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
SCRIPTS = ('kde-hypr-bridge',)
APPLICATION_COMPONENT = 'org.kde.graphite.applications.desktop'
RUNTIME_SCRIPTS = ('launch-app.py', 'workspace-keys.py')
# Upgrade cleanup applies only to these retired Graphite utilities.
RETIRED_UTILITIES = {'Wallpaper': 'wallpaper-settings.py', 'ColorPicker': 'pick-color.py'}
WHEEL = 'kwin_hypr_scroll_desktop'


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


def plasma_script(code):
    result = ast.literal_eval(dbus('org.kde.plasmashell', '/PlasmaShell',
                              'org.kde.PlasmaShell.evaluateScript', code))[0]
    if re.search(r'(?:^|\n)(?:Error|TypeError|ReferenceError|SyntaxError):', result):
        raise RuntimeError('Plasma scripting failed: ' + result)
    return result


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


def restored_config(current, original, groups):
    """Restore selected raw KConfig entries while retaining unrelated user text."""
    def blocks(text):
        result = []
        for line in text.splitlines(keepends=True):
            stripped = line.strip()
            if stripped.startswith('[') and stripped.endswith(']'):
                result.append([stripped[1:-1], line, []])
            else:
                if not result:
                    result.append([None, '', []])
                result[-1][2].append(line)
        return result
    def key(line):
        if line.lstrip().startswith(('#', ';')) or '=' not in line:
            return None
        return re.sub(r'\[\$[edi]+\]', '', line.split('=', 1)[0].strip())
    old_blocks = blocks(original)
    old_groups = {group for group, _, _ in old_blocks}
    saved = {(group, key(line)): line for group, _, lines in old_blocks for line in lines
             if key(line) in groups.get(group, [])}
    restored, seen = [], set()
    for group, header, lines in blocks(current):
        selected = set(groups.get(group, []))
        if group and group.endswith('][$i') and group[:-4] in groups:
            raise RuntimeError('Cannot restore a locked KConfig group: ' + group)
        body = []
        for line in lines:
            name = key(line)
            if name not in selected:
                body.append(line)
                continue
            if '[$i]' in line.split('=', 1)[0]:
                raise RuntimeError('Cannot restore a locked KConfig entry: ' + name)
            identity = (group, name)
            if identity not in seen and identity in saved:
                body.append(saved[identity].rstrip('\n') + '\n')
            seen.add(identity)
        for name in groups.get(group, []):
            identity = (group, name)
            if identity in saved and identity not in seen:
                if body and not body[-1].endswith('\n'):
                    body[-1] += '\n'
                body.append(saved[identity].rstrip('\n') + '\n')
                seen.add(identity)
        if group not in old_groups and not any(line.strip() for line in body):
            continue
        restored += [header, *body]
    for group, header, lines in old_blocks:
        missing = [line for line in lines if (group, key(line)) in saved and (group, key(line)) not in seen]
        if missing:
            restored += ['\n', header, *missing]
    content = ''.join(restored)
    # Remove only formatting left behind by newly created, now empty groups.
    if [line for line in content.splitlines() if line.strip()] == [line for line in original.splitlines() if line.strip()]:
        return original
    return content


def shortcut_groups(actions):
    groups = {}
    for component, name in actions:
        groups.setdefault(component, []).append(name)
        if component.endswith('.desktop'):
            groups.setdefault('services][' + component, []).append(name)
    return groups


def atomic_write(path, content):
    if path.is_file() and path.read_bytes() == content:
        return
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
    """Replace a changed file without truncating a mapped library."""
    if target.is_file() and source.read_bytes() == target.read_bytes() and source.stat().st_mode == target.stat().st_mode:
        return
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        shutil.copy2(source, temporary_path)
        temporary_path.replace(target)
    finally:
        temporary_path.unlink(missing_ok=True)


def legacy_actions():
    names = set(json.loads((ROOT / 'shortcuts.json').read_text())['applications'])
    names.update(['CalculatorKey', 'Launcher', 'Settings', 'Emoji', 'SessionMenu',
                  'ScreenshotRegion', 'ScreenshotFull', *RETIRED_UTILITIES])
    return ({'KdeHyprLaunch' + name for name in names} | {'KdeHyprLocalDesktop' + str(n) for n in range(1, 6)}
            | {'KdeHyprMonitorPrev', 'KdeHyprMonitorNext'})


def retired_files(data):
    paths = [data / 'kde-graphite/runtime' / name for name in RETIRED_UTILITIES.values()]
    paths += [data / 'kwin/scripts/kde-hypr-launchers-v2' / name
              for name in ['metadata.json', 'contents/ui/main.qml']]
    return [path for path in paths if path.exists()] + theme.retired_layouts(data)


def retire_shortcuts(config):
    saved = read_config(config / 'kglobalshortcutsrc')
    actions = legacy_actions()
    changed = False
    for section in saved.sections():
        if section not in ('kwin', 'kwin][$i'):
            continue
        for key in saved[section]:
            name = re.sub(r'\[\$[edi]+\]', '', key)
            if name not in actions:
                continue
            if '[$i]' in section or '[$i]' in key:
                raise RuntimeError('KConfig shortcut is locked: ' + name)
            dbus('org.kde.kglobalaccel', '/kglobalaccel', 'org.kde.KGlobalAccel.unregister', 'kwin', name)
            changed = True
    return changed


def settings(path=None):
    result = json.loads((ROOT / 'settings.json').read_text())
    if path:
        local = json.loads(Path(path).read_text())
        if not isinstance(local, dict):
            raise ValueError('settings must contain a JSON object')
        local.pop('panel_height', None)  # Ignored preference from the retired panel installer.
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
    if not isinstance(result['altgr_as_super'], bool):
        raise ValueError('altgr_as_super must be a boolean')
    if not all(isinstance(result[role], str) for role in ['primary_output', 'secondary_output']):
        raise ValueError('output names must be strings; use an empty string for automatic detection')
    if not isinstance(result['font'], str) or not result['font'] or any(c in result['font'] for c in ',\n\r'):
        raise ValueError('font must be a family name without commas or line breaks')
    if not isinstance(result['font_size'], (int, float)) or not 6 <= result['font_size'] <= 32:
        raise ValueError('font_size must be between 6 and 32')
    return result


def keyboard_configuration(config):
    """Add a user XKB option without replacing layouts or other keyboard options."""
    option = 'graphite:altgr_super'
    rules = config / 'xkb/rules/evdev'
    content = rules.read_text() if rules.exists() else '! include %S/evdev\n'
    rule = option + ' = +graphite(altgr_super)'
    if rule not in content:
        content += '\n! option = symbols\n  ' + rule + '\n'
    existing = read_config(config / 'kxkbrc')
    options = existing.get('Layout', 'Options', fallback=os.environ.get('XKB_DEFAULT_OPTIONS', ''))
    values = [value for value in options.split(',') if value and value != option]
    values.append(option)
    files = {rules: content.encode(),
             config / 'xkb/symbols/graphite': (ROOT / 'assets/xkb/symbols/graphite').read_bytes()}
    return files, {'Layout': {'Options': ','.join(values), 'ResetOldOptions': 'true'}}


def desktop_exec(argv):
    """Quote an argv array for Desktop Entry Exec, including its KConfig layer."""
    args = ['"' + re.sub(r'([\\`"$])', r'\\\1', value).replace('%', '%%') + '"' for value in argv]
    return ' '.join(args).replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')


def workspace_script():
    bindings = {name.removeprefix('KdeHypr'): seq for _, name, seq in workspace_shortcuts()}
    return (ROOT / 'templates/workspaces.js').read_text().replace('@@WORKSPACE_SHORTCUTS@@', json.dumps(bindings))


def payload(options, data, commands=None):
    """Install a native shortcut service and only the essential workspace helpers."""
    files = theme.payload(options, data)
    runtime = data / 'kde-graphite/runtime'
    for name in RUNTIME_SCRIPTS:
        files[runtime / name] = (ROOT / 'scripts' / name).read_bytes()
    files[runtime / 'applications.py'] = (ROOT / 'applications.py').read_bytes()
    if commands is None:
        commands, _ = applications.launchers(options)
    files[runtime / 'launchers.json'] = (json.dumps(commands, indent=2) + '\n').encode()
    keys = json.loads((ROOT / 'shortcuts.json').read_text())['applications']
    desktop = ['[Desktop Entry]', 'Type=Application', 'Name=Graphite application shortcuts',
               'X-KDE-GlobalShortcutType=Service', 'Actions=' + ';'.join(commands) + ';']
    for name, argv in commands.items():
        # KIO does not field-expand percent signs in the executable token.
        use_resolver = argv == applications.DEFAULT or '%' in argv[0]
        command = [sys.executable, str(runtime / 'launch-app.py'), name] if use_resolver else argv
        desktop += ['', '[Desktop Action ' + name + ']', 'Name=Graphite: ' + name,
                    'Exec=' + desktop_exec(command), 'X-KDE-Shortcuts=' + keys[name].replace(';', ','), 'StartupNotify=false']
    files[data / 'kglobalaccel' / APPLICATION_COMPONENT] = ('\n'.join(desktop) + '\n').encode()
    scripts_path = data / 'kwin/scripts/kde-hypr-bridge/metadata.json'
    files[scripts_path] = (json.dumps({
        'KPackageStructure': 'KWin/Script', 'KPlugin': {'Id': SCRIPTS[0], 'Name': 'Graphite workspaces',
        'Version': '1.0', 'License': 'MIT'}, 'X-Plasma-API': 'javascript', 'X-Plasma-MainScript': 'code/main.js'}, indent=2) + '\n').encode()
    files[scripts_path.parent / 'contents/code/main.js'] = workspace_script().encode()
    return files


def autostart_file(data):
    return ('[Desktop Entry]\nType=Application\nName=Graphite workspace keyboard layouts\nOnlyShowIn=KDE;\n'
            'Exec=' + desktop_exec([sys.executable, str(data / 'kde-graphite/runtime/workspace-keys.py')]) + '\n').encode()


class Backup:
    def __init__(self, state):
        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6]
        self.path = state / 'kde-graphite/backups' / stamp
        self.path.mkdir(parents=True, mode=0o700)
        self.pointer = state / 'kde-graphite/latest-backup'
        self.previous = self.pointer.read_text() if self.pointer.exists() else ''
        (self.path / 'previous-backup').write_text(self.previous)
        self.files = []

    def save(self, paths, selections=None):
        known = {entry['path'] for entry in self.files}
        for path in paths:
            path = Path(path)
            if str(path) in known:
                continue
            if path.is_symlink():
                raise RuntimeError(f'Refusing to replace symlink: {path}')
            entry = {'path': str(path), 'existed': path.exists(), 'copy': str(len(self.files))}
            if selections and str(path) in selections:
                entry['groups'] = selections[str(path)]
            if path.exists():
                shutil.copy2(path, self.path / entry['copy'])
            self.files.append(entry)
            known.add(str(path))
            self.flush()

    def include_shortcut_owners(self, actions):
        entry = next(item for item in self.files if Path(item['path']).name == 'kglobalshortcutsrc')
        for group, names in shortcut_groups(actions).items():
            entry['groups'].setdefault(group, []).extend(names)
        self.flush()

    def save_wallpaper(self):
        code = """print(JSON.stringify(desktops().map(d => {
    d.currentConfigGroup = ['Wallpaper', 'org.kde.image', 'General'];
    return {id:d.id, plugin:d.wallpaperPlugin, image:d.readConfig('Image', ''), fill:d.readConfig('FillMode', 2)};
})));"""
        snapshot = json.loads(plasma_script(code))
        if not isinstance(snapshot, list) or any(not isinstance(item, dict) or
                not {'id', 'plugin', 'image', 'fill'} <= item.keys() for item in snapshot):
            raise RuntimeError('Could not snapshot Plasma desktop wallpapers; no changes made.')
        atomic_write(self.path / 'wallpaper.json', (json.dumps(snapshot) + '\n').encode())

    def flush(self):
        atomic_write(self.path / 'manifest.json', (json.dumps(self.files, indent=2) + '\n').encode())


@contextmanager
def transaction(backup):
    """Recover saved files after any failed mutation; keep the failure backup."""
    atomic_write(backup.pointer, (str(backup.path) + '\n').encode())
    try:
        yield
    except BaseException:
        # Let queued KGlobalAccel writes settle before recovering the saved config.
        import time
        time.sleep(0.6)
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
    groups = json.loads((ROOT / 'shortcuts.json').read_text())['native']
    return {(component, name): sequences for component, values in groups.items()
            if not component.endswith('.desktop') or applications.service_path(component)
            for name, sequences in values.items()}


def application_shortcuts(commands):
    keys = json.loads((ROOT / 'shortcuts.json').read_text())['applications']
    return {(APPLICATION_COMPONENT, name): keys[name] for name in commands}


def clear_conflicts(bindings, backup=None):
    from PySide6.QtGui import QKeySequence
    base = ('org.kde.kglobalaccel', '/kglobalaccel')
    managed = set(shortcut_ids()) | {(c, n) for c, n, _ in workspace_shortcuts()}
    managed.update(('kwin', name) for name in legacy_actions())
    managed.update((APPLICATION_COMPONENT, name) for name in json.loads((ROOT / 'shortcuts.json').read_text())['applications'])
    # Native defaults displaced by Graphite's documented bindings.
    native_defaults = {('kwin', 'Show Desktop'), ('kwin', 'Overview'), ('kwin', 'Edit Tiles'),
        ('kwin', 'Window One Desktop to the Left'), ('kwin', 'Window One Desktop to the Right'),
        ('kwin', 'Switch One Desktop to the Left'), ('kwin', 'Switch One Desktop to the Right'),
        ('kwin', 'Switch One Desktop Down'), ('org.kde.spectacle.desktop', '_launch'),
        ('org.kde.spectacle.desktop', 'ActiveWindowScreenShot'),
        ('plasmashell', 'manage activities')}
    native_defaults.update(('plasmashell', 'activate task manager entry ' + str(n)) for n in range(1, 11))
    native_defaults.update((name, '_launch') for name in ['org.kde.dolphin.desktop',
                          'org.kde.konsole.desktop', 'org.kde.plasma-systemmonitor.desktop'])
    changes = {}
    for component, name, sequences in bindings:
        for sequence in sequences.split(';'):
            if not sequence:
                continue
            key = QKeySequence(sequence)[0].toCombined()
            reply = dbus(*base, 'org.kde.KGlobalAccel.action', str(key))
            owner = ast.literal_eval(re.sub(r'@as\s*', '', reply))[0]
            if owner and owner[:2] != [component, name]:
                if tuple(owner[:2]) not in managed | native_defaults:
                    raise RuntimeError(f'{sequence} belongs to an unmanaged shortcut action: {owner[1]}. '
                                       'Resolve the conflict in System Settings before installing.')
                reply = dbus(*base, 'org.kde.KGlobalAccel.shortcut', json.dumps(owner))
                current = ast.literal_eval(re.sub(r'@ai\s*', '', reply))[0]
                ids = json.dumps(owner)
                previous = changes.get(ids, current)
                changes[ids] = [code for code in previous if code != key]
    if backup and changes:
        backup.include_shortcut_owners([json.loads(ids)[:2] for ids in changes])
    for ids, remaining in changes.items():
        dbus(*base, 'org.kde.KGlobalAccel.setShortcut', ids, json.dumps(remaining), '4')
    return bool(changes)


def native_shortcuts(bindings):
    """Let KGlobalAccel persist version-appropriate configuration; skip unchanged actions."""
    from PySide6.QtGui import QKeySequence
    changed = False
    for (component, name), sequences in bindings.items():
        keys = [QKeySequence(sequence)[0].toCombined() for sequence in sequences.split(';') if sequence]
        ids = json.dumps([component, name, component, name])
        current = dbus('org.kde.kglobalaccel', '/kglobalaccel', 'org.kde.KGlobalAccel.shortcut', ids)
        current = ast.literal_eval(re.sub(r'@ai\s*', '', current))[0]
        if set(keys) <= set(current):
            continue
        keys = list(dict.fromkeys(current + keys))
        dbus('org.kde.kglobalaccel', '/kglobalaccel', 'org.kde.KGlobalAccel.doRegister', ids)
        actual = dbus('org.kde.kglobalaccel', '/kglobalaccel', 'org.kde.KGlobalAccel.setShortcut', ids, json.dumps(keys), '4')
        if set(ast.literal_eval(re.sub(r'@ai\s*', '', actual))[0]) != set(keys):
            raise RuntimeError('Could not register shortcut: ' + sequences)
        changed = True
    if changed:
        import time
        # KGlobalAccel debounces persistence for 500 ms; let it finish before returning.
        time.sleep(0.6)
    return changed


def workspace_shortcuts():
    bindings = [('kwin', 'KdeHypr' + prefix + str(n), modifier + str(n % 10))
            for prefix, modifier in [('Desktop', 'Meta+'), ('SendDesktop', 'Meta+Shift+')]
            for n in range(1, 11)]
    bindings += [('kwin', 'KdeHypr' + name, sequence) for name, sequence in {
        'WorkspaceNext': 'Meta+Ctrl+Right', 'WorkspacePrev': 'Meta+Ctrl+Left',
        'SendNext': 'Meta+Ctrl+Shift+Right', 'SendPrev': 'Meta+Ctrl+Shift+Left',
        'Empty': 'Meta+Ctrl+Down', 'ScratchSend': 'Meta+Shift+S', 'ScratchToggle': 'Meta+S',
    }.items()]
    return bindings


def preflight(options, with_wheel=False):
    doctor.require(sys.modules[__name__], options, full=True, with_wheel=with_wheel)


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


def apply(options, config, data, state, with_wheel=False):
    preflight(options, with_wheel)
    options = resolve_outputs(options)
    families = run('fc-list', ':', 'family')
    if options['font'] not in families:
        options['font'] = 'Fira Code' if 'Fira Code' in families else 'monospace'
    commands = doctor.report_optional(options)
    files = payload(options, data, commands)
    files[config / 'autostart/org.kde.graphite.workspace-keys.desktop'] = autostart_file(data)
    fragments = theme.configuration(options, sys.modules[__name__])
    if options['altgr_as_super']:
        keyboard_files, fragments['kxkbrc'] = keyboard_configuration(config)
        files.update(keyboard_files)
    fragments['kwinrc']['Windows']['PerOutputVirtualDesktops'] = 'true'
    fragments['kwinrc']['Plugins'] = {'kde-hypr-bridgeEnabled': 'true'}
    installed = read_config(config / 'kwinrc')
    for name in ['kde-hypr-launchers', 'kde-hypr-launchers-v2']:
        if installed.has_option('Plugins', name + 'Enabled'):
            fragments['kwinrc']['Plugins'][name + 'Enabled'] = 'false'
    if with_wheel:
        fragments['kwinrc']['Plugins'][WHEEL + 'Enabled'] = 'true'
    fragments['kwinrc']['Script-kde-hypr-bridge'] = {
        'PrimaryOutput': options['primary_output'], 'SecondaryOutput': options['secondary_output']}
    fragments['kwinrc']['Desktops'] = {'Number': '5'}
    bindings = {**shortcut_ids(), **application_shortcuts(commands),
                **{(c, n): seq for c, n, seq in workspace_shortcuts()}}
    before = protected_hashes(config)
    retired = retired_files(data)
    backup = Backup(state)
    selections = {str(config / name): {group: list(values) for group, values in groups.items()}
                  for name, groups in fragments.items()}
    selections[str(config / 'kglobalshortcutsrc')] = shortcut_groups(
        list(bindings) + [('kwin', name) for name in legacy_actions()])
    backup.save([config / name for name in fragments] + [config / 'kglobalshortcutsrc',
                config / 'kdedefaults/package'] + retired + list(files), selections)
    backup.save_wallpaper()
    print(f'Backup: {backup.path}', flush=True)
    with transaction(backup):
        changed = clear_conflicts([(c, n, seq) for (c, n), seq in bindings.items()], backup)
        for path, content in files.items():
            atomic_write(path, content)
        for name, groups in fragments.items():
            merge_config(config / name, groups)
        changed = retire_shortcuts(config) or changed
        for path in retired:
            path.unlink()
        atomic_write(config / 'kdedefaults/package', (theme.THEME_ID + '\n').encode())
        registered = native_shortcuts(bindings)
        if changed and not registered:
            import time
            time.sleep(0.6)
        plasma_script(theme.wallpaper_script(data))
        if before != protected_hashes(config):
            raise RuntimeError(f'A protected desktop config changed during installation. Backup: {backup.path}')
        print('Installed. Log out and back into KDE to activate workspaces and shortcuts. Then run: python3 install.py check')


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
    if not (data / 'kglobalaccel' / APPLICATION_COMPONENT).is_file():
        raise RuntimeError('Native Graphite shortcut service is missing. Re-run install and log in again.')
    if not (config / 'autostart/org.kde.graphite.workspace-keys.desktop').is_file():
        raise RuntimeError('Keyboard-layout autostart entry is missing. Re-run install.')
    from PySide6.QtGui import QKeySequence
    launchers = json.loads((data / 'kde-graphite/runtime/launchers.json').read_text())
    bindings = {**shortcut_ids(), **application_shortcuts(launchers),
                **{(c, n): seq for c, n, seq in workspace_shortcuts()}}
    for (component, name), sequences in bindings.items():
        ids = json.dumps([component, name, component, name])
        actual = dbus('org.kde.kglobalaccel', '/kglobalaccel', 'org.kde.KGlobalAccel.shortcut', ids)
        keys = ast.literal_eval(re.sub(r'@ai\s*', '', actual))[0]
        for sequence in sequences.split(';'):
            key = QKeySequence(sequence)[0].toCombined()
            if key not in keys:
                raise RuntimeError(f'Shortcut is not registered: {sequence}')
            reply = dbus('org.kde.kglobalaccel', '/kglobalaccel', 'org.kde.KGlobalAccel.action', str(key))
            owner = ast.literal_eval(re.sub(r'@as\s*', '', reply))[0]
            if owner[:2] != [component, name]:
                raise RuntimeError(f'Shortcut has a conflicting handler: {sequence}')
    if dbus('org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus.NameHasOwner',
            'org.kde.GraphiteWorkspaceKeys') != '(true,)':
        raise RuntimeError('Workspace keyboard-layout helper is not running. Log in again.')
    print(f'Workspace script, five desktops and {len(bindings)} native/global shortcut actions verified.')


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
    backup.save([plugin, environment, config / 'kwinrc'],
                {str(config / 'kwinrc'): {'Plugins': [WHEEL + 'Enabled']}})
    with transaction(backup):
        plugin.parent.mkdir(parents=True, exist_ok=True)
        # Keep a currently mapped plugin intact; activate the new inode at login.
        atomic_copy(build / (WHEEL + '.so'), plugin)
        environment.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(environment, ('# Graphite workspace-wheel effect; Plasma session only.\n'
                                  'export QT_PLUGIN_PATH=' + shlex.quote(str(plugin_root)) +
                                  '${QT_PLUGIN_PATH:+:"$QT_PLUGIN_PATH"}\n').encode())
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
    print('Settings restored. Log out and back into KDE to reload all shortcut registrations.')


def restore_files(path):
    entries = json.loads((path / 'manifest.json').read_text())
    wallpaper = path / 'wallpaper.json'
    snapshot = json.loads(wallpaper.read_text()) if wallpaper.exists() else None
    if snapshot is not None and (not isinstance(snapshot, list) or any(not isinstance(item, dict) or
            not {'id', 'plugin', 'image', 'fill'} <= item.keys() for item in snapshot)):
        raise RuntimeError('Invalid wallpaper backup; no files changed.')
    # Validate the complete backup before replacing the first destination.
    for entry in entries:
        target = Path(entry['path'])
        source = path / entry['copy']
        if not target.is_absolute() or target.is_symlink():
            raise RuntimeError('Unsafe restore destination: ' + str(target))
        if entry['existed'] and (source.parent != path or not source.is_file() or source.is_symlink()):
            raise RuntimeError('Missing or unsafe backup file: ' + str(source))
    scoped = {}
    for entry in entries:
        target = Path(entry['path'])
        groups = entry.get('groups')
        # Older backups predate entry selections. Never restore foreign KWin scripts.
        if groups is None and target.name == 'kwinrc':
            groups = {group: list(values) for group, values in json.loads((ROOT / 'config.json').read_text())['kwinrc'].items()}
            groups.update({'Windows': ['BorderlessMaximizedWindows', 'PerOutputVirtualDesktops'],
                           'Desktops': ['Number'], 'Script-kde-hypr-bridge': ['PrimaryOutput', 'SecondaryOutput'],
                           'Plugins': ['kde-hypr-bridgeEnabled', 'kde-hypr-launchersEnabled',
                                       'kde-hypr-launchers-v2Enabled', WHEEL + 'Enabled']})
        if groups is None and target.name == 'kglobalshortcutsrc':
            groups = shortcut_groups(list(shortcut_ids()) + [(c,n) for c,n,_ in workspace_shortcuts()]
                                     + [('kwin', name) for name in legacy_actions()])
        if groups is not None:
            if not isinstance(groups, dict) or any(not isinstance(names, list) or
                    not all(isinstance(name, str) for name in names) for names in groups.values()):
                raise RuntimeError('Invalid scoped configuration backup; no files changed.')
            original = (path / entry['copy']).read_text() if entry['existed'] else ''
            current = target.read_text() if target.exists() else ''
            scoped[str(target)] = restored_config(current, original, groups)
    legacy_layouts = [entry for entry in entries if Path(entry['path']).name == 'plasma-org.kde.plasma.desktop-appletsrc']
    if snapshot is None and legacy_layouts and legacy_layouts[0]['existed']:
        original = read_config(path / legacy_layouts[0]['copy'])
        snapshot = []
        for section in original.sections():
            match = re.fullmatch(r'Containments\]\[(\d+)', section)
            if not match or original[section].get('plugin') == 'org.kde.panel' or 'wallpaperplugin' not in original[section]:
                continue
            group = section + '][Wallpaper][org.kde.image][General'
            snapshot.append({'id': int(match[1]), 'plugin': original[section]['wallpaperplugin'],
                             'image': original.get(group, 'Image', fallback=''),
                             'fill': original.get(group, 'FillMode', fallback='2')})
    for entry in entries:
        target = Path(entry['path'])
        if target.name == 'plasma-org.kde.plasma.desktop-appletsrc':
            continue  # Legacy backups restore desktop wallpaper through Plasma, never whole panels.
        if str(target) in scoped:
            content = scoped[str(target)]
            if not entry['existed'] and not content.strip():
                target.unlink(missing_ok=True)
            else:
                atomic_write(target, content.encode())
        elif entry['existed']:
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_copy(path / entry['copy'], target)
        elif target.exists():
            target.unlink()
    if snapshot:
        code = 'var saved = ' + json.dumps(snapshot) + """;
for (const d of desktops()) {
    const old = saved.find(item => item.id === d.id);
    if (!old) continue;
    d.currentConfigGroup = ['Wallpaper', 'org.kde.image', 'General'];
    d.writeConfig('Image', old.image);
    d.writeConfig('FillMode', old.fill);
    d.wallpaperPlugin = old.plugin;
}"""
        plasma_script(code)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', nargs='?', default='theme', choices=['install', 'theme', 'wheel', 'build-theme', 'check', 'restore', 'doctor'])
    parser.add_argument('value', nargs='?')
    parser.add_argument('--settings', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    wheel = parser.add_mutually_exclusive_group()
    wheel.add_argument('--with-wheel', action='store_true', help='Enable the separately compiled workspace wheel plugin')
    wheel.add_argument('--without-wheel', action='store_true', help='Skip wheel verification; installation preserves existing wheel state')
    args = parser.parse_args()
    if args.value and args.command not in ['doctor', 'build-theme', 'restore']:
        parser.error('Unexpected argument for ' + args.command + ': ' + args.value)
    if args.command not in ['install', 'doctor', 'check'] and (args.with_wheel or args.without_wheel):
        parser.error('Wheel verification flags apply only to install, doctor install or check')
    if args.command == 'doctor' and args.value != 'install' and (args.with_wheel or args.without_wheel):
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
        errors = doctor.problems(sys.modules[__name__], settings(args.settings), full=args.value == 'install', with_wheel=args.with_wheel)
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
            print(f'Would install {len(payload(options, data))} asset/script files under {data}.')
            print(f'Would merge theme and shortcut settings under {config}; use five desktops per output.')
            print('Would preserve all existing panels and native Pager settings.')
            if options['altgr_as_super']:
                print('Would map AltGr to an additional Super key, preserving existing layouts and other options.')
            print('Would retire obsolete Graphite launchers with backups; preserve installed widgets used by existing panels.')
            print('Would back up touched files and leave other desktop configs unchanged. No changes made.')
        else:
            apply(options, config, data, state, args.with_wheel)
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
