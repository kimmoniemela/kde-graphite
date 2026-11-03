#!/usr/bin/env python3
"""Check the local wheel build before Plasma starts KWin; never install packages."""
import argparse
import configparser
import fcntl
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

PLUGIN = 'kwin_hypr_scroll_desktop.so'


def rebuild(wheel, state):
    state.mkdir(parents=True, exist_ok=True)
    build = state / 'wheel-build'
    target = wheel / 'qt6/plugins/kwin/effects/plugins' / PLUGIN
    # Serialize login/manual checks and retain the previous binary on failure.
    with (state / 'wheel-build.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with (state / 'wheel-build.log').open('w') as log:
            try:
                for command in [
                    ['cmake', '-S', str(wheel / 'source'), '-B', str(build), '-DCMAKE_BUILD_TYPE=Release'],
                    ['cmake', '--build', str(build), '--parallel', '2'],
                ]:
                    subprocess.run(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                   check=True, timeout=120)
            except (OSError, subprocess.SubprocessError) as error:
                print(error, file=log)
                raise
        source = build / PLUGIN
        if target.is_file() and source.read_bytes() == target.read_bytes():
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as temporary:
            replacement = Path(temporary.name)
        try:
            shutil.copy2(source, replacement)
            replacement.replace(target)
        finally:
            replacement.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--state', type=Path, required=True)
    args = parser.parse_args()
    try:
        config = configparser.ConfigParser(interpolation=None, strict=False)
        config.read(args.config)
        if config.getboolean('Plugins', 'kwin_hypr_scroll_desktopEnabled', fallback=False):
            rebuild(Path(__file__).resolve().parent, args.state)
    except (OSError, ValueError, configparser.Error, subprocess.SubprocessError) as error:
        print(f'Graphite wheel build failed: {error}. See {args.state / "wheel-build.log"}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
