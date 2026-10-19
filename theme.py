"""Build and install the Graphite Plasma LookAndFeel package."""
import io
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parent
THEME_ID = 'org.kde.graphite.desktop'
PACKAGE = ROOT / 'theme' / THEME_ID
WALLPAPERS = ('GraphiteContours', 'GraphiteContoursAlternate')


def wallpaper_script(data):
    relative = [Path('plasma/look-and-feel') / THEME_ID / 'contents/wallpapers' / name
                / 'contents/images/3840x2160.png' for name in WALLPAPERS]
    images = json.dumps([(data / path).as_uri() for path in relative])
    return (ROOT / 'templates/wallpaper.js').read_text().replace('@@WALLPAPER_IMAGES@@', images)


def font_values(options):
    family, size = options['font'], options['font_size']
    normal = f'{family},{size},-1,5,400,0,0,0,0,0'
    small = f'{family},{max(size - 1, 8)},-1,5,400,0,0,0,0,0'
    title = f'{family},{max(size - 1, 8)},-1,5,500,0,0,0,0,0'
    return {'General': {**{key: normal for key in ['font', 'fixed', 'menuFont', 'toolBarFont']},
                        'smallestReadableFont': small}, 'WM': {'activeFont': title}}


def package_files(options):
    files = {p.relative_to(PACKAGE): p.read_bytes() for p in PACKAGE.rglob('*') if p.is_file()}
    # The canonical palette also feeds the workflow installer.
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
    return files


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
    options = {'font': 'Fira Code', 'font_size': 10}
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(destination, 'w:gz') as archive:
        for path, content in sorted(package_files(options).items()):
            entry = tarfile.TarInfo(str(Path(THEME_ID) / path))
            entry.size = len(content)
            entry.mode = 0o644
            archive.addfile(entry, io.BytesIO(content))
    return destination


def configuration(options, api):
    """The same appearance settings feed both installation profiles."""
    appearance = json.loads((ROOT / 'config.json').read_text())
    palette = api.read_config(ROOT / 'assets/color-schemes/TerminalGraphite.colors')
    appearance['kdeglobals'] = {group: dict(palette[group]) for group in palette.sections() if group != 'General'}
    fonts = font_values(options)
    appearance['kdeglobals'].update({'General': {'ColorScheme': 'TerminalGraphite', **fonts['General']},
                                    'KDE': {'LookAndFeelPackage': THEME_ID, 'widgetStyle': 'Breeze'},
                                    'Icons': {'Theme': 'breeze-dark'}})
    appearance['kdeglobals']['WM'].update(fonts['WM'])
    appearance['plasmarc'] = {'Theme': {'name': 'default'}}
    return appearance


def retired_layouts(data):
    """Old package layout scripts must not remain available to reset user panels."""
    root = data / 'plasma/look-and-feel' / THEME_ID / 'contents/layouts'
    return [path for path in [root / 'defaults', root / 'org.kde.plasma.desktop-layout.js'] if path.exists()]


def install_theme(options, config, data, state, api):
    import doctor
    doctor.require(api, options)
    options = dict(options)
    families = api.run('fc-list', ':', 'family')
    if options['font'] not in families:
        options['font'] = 'Fira Code' if 'Fira Code' in families else 'monospace'
    files = payload(options, data)
    appearance = configuration(options, api)
    retired = retired_layouts(data)
    protected = api.protected_hashes(config)
    backup = api.Backup(state)
    marker = config / 'kdedefaults/package'
    backup.save(list(files) + [config / name for name in appearance] + [marker] + retired,
                {str(config / name): {group: list(values) for group, values in groups.items()}
                 for name, groups in appearance.items()})
    backup.save_wallpaper()
    print(f'Backup: {backup.path}', flush=True)
    with api.transaction(backup):
        for path, content in files.items():
            api.atomic_write(path, content)
        for name, groups in appearance.items():
            api.merge_config(config / name, groups)
        for path in retired:
            path.unlink()
        api.atomic_write(marker, (THEME_ID + '\n').encode())
        api.plasma_script(wallpaper_script(data))
        if protected != api.protected_hashes(config):
            raise RuntimeError(f'A protected desktop config changed. Backup: {backup.path}')
        print('Graphite installed and selected. Log out and back in to apply all appearance settings.')
        print('Existing panels, shortcuts, workspaces, effects and KWin scripts retained.')
