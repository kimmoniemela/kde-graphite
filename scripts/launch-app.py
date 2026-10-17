#!/usr/bin/env python3
"""Run a configured shortcut command without tying its lifetime to KWin."""
import json
import pathlib
import subprocess
import sys

commands = json.loads(pathlib.Path(__file__).with_name("launchers.json").read_text())
subprocess.Popen(
    commands[sys.argv[1]],
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    start_new_session=True,
)
