"""Build and install the Graphite Plasma LookAndFeel package."""
import io
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parent
THEME_ID = 'org.kde.graphite.desktop'
PACKAGE = ROOT / 'theme' / THEME_ID


def font_values(options):
    family, size = options['font'], options['font_size']
    normal = f'{family},{size},-1,5,400,0,0,0,0,0'
    small = f'{family},{max(size - 1, 8)},-1,5,400,0,0,0,0,0'
    title = f'{family},{max(size - 1, 8)},-1,5,500,0,0,0,0,0'
    return {'General': {**{key: normal for key in ['font', 'fixed', 'menuFont', 'toolBarFont']},
                        'smallestReadableFont': small}, 'WM': {'activeFont': title}}


def layout_script(options):
    # The appearance package must also work without Graphite's workspace scripts.
    prefix = """// Generated from templates/panel.js. No monitor names or widget IDs are stored.
var plugins = new ConfigFile('kwinrc', 'Plugins');
var bridge = new ConfigFile('kwinrc', 'Script-kde-hypr-bridge');
var graphiteBridge = String(plugins.readEntry('kde-hypr-bridgeEnabled')) === 'true';
var graphitePagerType = graphiteBridge && knownWidgetTypes.includes('org.kde.graphite.workspaces')
    ? 'org.kde.graphite.workspaces' : 'org.kde.plasma.pager';
var graphiteAssignShortcuts = graphiteBridge;
var graphitePrimaryOutput = String(bridge.readEntry('PrimaryOutput') || '');
"""
    script = (ROOT / 'templates/panel.js').read_text()
    return (prefix + script.replace('@@PANEL_HEIGHT@@', str(options['panel_height']))
            .replace('@@APPLICATION_TRAY_IDS@@', '[]')
            .replace('@@PRIMARY_OUTPUT@@', 'graphitePrimaryOutput'))


def package_files(options):
    files = {p.relative_to(PACKAGE): p.read_bytes() for p in PACKAGE.rglob('*') if p.is_file()}
    # Canonical palette and layout also feed the full installer.
    files[Path('contents/colors')] = (ROOT / 'assets/color-schemes/TerminalGraphite.colors').read_bytes()
    defaults = (PACKAGE / 'contents/defaults').read_text()
    fonts = font_values(options)
    replacements = {
        'Fira Code,10,-1,5,400,0,0,0,0,0': fonts['General']['font'],
        'Fira Code,9,-1,5,400,0,0,0,0,0': fonts['General']['smallestReadableFont'],
        'Fira Code,9,-1,5,500,0,0,0,0,0': fonts['WM']['activeFont'],
    }
    for old, new in replacements.items():
        defaults = defaults.replace(old, new)
    files[Path('contents/defaults')] = defaults.encode()
    files[Path('contents/layouts/org.kde.plasma.desktop-layout.js')] = layout_script(options).encode()
    return files


def payload(options, data):
    files = {data / 'plasma/look-and-feel' / THEME_ID / path: content
             for path, content in package_files(options).items()}
    # A named palette remains available separately in System Settings > Colors.
    files[data / 'color-schemes/TerminalGraphite.colors'] = (ROOT / 'assets/color-schemes/TerminalGraphite.colors').read_bytes()
    return files


def build_archive(destination):
    # Portable defaults, independent of the font installed on the build machine.
    options = {'font': 'Fira Code', 'font_size': 10, 'panel_height': 28}
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(destination, 'w:gz') as archive:
        for path, content in sorted(package_files(options).items()):
            entry = tarfile.TarInfo(str(Path(THEME_ID) / path))
            entry.size = len(content)
            entry.mode = 0o644
            archive.addfile(entry, io.BytesIO(content))
    return destination


def install_theme(options, config, data, state, api):
    import os
    if 'KDE' not in os.environ.get('XDG_CURRENT_DESKTOP', '').split(':'):
        raise RuntimeError('Run theme installation from a KDE Plasma session.')
    options = dict(options)
    families = api.run('fc-list', ':', 'family')
    if options['font'] not in families:
        options['font'] = 'Fira Code' if 'Fira Code' in families else 'monospace'
    files = payload(options, data)
    fragments = json.loads((ROOT / 'config.json').read_text())
    # Appearance settings only: never enable tiling or rewrite workspace shortcuts.
    kwin = fragments['kwinrc']
    appearance = {name: fragments[name] for name in ['breezerc', 'kscreenlockerrc', 'kded5rc']}
    appearance['kwinrc'] = {'org.kde.kdecoration2': {**kwin['org.kde.kdecoration2'],
                          'library': 'org.kde.breeze', 'theme': 'Breeze'},
                          'Plugins': {k: v for k, v in kwin['Plugins'].items()
                                      if k.endswith('Enabled') and v == 'false'}}
    palette = api.read_config(ROOT / 'assets/color-schemes/TerminalGraphite.colors')
    appearance['kdeglobals'] = {group: dict(palette[group]) for group in palette.sections() if group != 'General'}
    fonts = font_values(options)
    appearance['kdeglobals'].update({'General': {'ColorScheme': 'TerminalGraphite', **fonts['General']},
                                    'KDE': {'LookAndFeelPackage': THEME_ID, 'widgetStyle': 'Breeze', 'AnimationDurationFactor': '0'},
                                    'Icons': {'Theme': 'breeze-dark'}})
    appearance['kdeglobals']['WM'].update(fonts['WM'])
    appearance['plasmarc'] = {'Theme': {'name': 'default'}}
    protected = api.protected_hashes(config)
    backup = api.Backup(state)
    marker = config / 'kdedefaults/package'
    backup.save(list(files) + [config / name for name in appearance] + [marker])
    print(f'Backup: {backup.path}', flush=True)
    # KDE's GTK sync must be stopped before notifying it about palette changes.
    api.dbus('org.kde.kded6', '/kded', 'org.kde.kded6.setModuleAutoloading', 'gtkconfig', 'false')
    api.dbus('org.kde.kded6', '/kded', 'org.kde.kded6.unloadModule', 'gtkconfig')
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    for name, groups in appearance.items():
        api.merge_config(config / name, groups)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(THEME_ID + '\n')
    api.kwin('/KWin', 'org.kde.KWin.reconfigure')
    api.dbus('org.kde.plasmashell', '/PlasmaShell', 'org.kde.PlasmaShell.evaluateScript', "theme = 'default';")
    if protected != api.protected_hashes(config):
        raise RuntimeError(f'A protected desktop config changed. Backup: {backup.path}')
    (state / 'kde-graphite/latest-backup').write_text(str(backup.path) + '\n')
    print('Graphite installed and selected. Reopen System Settings > Colors & Themes > Global Theme.')
    print('Existing panels, shortcuts, workspaces and tiling state retained.')
