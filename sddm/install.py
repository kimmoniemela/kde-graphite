#!/usr/bin/env python3
"""Explicit system-wide SDDM theme install; no packages or service restarts."""
import argparse
import configparser
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sysconfig
import tempfile
import uuid

SOURCE = Path(__file__).resolve().parent / 'graphite'
THEME = Path('/usr/share/sddm/themes/graphite')
CONFIG = Path('/etc/sddm.conf.d/99-graphite.conf')
MAIN_CONFIG = Path('/etc/sddm.conf')
BACKUPS = Path('/var/lib/kde-graphite/sddm-backups')
REQUIRED = ['Main.qml', 'Login.qml', 'Background.qml', 'KeyboardButton.qml',
            'SessionButton.qml', 'metadata.desktop', 'theme.conf', 'background.png',
            'preview.png', 'faces/.face.icon']
QML_MODULES = ['QtQuick', 'QtQuick/Layouts', 'QtQuick/Controls', 'Qt5Compat/GraphicalEffects',
               'org/kde/plasma/components', 'org/kde/plasma/extras', 'org/kde/kirigami',
               'org/kde/plasma/private/keyboardindicator', 'org/kde/plasma/workspace/keyboardlayout',
               'org/kde/breeze/components']


def runtime_check():
    """Reject missing greeter components before selecting a system login theme."""
    if not any(shutil.which(name) for name in ['sddm-greeter-qt6', 'sddm-greeter']):
        raise RuntimeError('SDDM greeter is unavailable. Desktop installation does not require SDDM.')
    roots = [Path(p) for p in os.environ.get('QML_IMPORT_PATH', '').split(':') if p]
    roots += [Path('/usr/lib/qt6/qml'), Path('/usr/lib64/qt6/qml')]
    multiarch = sysconfig.get_config_var('MULTIARCH')
    if multiarch:
        roots.append(Path('/usr/lib') / multiarch / 'qt6/qml')
    for name in ['qtpaths6', 'qtpaths-qt6', '/usr/lib/qt6/bin/qtpaths']:
        if shutil.which(name):
            result = subprocess.run([name, '--query', 'QT_INSTALL_QML'], text=True,
                                    capture_output=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                roots.append(Path(result.stdout.strip()))
            break
    missing = [module.replace('/', '.') for module in QML_MODULES
               if not any((root / module / 'qmldir').is_file() for root in roots)]
    if missing:
        raise RuntimeError('SDDM theme requires installed Qt 6 / Plasma Breeze QML modules: '
                           + ', '.join(missing) + '. No system files changed.')


def source_files():
    files = []
    for relative in REQUIRED:
        path = SOURCE / relative
        if not path.is_file() or path.is_symlink():
            raise RuntimeError('Missing or unsafe theme source: ' + str(path))
        files.append((relative, path))
    return files


def apply():
    files = source_files()
    if os.geteuid() != 0:
        raise RuntimeError('System SDDM files need administrator access. Run: sudo python3 sddm/install.py')
    runtime_check()
    for target in [THEME, CONFIG, THEME.parent, CONFIG.parent, BACKUPS]:
        if target.is_symlink():
            raise RuntimeError('Refusing a symlink at ' + str(target))
    # Later drop-ins and /etc/sddm.conf override our file.
    main = configparser.ConfigParser(interpolation=None)
    later = sorted(path for path in CONFIG.parent.glob('*.conf') if path.name > CONFIG.name)
    main.read(later + [MAIN_CONFIG])
    current = main.get('Theme', 'Current', fallback='')
    if current and current != 'graphite':
        raise RuntimeError('A higher-priority SDDM config selects another theme; remove its Theme/Current override first.')
    effective = configparser.ConfigParser(interpolation=None)
    effective.read(sorted(Path('/usr/lib/sddm/sddm.conf.d').glob('*.conf'))
                   + sorted(CONFIG.parent.glob('*.conf')) + [MAIN_CONFIG])
    theme_dir = effective.get('Theme', 'ThemeDir', fallback=str(THEME.parent))
    if Path(theme_dir) != THEME.parent:
        raise RuntimeError('SDDM uses a custom ThemeDir; no system files changed: ' + theme_dir)
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6]
    backup = BACKUPS / stamp
    backup.mkdir(parents=True, mode=0o700)
    if THEME.exists():
        shutil.copytree(THEME, backup / 'theme', symlinks=True)
    if CONFIG.exists():
        shutil.copy2(CONFIG, backup / 'config')
    (backup / 'manifest.json').write_text(json.dumps({
        'version': 1, 'theme_existed': THEME.exists(), 'config_existed': CONFIG.exists(),
    }) + '\n')
    try:
        THEME.parent.mkdir(parents=True, exist_ok=True)
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        # Copy only the reviewed theme files, owned by root, readable by SDDM.
        with tempfile.TemporaryDirectory(prefix='.graphite-', dir=THEME.parent) as directory:
            staged = Path(directory) / 'graphite'
            staged.mkdir(mode=0o755)
            for relative, source in files:
                target = staged / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read_bytes())
                target.chmod(0o644)
            if THEME.exists():
                shutil.rmtree(THEME)
            staged.rename(THEME)
        config = ('[Theme]\nCurrent=graphite\n'
                  'Font=monospace,10,-1,5,400,0,0,0,0,0\n')
        with tempfile.NamedTemporaryFile(dir=CONFIG.parent, mode='w', delete=False) as handle:
            handle.write(config)
            staged_config = Path(handle.name)
        staged_config.chmod(0o644)
        staged_config.replace(CONFIG)
        print('Installed Graphite SDDM theme. It will appear at the next login screen.')
        print('Backup:', backup)
        print('No packages installed; no services restarted; authentication settings retained.')
    except Exception:
        try:
            restore(backup)
        except Exception as error:
            print(f'SDDM rollback failed: {error}. Backup: {backup}')
        raise


