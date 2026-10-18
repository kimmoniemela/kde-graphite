"""Build and install the Graphite Plasma LookAndFeel package."""
import io
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parent
THEME_ID = 'org.kde.graphite.desktop'
PACKAGE = ROOT / 'theme' / THEME_ID
WALLPAPERS = ('GraphiteContours', 'GraphiteContoursAlternate')


def wallpaper_script(data=None):
    relative = [Path('plasma/look-and-feel') / THEME_ID / 'contents/wallpapers' / name
                / 'contents/images/3840x2160.png' for name in WALLPAPERS]
    if data is not None:
        images = json.dumps([(data / path).as_uri() for path in relative])
    else:
        images = '[' + ', '.join('"file://" + userDataPath("data", ' + json.dumps(str(path))
                                  + ').split("/").map(encodeURIComponent).join("/")' for path in relative) + ']'
    return (ROOT / 'templates/wallpaper.js').read_text().replace('@@WALLPAPER_IMAGES@@', images)


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
            .replace('@@PRIMARY_OUTPUT@@', 'graphitePrimaryOutput')) + wallpaper_script()


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


def window_control_files(data):
    root = data / 'kwin/scripts/graphite-window-controls'
    metadata = {'KPackageStructure': 'KWin/Script',
                'KPlugin': {'Id': 'graphite-window-controls', 'Name': 'Graphite window controls',
                            'Description': 'Keep minimize, maximize and close controls on normal windows',
                            'Version': '1.0', 'License': 'MIT'},
                'X-Plasma-API': 'javascript', 'X-Plasma-MainScript': 'code/main.js'}
    return {root / 'metadata.json': (json.dumps(metadata, indent=2) + '\n').encode(),
            root / 'contents/code/main.js': (ROOT / 'templates/window-controls.js').read_bytes()}


def payload(options, data):
    files = {data / 'plasma/look-and-feel' / THEME_ID / path: content
             for path, content in package_files(options).items()}
    # Also expose named packages in KDE's wallpaper picker.
    for name in WALLPAPERS:
        source = PACKAGE / 'contents/wallpapers' / name
        for path in source.rglob('*'):
            if path.is_file():
                files[data / 'wallpapers' / name / path.relative_to(source)] = path.read_bytes()
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
    import doctor
    doctor.require(api, options)
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
                          'Windows': {'BorderlessMaximizedWindows': 'false'},
                          'Plugins': {k: v for k, v in kwin['Plugins'].items()
                                      if k.endswith('Enabled') and v == 'false' and not k.startswith('kde-hypr-')},
                          }
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
    backup.save(list(files) + [config / name for name in appearance]
                + [marker, config / 'plasma-org.kde.plasma.desktop-appletsrc'])
    print(f'Backup: {backup.path}', flush=True)
    with api.transaction(backup):
        # KDE's GTK sync must be stopped before notifying it about palette changes.
        api.dbus('org.kde.kded6', '/kded', 'org.kde.kded6.setModuleAutoloading', 'gtkconfig', 'false')
        api.dbus('org.kde.kded6', '/kded', 'org.kde.kded6.unloadModule', 'gtkconfig')
        for path, content in files.items():
            api.atomic_write(path, content)
        for name, groups in appearance.items():
            api.merge_config(config / name, groups)
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(THEME_ID + '\n')
        api.kwin('/KWin', 'org.kde.KWin.reconfigure')
        api.dbus('org.kde.plasmashell', '/PlasmaShell', 'org.kde.PlasmaShell.evaluateScript',
                 "theme = 'default';\n" + wallpaper_script(data))
        if protected != api.protected_hashes(config):
            raise RuntimeError(f'A protected desktop config changed. Backup: {backup.path}')
        print('Graphite installed and selected. Reopen System Settings > Colors & Themes > Global Theme.')
        print('Existing panels, shortcuts, workspaces and tiling state retained.')
