#!/usr/bin/env python3
"""Run a configured shortcut command without tying its lifetime to KWin."""
import json
import pathlib
import subprocess
import sys

from applications import DEFAULT, default_command

def terminal_command():
    return default_command('Terminal')


def main():
    commands = json.loads(pathlib.Path(__file__).with_name('launchers.json').read_text())
    name = sys.argv[1]
    command = commands[name]
    if command == DEFAULT:
        command = default_command('Calculator' if name == 'CalculatorKey' else name)
    if not command:
        raise RuntimeError('No application available for ' + name)
    subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print('Graphite launcher: ' + str(error), file=sys.stderr)
        sys.exit(1)
