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
            with self.assertRaisesRegex(RuntimeError, 'unmanaged KWin action'):
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
        files = installer.payload(options, destination, panel=True)
        launchers = json.loads(files[destination / 'kde-graphite/runtime/launchers.json'])
        self.assertEqual(launchers['Terminal'], ['@default'])
        qml = files[destination / 'kwin/scripts/kde-hypr-launchers-v2/contents/ui/main.qml'].decode()
        self.assertNotIn('@@', qml)
        self.assertIn("'/tmp/a different home/data/kde-graphite/runtime/launch-app.py'", qml)
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
            self.assertEqual(bindings['kwin', f'Window to Desktop {n}'], '')

    @unittest.skipUnless(shutil.which('node'), 'Node is needed for the KWin scripting mock')
    def test_number_keys_and_move_keys_share_the_same_monitor_destinations(self):
        script = (ROOT / 'templates/workspaces.js').read_text()
        mock = """
const primary = {name: 'PRIMARY'}, secondary = {name: 'SECONDARY'};
const callbacks = {}, asynchronous = [];
const workspace = {
    screens: [secondary, primary], desktops: [1,2,3,4,5], activeScreen: primary,
    activeWindow: {skipPager: false, noBorder: true, output: secondary, deleted: false, specialWindow: false},
    windowRemoved: {connect() {}},
    windowList: () => [],
    currentDesktopForScreen: s => ({name: '1'}),
    setCurrentDesktopForScreen: (d, s) => { workspace.selected = {d, s}; },
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
if (!w.minimized || !w.keepAbove || w.skipPager || !w.noBorder)
    throw Error('Scratchpad changed unrelated window properties');
callbacks['Meta+S']();
if (w.minimized || w.output !== primary || w.desktops[0].name !== '1')
    throw Error('Scratchpad did not restore on the focused workspace');
callbacks['Meta+S']();
if (!w.minimized) throw Error('Scratchpad did not hide');
"""
        subprocess.run(['node', '-e', mock + script + checks], check=True, capture_output=True, text=True)

    @unittest.skipUnless(shutil.which('node'), 'Node is needed for the Plasma scripting mock')
    def test_panels_cover_each_screen_without_duplicates_or_shortcut_conflicts(self):
        script = (ROOT / 'templates/panel.js').read_text().replace('@@PANEL_HEIGHT@@', '28')
        script = script.replace('@@APPLICATION_TRAY_IDS@@', '[]').replace('@@PRIMARY_OUTPUT@@', '"PRIMARY"')
        mock = """
const bars = [];
function Panel() {
    this.items = [];
    this.widgets = () => [...this.items];
    this.addWidget = type => {
        const w = {type, writeConfig() {}, remove: () => this.items.splice(this.items.indexOf(w), 1)};
        this.items.push(w);
        return w;
    };
    bars.push(this);
}
function panels() { return bars; }
function desktops() { return [0, 1].map(screen => ({screen, writeConfig() {}})); }
function print() {}
function verify() {
    if (bars.length !== 2 || new Set(bars.map(p => p.screen)).size !== 2)
        throw Error('Expected one panel per screen');
    if (bars.filter(p => p.items.some(w => w.globalShortcut === 'Meta+X')).length !== 1)
        throw Error('Expected exactly one tray keyboard shortcut');
}
"""
        # A reapply must reuse both bars; a live addition must leave the original intact.
        code = mock + script + '\nverify();\n' + script + '\nverify();\n'
        code += 'bars.pop(); const original = bars[0].items[0]; var graphiteOnlyMissing = true;\n'
        code += script + '\nverify(); if (bars[0].items[0] !== original) throw Error("Original bar changed");'
        subprocess.run(['node', '-e', code], check=True, capture_output=True, text=True)


if __name__ == '__main__':
    unittest.main()
