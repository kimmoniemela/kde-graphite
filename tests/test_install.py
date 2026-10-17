import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installer', ROOT / 'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
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
        self.assertEqual(launchers['Terminal'], ['kitty'])
        self.assertIn(str(destination), launchers['Wallpaper'][1])
        qml = files[destination / 'kwin/scripts/kde-hypr-launchers-v2/contents/ui/main.qml'].decode()
        self.assertNotIn('@@', qml)
        self.assertIn("'/tmp/a different home/data/kde-graphite/runtime/launch-app.py'", qml)
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
            self.assertEqual(options['applications']['Terminal'], ['kitty'])
            self.assertEqual(options['primary_output'], 'DP-1')

    def test_monitor_selection_has_no_fixed_output_names(self):
        script = (ROOT / 'templates/workspaces.js').read_text()
        self.assertIn("readConfig('PrimaryOutput'", script)
        self.assertIn("readConfig('SecondaryOutput'", script)

    def test_move_shortcuts_use_native_monitor_local_actions(self):
        bindings = installer.shortcut_ids()
        for n in range(1, 6):
            self.assertEqual(bindings['kwin', f'Window to Desktop {n}'], f'Meta+Shift+{n}')

    @unittest.skipUnless(shutil.which('node'), 'Node is needed for the Plasma scripting mock')
    def test_panels_cover_each_screen_without_duplicates_or_shortcut_conflicts(self):
        script = (ROOT / 'templates/panel.js').read_text().replace('@@PANEL_HEIGHT@@', '28')
        script = script.replace('@@APPLICATION_TRAY_IDS@@', '[]')
        mock = """
const bars = [];
function Panel() {
    this.items = [];
    this.widgets = () => this.items;
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