def restore(path):
    if os.geteuid() != 0:
        raise RuntimeError('Restore needs administrator access.')
    path = Path(path).resolve()
    if path.parent != BACKUPS or not path.is_dir():
        raise RuntimeError('Select a backup directory directly under ' + str(BACKUPS))
    if any(target.is_symlink() for target in [THEME, CONFIG, THEME.parent, CONFIG.parent, BACKUPS]):
        raise RuntimeError('Refusing to restore over a symlink.')
    manifest_path = path / 'manifest.json'
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise RuntimeError('Backup manifest missing; no files changed. Recover legacy backups manually.')
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('version') != 1 or not all(isinstance(manifest.get(key), bool) for key in ['theme_existed', 'config_existed']):
        raise RuntimeError('Invalid SDDM backup manifest; no files changed.')
    for name, present in [('theme', manifest['theme_existed']), ('config', manifest['config_existed'])]:
        source = path / name
        if source.is_symlink() or (present and not (source.is_dir() if name == 'theme' else source.is_file())):
            raise RuntimeError('Incomplete or unsafe SDDM backup; no files changed.')
    if THEME.exists():
        shutil.rmtree(THEME)
    if manifest['theme_existed']:
        shutil.copytree(path / 'theme', THEME, symlinks=True)
    if manifest['config_existed']:
        shutil.copy2(path / 'config', CONFIG)
    else:
        CONFIG.unlink(missing_ok=True)
    print('SDDM theme restored. No service restart performed.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--restore', type=Path)
    args = parser.parse_args()
    try:
        if args.dry_run:
            source_files()
            runtime_check()
            print(f'Would install Graphite into {THEME} and select it in {CONFIG}.')
            print(f'Would back up existing targets under {BACKUPS}. No changes made.')
        elif args.restore:
            restore(args.restore)
        else:
            apply()
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError, configparser.Error) as error:
        parser.exit(1, str(error) + '\n')
