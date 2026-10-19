"""Fresh-machine, failure-recovery and optional-application contracts."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import applications
import install


class ArchitectureTests(unittest.TestCase):
    def test_unavailable_optional_apps_do_not_claim_shortcuts(self):
        with patch.object(applications, 'default_command', return_value=None), \
             patch.object(applications.shutil, 'which', return_value=None):
            files = install.payload(install.settings(), Path('/tmp/new home/data'))
            commands = json.loads(files[Path('/tmp/new home/data/kde-graphite/runtime/launchers.json')])
            desktop = files[Path('/tmp/new home/data/kglobalaccel') / install.APPLICATION_COMPONENT].decode()
        self.assertEqual(commands, {})
        self.assertNotIn('[Desktop Action Calculator]', desktop)
        self.assertNotIn('[Desktop Action Terminal]', desktop)

    def test_optional_app_selection_uses_installed_calculator(self):
        with patch.object(applications.shutil, 'which', side_effect=lambda name: '/bin/app' if name == 'gnome-calculator' else None):
            self.assertEqual(applications.default_command('Calculator'), ['gnome-calculator'])

    def test_defaults_use_mime_preferences_and_reject_missing_desktop_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            desktop = root / 'applications/custom-editor.desktop'
            desktop.parent.mkdir()
            desktop.write_text('[Desktop Entry]\nType=Application\nExec=custom-editor\n')
            with patch.dict(os.environ, XDG_DATA_HOME=directory, XDG_DATA_DIRS=directory), \
                 patch.object(applications, 'query', return_value='custom-editor.desktop'), \
                 patch.object(applications.shutil, 'which', return_value='/bin/xdg-mime'):
                self.assertEqual(applications.default_command('Editor'), ['kstart', '--application', 'custom-editor'])
                desktop.unlink()
                self.assertIsNone(applications.default_command('Editor'))

    def test_installed_launcher_imports_without_source_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = install.payload(install.settings(), root)
            runtime = root / 'kde-graphite/runtime'
            for path, content in files.items():
                install.atomic_write(path, content)
            result = subprocess.run([sys.executable, '-I', '-c',
                'import runpy, sys; sys.path.insert(0, sys.argv[1]); '
                'runpy.run_path(sys.argv[1] + "/launch-app.py", run_name="import_check")', str(runtime)],
                cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_config_merge_preserves_comments_localizations_and_nested_groups(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config'
            path.write_text('# keep comment\n[General]\nName[fi]=Säilytä\nCommand=literal %f # text\n'
                            'Change[$e]=old\n\n[Containments][7]\nplugin=custom\n')
            install.merge_config(path, {'General': {'Change': 'new', 'Added': 'yes'}})
            first = path.read_bytes()
            install.merge_config(path, {'General': {'Change': 'new', 'Added': 'yes'}})
            self.assertEqual(path.read_bytes(), first)
            self.assertIn(b'# keep comment\n', first)
            self.assertIn('Name[fi]=Säilytä\n', first.decode())
            self.assertIn(b'Command=literal %f # text\n', first)
            self.assertIn(b'[Containments][7]\nplugin=custom\n', first)
            self.assertNotIn(b'Change[$e]', first)

    def test_config_merge_refuses_administrator_locked_preferences(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config'
            for original in ['[General][$i]\nChange=old\n', '[General]\nChange[$i]=old\n']:
                path.write_text(original)
                with self.assertRaisesRegex(RuntimeError, 'locked'):
                    install.merge_config(path, {'General': {'Change': 'new'}})
                self.assertEqual(path.read_text(), original)

    def test_late_install_failure_rolls_back_files_and_keeps_previous_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, data, state = [root / name for name in ['config', 'data', 'state']]
            config.mkdir()
            original = '# original\n[Windows]\nUnrelated=keep\n'
            (config / 'kwinrc').write_text(original)
            pointer = state / 'kde-graphite/latest-backup'
            install.atomic_write(pointer, b'/previous/backup\n')
            with patch.object(install, 'preflight'), patch.object(install, 'resolve_outputs', side_effect=lambda o: o), \
                 patch.object(install, 'run', return_value='monospace'), patch.object(install, 'dbus', return_value="('[]',)"), \
                 patch.object(install, 'clear_conflicts'), \
                 patch.object(install, 'native_shortcuts', side_effect=RuntimeError('simulated late failure')), \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, 'simulated late failure'):
                    install.apply(install.settings(), config, data, state)
            self.assertEqual((config / 'kwinrc').read_text(), original)
            self.assertEqual(pointer.read_text(), '/previous/backup\n')
            self.assertFalse((config / 'kdeglobals').exists())
            self.assertEqual(list(data.rglob('*.py')), [])

    def test_repeated_install_and_restore_walk_back_to_original(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, data, state = [root / name for name in ['config', 'data', 'state']]
            config.mkdir()
            original = '# original\n[Windows]\nUnrelated=keep\n'
            (config / 'kwinrc').write_text(original)
            with patch.object(install, 'preflight'), patch.object(install, 'resolve_outputs', side_effect=lambda o: o), \
                 patch.object(install, 'run', return_value='monospace'), patch.object(install, 'dbus', return_value="('[]',)"), \
                 patch.object(install, 'clear_conflicts'), patch.object(install, 'native_shortcuts'), \
                 contextlib.redirect_stdout(io.StringIO()):
                install.apply(install.settings(), config, data, state)
                first = (config / 'kwinrc').read_bytes()
                pointer = state / 'kde-graphite/latest-backup'
                first_backup = Path(pointer.read_text().strip())
                install.apply(install.settings(), config, data, state)
                self.assertEqual((config / 'kwinrc').read_bytes(), first)
                install.restore(Path(pointer.read_text().strip()))
                self.assertEqual(Path(pointer.read_text().strip()), first_backup)
                install.restore(first_backup)
            self.assertEqual((config / 'kwinrc').read_text(), original)
            self.assertFalse(pointer.exists())

    def test_incomplete_backup_is_rejected_before_any_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, second = root / 'first', root / 'second'
            first.write_text('before'); second.write_text('before')
            backup = install.Backup(root / 'state')
            backup.save([first, second])
            first.write_text('after'); second.write_text('after')
            (backup.path / '1').unlink()
            with self.assertRaisesRegex(RuntimeError, 'backup file'):
                install.restore_files(backup.path)
            self.assertEqual(first.read_text(), 'after')

    def test_empty_xdg_path_uses_default_and_relative_path_is_rejected(self):
        with patch.dict(os.environ, XDG_CONFIG_HOME=''):
            self.assertEqual(install.xdg_path('XDG_CONFIG_HOME', Path('/tmp/config')), Path('/tmp/config'))
        with patch.dict(os.environ, XDG_CONFIG_HOME='relative'):
            with self.assertRaisesRegex(ValueError, 'absolute'):
                install.xdg_path('XDG_CONFIG_HOME', Path('/tmp/config'))


if __name__ == '__main__':
    unittest.main()
