import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installer', ROOT / 'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec('PySide6'), 'PySide6 is required for shortcut keys')
    def test_conflicts_release_only_the_conflicting_key(self):
        from PySide6.QtGui import QKeySequence
        requested = QKeySequence('Meta+Q')[0].toCombined()
        retained = QKeySequence('Alt+F4')[0].toCombined()
        owner = ['kwin', 'Window Fullscreen', 'KWin', 'Fullscreen']
        with patch.object(installer, 'dbus', side_effect=[repr((owner,)), repr(([requested, retained],)), '()']) as dbus:
            installer.clear_conflicts([('kwin', 'Window Close', 'Meta+Q')])
        self.assertEqual(json.loads(dbus.call_args.args[-2]), [retained])

    @unittest.skipUnless(importlib.util.find_spec('PySide6'), 'PySide6 is required for shortcut keys')
    def test_conflicts_preserve_independently_registered_kwin_actions(self):
        # Any unknown script action is protected, without knowing its package name.
        owner = ['kwin', 'IndependentScriptAction', 'KWin', 'Custom action']
        native = ['kwin', 'Window Fullscreen', 'KWin', 'Fullscreen']
        with patch.object(installer, 'dbus', side_effect=[repr((native,)), repr(([123],)), repr((owner,))]) as dbus:
            with self.assertRaisesRegex(RuntimeError, 'unmanaged shortcut action'):
                installer.clear_conflicts([('kwin', 'Window Close', 'Meta+Q;Meta+W')])
        # Even earlier native conflicts must remain unchanged when a script blocks installation.
        self.assertEqual(dbus.call_count, 3)
        self.assertTrue(all('setShortcut' not in call.args[2] for call in dbus.call_args_list))

    def test_merges_kconfig_without_overwriting_other_preferences(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'kwinrc'
            path.write_text('[Windows]\nUnrelated=keep\nFocusPolicy=ClickToFocus\n\n[Desktops]\nId_1=local-id\n')
            installer.merge_config(path, {'Windows': {'FocusPolicy': 'FocusFollowsMouse'}})
            config = installer.read_config(path)
            self.assertEqual(config['Windows']['Unrelated'], 'keep')
            self.assertEqual(config['Desktops']['Id_1'], 'local-id')
            self.assertEqual(config['Windows']['FocusPolicy'], 'FocusFollowsMouse')

    def test_backup_distinguishes_existing_and_created_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / 'old'; old.write_bytes(b'original\n')
            new = root / 'new'
            backup = installer.Backup(root / 'state')
            backup.save([old, new, old])
            old.write_text('changed'); new.write_text('created')
            records = json.loads((backup.path / 'manifest.json').read_text())
            self.assertEqual(len(records), 2)
            installer.restore_files(backup.path)
            self.assertEqual(old.read_bytes(), b'original\n')
            self.assertFalse(new.exists())

    def test_renders_for_destination_with_spaces_and_no_source_machine_paths(self):
        options = installer.settings()
        destination = Path('/tmp/a different home/data')
        files = installer.payload(options, destination)
        launchers = json.loads(files[destination / 'kde-graphite/runtime/launchers.json'])
        self.assertEqual(launchers['Terminal'], ['@default'])
        desktop = files[destination / 'kglobalaccel' / installer.APPLICATION_COMPONENT].decode()
        self.assertNotIn('@@', desktop)
        self.assertIn('"/tmp/a different home/data/kde-graphite/runtime/launch-app.py"', desktop)
        runtime = destination / 'kde-graphite/runtime'
        self.assertEqual({p.name for p in files if p.parent == runtime},
                         {'launch-app.py', 'workspace-keys.py', 'applications.py', 'launchers.json'})
        self.assertEqual({p.relative_to(destination / 'kwin/scripts').parts[0] for p in files
                          if p.is_relative_to(destination / 'kwin/scripts')}, set(installer.SCRIPTS))
        for path, content in files.items():
            self.assertTrue(path.is_relative_to(destination))
            if path.suffix in ['.qml', '.js', '.py', '.json']:
                self.assertNotIn(str(Path.home()).encode(), content)

    def test_local_settings_override_only_selected_applications(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'settings.json'
            path.write_text(json.dumps({'applications': {'Files': ['dolphin']}, 'primary_output': 'DP-1'}))
            options = installer.settings(path)
            self.assertEqual(options['applications']['Files'], ['dolphin'])
            self.assertEqual(options['applications']['Terminal'], ['@default'])
            self.assertEqual(options['primary_output'], 'DP-1')

    def test_output_mapping_uses_kde_priority_and_preserves_overrides(self):
        outputs = {'outputs': [
            {'name': 'INTERNAL', 'enabled': True, 'connected': True, 'priority': 2},
            {'name': 'EXTERNAL', 'enabled': True, 'connected': True, 'priority': 1},
            {'name': 'OFF', 'enabled': False, 'connected': True, 'priority': 0},
        ]}
        with patch.object(installer, 'run', return_value=json.dumps(outputs)):
            options = installer.resolve_outputs(installer.settings())
            self.assertEqual((options['primary_output'], options['secondary_output']), ('EXTERNAL', 'INTERNAL'))
            options['primary_output'] = 'INTERNAL'
            options['secondary_output'] = ''
            options = installer.resolve_outputs(options)
            self.assertEqual(options['secondary_output'], 'EXTERNAL')

    def test_monitor_selection_has_no_fixed_output_names(self):
        script = (ROOT / 'templates/workspaces.js').read_text()
        self.assertIn("readConfig('PrimaryOutput'", script)
        self.assertIn("readConfig('SecondaryOutput'", script)

    def test_native_move_shortcuts_leave_number_keys_for_monitor_aware_actions(self):
        bindings = installer.shortcut_ids()
        for n in range(1, 6):
            self.assertEqual(bindings['kwin', f'Switch to Desktop {n}'], f'Meta+Ctrl+{n}')
            self.assertNotIn(('kwin', f'Window to Desktop {n}'), bindings)

    @unittest.skipUnless(shutil.which('node'), 'Node is needed for the KWin scripting mock')
    def test_number_keys_and_move_keys_share_the_same_monitor_destinations(self):
        script = installer.workspace_script()
        mock = """
const primary = {name: 'PRIMARY'}, secondary = {name: 'SECONDARY'};
const callbacks = {}, asynchronous = [];
const selected = new Map([[primary, 1], [secondary, 2]]);
const workspace = {
    screens: [secondary, primary], desktops: [1,2,3,4,5], activeScreen: primary,
    activeWindow: {skipPager: false, noBorder: true, output: secondary, deleted: false, specialWindow: false},
    windowRemoved: {connect() {}},
    windowList: () => [],
    currentDesktopForScreen: s => selected.get(s),
    setCurrentDesktopForScreen: (d, s) => { workspace.selected = {d, s}; selected.set(s, d); },
    slotSwitchToNextScreen: () => { workspace.activeScreen = workspace.activeScreen === primary ? secondary : primary; },
    sendClientToScreen: (w, s) => {
        w.output = s;
        w.desktops = [1];
    }
};
function readConfig(name) { return name === 'PrimaryOutput' ? 'PRIMARY' : 'SECONDARY'; }
function registerShortcut(name, text, key, fn) { callbacks[key] = fn; }
function callDBus() { throw Error('Workspace actions must not invoke external shortcuts'); }
function print() {}
function QTimer() {
    this.timeout = {connect: fn => { this.callback = fn; }};
    this.start = () => asynchronous.push(this.callback);
}
function drain() { while (asynchronous.length) asynchronous.shift()(); }
"""
        checks = """
callbacks['Meta+2']();
drain();
if (selected.get(secondary) !== 2) throw Error('Primary switch changed the secondary desktop');
for (const n of [10,1,9,2,8,3,7,4,6,5]) {
    const output = n <= 5 ? primary : secondary;
    const desktop = (n - 1) % 5 + 1;
    callbacks['Meta+' + n % 10]();
    drain();
    if (workspace.selected.s !== output || workspace.selected.d !== desktop)
        throw Error('Wrong switch destination: ' + n);
    callbacks['Meta+Shift+' + n % 10]();
    drain();
    const w = workspace.activeWindow;
    if (w.output !== output || w.desktops[0] !== desktop || w.skipPager)
        throw Error('Wrong move destination or pager state: ' + n);
}
workspace.screens = [primary];
callbacks['Meta+0']();
drain();
if (workspace.selected.s !== primary || workspace.selected.d !== 5)
    throw Error('Single-monitor fallback failed');
const w = workspace.activeWindow;
w.noBorder = true;
w.skipPager = false;
callbacks['Meta+Shift+S']();
if (!w.minimized || w.keepAbove || w.skipPager || !w.noBorder)
    throw Error('Scratchpad changed unrelated window properties');
callbacks['Meta+S']();
if (w.minimized || w.output !== primary || w.desktops[0] !== 5)
    throw Error('Scratchpad did not restore on the focused workspace');
callbacks['Meta+S']();
if (!w.minimized || w.keepAbove) throw Error('Scratchpad did not restore keep-above state');
w.keepAbove = true;
callbacks['Meta+S']();
callbacks['Meta+S']();
if (!w.keepAbove) throw Error('Scratchpad changed a preexisting keep-above preference');
callbacks['Meta+Ctrl+Right']();
if (selected.get(primary) !== 5) throw Error('Next workspace must clamp at five');
callbacks['Meta+Ctrl+Left']();
if (selected.get(primary) !== 4) throw Error('Previous workspace failed');
callbacks['Meta+Ctrl+Shift+Left']();
if (w.desktops[0] !== 3 || selected.get(primary) !== 4)
    throw Error('Relative send followed the window or chose the wrong desktop');
workspace.windowList = () => [1,2].map(d => ({output:primary, desktops:[d], specialWindow:false, minimized:false}));
callbacks['Meta+Ctrl+Down']();
if (selected.get(primary) !== 3) throw Error('First empty desktop failed');
const ruled = {output:primary, desktops:[3], specialWindow:false, deleted:false, minimized:false};
Object.defineProperty(ruled, 'keepAbove', {get: () => false, set: () => {}});
workspace.activeWindow = ruled;
callbacks['Meta+Shift+S']();
callbacks['Meta+S']();
if (ruled.keepAbove) throw Error('Scratchpad overrode the effective native window rule');
callbacks['Meta+S']();
if (!ruled.minimized) throw Error('Rule-protected scratchpad did not hide');

"""
        subprocess.run(['node', '-e', mock + script + checks], check=True, capture_output=True, text=True)



if __name__ == '__main__':
    unittest.main()
