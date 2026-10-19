"""Optional end-to-end test using KDE's real shortcut host on a private bus.

Build tests/native and set GRAPHITE_NATIVE_SHORTCUT_HOST to shortcut-host.
No compositor or live desktop is contacted. Build dependencies are test-only.
"""
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import install


def probe(host):
    root = Path(os.environ['HOME'])
    data = Path(os.environ['XDG_DATA_HOME'])
    commands = root / 'bin'
    commands.mkdir()
    preferences = root / 'terminal-preference'
    preferences.write_text('kitty.desktop')
    record = root / 'records.jsonl'
    reader = commands / 'kreadconfig6'
    reader.write_text('#!' + sys.executable + '\nfrom pathlib import Path\nprint(Path(' + repr(str(preferences)) + ').read_text())\n')
    reader.chmod(0o755)
    starter = commands / 'kstart'
    starter.write_text('#!' + sys.executable + '\nimport json,sys\nwith open(' + repr(str(record)) + ',"a") as f: f.write(json.dumps(sys.argv[1:])+"\\n")\n')
    starter.chmod(0o755)
    for app in ['kitty', 'wezterm']:
        install.atomic_write(data / 'applications' / (app + '.desktop'), b'[Desktop Entry]\nType=Application\nName=Dummy\nExec=true\n')
    options = install.settings()
    options['applications'] = {name: [] for name in options['applications']}
    options['applications']['Terminal'] = ['@default']
    literal = 'spaces "quote" $money `ticks` \\slash %percent\nnewline'
    options['applications']['Editor'] = [sys.executable, str(starter), literal]
    options['applications']['ProcessMonitor'] = [str(starter), literal]
    for path, content in install.payload(options, data).items():
        install.atomic_write(path, content)
    process = subprocess.Popen([host], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    def call(method, *args):
        return install.dbus('org.kde.kglobalaccel', '/kglobalaccel', 'org.kde.KGlobalAccel.' + method, *args)
    def wait_records(count):
        for _ in range(100):
            if record.exists():
                values = [json.loads(line) for line in record.read_text().splitlines()]
                if len(values) >= count:
                    return values
            time.sleep(.05)
        raise RuntimeError('Native action did not launch: ' + str(count))
    try:
        for _ in range(100):
            try:
                reply = call('getComponent', install.APPLICATION_COMPONENT)
                break
            except RuntimeError:
                if process.poll() is not None:
                    raise RuntimeError(process.stderr.read())
                time.sleep(.05)
        else:
            raise RuntimeError('Native shortcut host did not start')
        path = ast.literal_eval(reply.replace('objectpath ', ''))[0]
        def invoke(action):
            install.dbus('org.kde.kglobalaccel', path, 'org.kde.kglobalaccel.Component.invokeShortcut', action)
        bindings = install.application_shortcuts({'Terminal': None, 'Editor': None})
        install.native_shortcuts(bindings)
        invoke('Terminal')
        assert wait_records(1)[0] == ['--application', 'kitty']
        preferences.write_text('wezterm.desktop')
        invoke('Terminal')
        assert wait_records(2)[1] == ['--application', 'wezterm']
        invoke('Terminal')
        assert wait_records(3)[2] == ['--application', 'wezterm']
        invoke('Editor')
        assert wait_records(4)[3] == [literal]
        invoke('ProcessMonitor')
        assert wait_records(5)[4] == [literal]
        # Prove runtime registration/persistence, not just desktop default discovery.
        install.native_shortcuts({(install.APPLICATION_COMPONENT, 'Editor'): 'Meta+Alt+T'})
        owner = call('shortcut', json.dumps([install.APPLICATION_COMPONENT, 'Editor', '', '']))
        from PySide6.QtGui import QKeySequence
        assert QKeySequence('Meta+Alt+T')[0].toCombined() in ast.literal_eval(owner)[0]
    finally:
        process.terminate()
        process.wait(timeout=5)
        if sys.exc_info()[0] is not None:
            print(process.stderr.read(), file=sys.stderr)
    print('Native actions: repeated launches, dynamic defaults, explicit argv, and API registration passed.')


class NativeShortcutTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('GRAPHITE_NATIVE_SHORTCUT_HOST'), 'Build tests/native to enable the private-bus integration test')
    def test_native_shortcut_execution(self):
        with tempfile.TemporaryDirectory(prefix='graphite native "$%` ') as directory:
            root = Path(directory)
            env = dict(os.environ, HOME=str(root), XDG_CONFIG_HOME=str(root / 'config'),
                       XDG_DATA_HOME=str(root / 'data'), XDG_CACHE_HOME=str(root / 'cache'),
                       XDG_STATE_HOME=str(root / 'state'), QT_QPA_PLATFORM='offscreen')
            env['PATH'] = str(root / 'bin') + os.pathsep + env['PATH']
            subprocess.run(['dbus-run-session', '--', sys.executable, __file__, '--probe',
                            os.environ['GRAPHITE_NATIVE_SHORTCUT_HOST']], env=env, check=True, timeout=25)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--probe':
        probe(sys.argv[2])
    else:
        unittest.main()
