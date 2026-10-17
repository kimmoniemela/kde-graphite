#!/usr/bin/env python3
"""Control KDE's Kröhnkite script; stdout is a single JSON status object."""
import argparse
import configparser
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time


def run(*args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=8)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or 'Command failed')
    return result.stdout.strip()


def kwin(path, method, *args):
    return run('gdbus', 'call', '--session', '--dest', 'org.kde.KWin',
               '--object-path', path, '--method', method, *args)


def enabled():
    return kwin('/Scripting', 'org.kde.kwin.Scripting.isScriptLoaded', 'krohnkite') == '(true,)'


def configured():
    config = configparser.ConfigParser(interpolation=None, strict=False)
    config.read(Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'kwinrc')
    return config.getboolean('Plugins', 'krohnkiteEnabled', fallback=False)


def available():
    roots = [os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))]
    roots += os.environ.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share').split(':')
    return any((Path(root) / 'kwin/scripts/krohnkite/metadata.json').is_file() for root in roots)


def change(action):
    """Serialize clicks from multiple panels; keep saved and running state aligned."""
    if not available():
        raise RuntimeError('Kröhnkite is not installed')
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR', '/tmp'))
    with (runtime / f'graphite-tiling-{os.getuid()}.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        target = not enabled() if action == 'toggle' else action == 'on'
        run('kwriteconfig6', '--file', 'kwinrc', '--group', 'Plugins',
            '--key', 'krohnkiteEnabled', str(target).lower())
        if not target:
            kwin('/Scripting', 'org.kde.kwin.Scripting.unloadScript', 'krohnkite')
        kwin('/KWin', 'org.kde.KWin.reconfigure')
        if target:
            kwin('/Scripting', 'org.kde.kwin.Scripting.start')
        deadline = time.monotonic() + 4
        while enabled() != target:
            if time.monotonic() >= deadline:
                raise RuntimeError('KWin did not apply the requested tiling mode')
            time.sleep(0.1)
        return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['status', 'on', 'off', 'toggle'])
    parser.add_argument('request_id', nargs='?')  # Distinct Plasma executable data sources.
    args = parser.parse_args()
    try:
        active = enabled() if args.action == 'status' else change(args.action)
        result = {'enabled': active, 'available': available(), 'error': ''}
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        result = {'enabled': None, 'available': False, 'error': str(error)}
    print(json.dumps(result))
    return 1 if result['error'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
