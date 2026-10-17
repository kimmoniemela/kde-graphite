import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import doctor
import install


class PortabilityTests(unittest.TestCase):
    def test_doctor_reports_all_missing_commands_without_modification(self):
        with patch('doctor.shutil.which', return_value=None), patch('doctor.os.geteuid', return_value=1000), \
             patch.dict(os.environ, {'XDG_CURRENT_DESKTOP': 'KDE', 'WAYLAND_DISPLAY': 'wayland-1'}):
            api = SimpleNamespace(kwin=Mock(), dbus=Mock())
            errors = doctor.problems(api, install.settings(), full=True)
            for command in ['gdbus', 'konsole', 'dolphin', 'wl-copy', 'kreadconfig6']:
                self.assertIn('Missing command: ' + command, errors)
            api.kwin.assert_not_called()
            api.dbus.assert_not_called()

    def test_theme_preflight_does_not_require_full_profile_tools_or_pyside(self):
        api = SimpleNamespace(kwin=Mock(return_value='KWin version: 6.5.2'), dbus=Mock())
        required = []
        def which(name):
            required.append(name)
            return '/bin/' + name
        with patch('doctor.shutil.which', side_effect=which), patch('doctor.os.geteuid', return_value=1000), \
             patch('doctor.Path.is_file', return_value=True), \
             patch.dict(os.environ, {'XDG_CURRENT_DESKTOP': 'KDE'}), \
             patch('doctor.importlib.util.find_spec', side_effect=AssertionError('Appearance must not import PySide')):
            self.assertEqual(doctor.problems(api, install.settings()), [])
        self.assertNotIn('kscreen-doctor', required)
        self.assertNotIn('konsole', required)

    def test_dry_runs_do_not_call_mutations_and_default_to_appearance(self):
        for args, function in [(['--dry-run'], 'apply'), (['restore', '--dry-run'], 'restore')]:
            with patch.object(sys, 'argv', ['install.py', *args]), \
                 patch.object(install, function, side_effect=AssertionError('Dry run mutated state')), \
                 patch('theme.install_theme', side_effect=AssertionError('Dry run applied theme')), \
                 contextlib.redirect_stdout(io.StringIO()) as output:
                install.main()
            self.assertIn('Would', output.getvalue())
            if args == ['--dry-run']:
                self.assertIn('retain panels', output.getvalue())
        self.assertIn('No changes made.', output.getvalue())

    def test_invalid_output_override_is_rejected_before_changes(self):
        options = install.settings()
        options['primary_output'] = 'OLD-MACHINE-DP-9'
        outputs = {'outputs': [{'name': 'eDP-1', 'enabled': True, 'connected': True, 'priority': 1}]}
        with patch.object(install, 'run', return_value=json.dumps(outputs)):
            with self.assertRaisesRegex(ValueError, 'not a connected output'):
                install.resolve_outputs(options)

    def test_full_install_to_fresh_xdg_directories_preserves_other_desktops_and_restores(self):
        with tempfile.TemporaryDirectory(prefix='graphite new home ') as directory:
            root = Path(directory)
            config, data, state = [root / name for name in ['config', 'data', 'state']]
            (config / 'hypr').mkdir(parents=True)
            (config / 'hypr/hyprland.conf').write_text('keep this\n')
            (config / 'kwinrc').write_text('[Windows]\nUnrelated=keep\n[Script-krohnkite]\nruntimeEnabled=false\n')
            obsolete = data / 'kde-graphite/runtime/tiling-control.py'
            obsolete.parent.mkdir(parents=True)
            obsolete.write_text('# superseded toggle\n')
            original = (config / 'kwinrc').read_bytes()
            protected = install.protected_hashes(config)
            options = install.settings()
            options.update(primary_output='PRIMARY', secondary_output='SECONDARY')
            with patch.object(install, 'preflight'), patch.object(install, 'resolve_outputs', return_value=options), \
                 patch.object(install, 'run', return_value='Fira Code'), patch.object(install, 'dbus'), \
                 patch.object(install, 'kwin', side_effect=AssertionError('Do not reload live KWin scripts')), \
                 patch.object(install, 'clear_conflicts'), patch.object(install, 'native_shortcuts'), \
                 contextlib.redirect_stdout(io.StringIO()):
                install.apply(options, config, data, state, panel=False)
            self.assertEqual(protected, install.protected_hashes(config))
            self.assertEqual(install.read_config(config / 'kwinrc')['Windows']['Unrelated'], 'keep')
            self.assertEqual(install.read_config(config / 'kwinrc')['org.kde.kdecoration2']['library'], 'org.kde.breeze')
            self.assertEqual(install.read_config(config / 'kwinrc')['Plugins'][install.WHEEL + 'Enabled'], 'false')
            shortcuts = install.read_config(config / 'kglobalshortcutsrc')['kwin']
            self.assertTrue(shortcuts['KdeHyprLaunchTerminal'].startswith('Meta+Return,'))
            self.assertTrue(shortcuts['KdeHyprSendDesktop10'].startswith('Meta+Shift+0,'))
            self.assertFalse((data / 'kde-graphite/runtime/tiling-control.py').exists())
            self.assertNotIn('runtimeEnabled', install.read_config(config / 'kwinrc')['Script-krohnkite'])
            self.assertTrue((data / 'plasma/plasmoids/org.kde.graphite.workspaces/metadata.json').is_file())
            self.assertFalse((data / 'plasma/plasmoids/org.kde.graphite.tiling/metadata.json').exists())
            backup = Path((state / 'kde-graphite/latest-backup').read_text().strip())
            with patch.object(install, 'restart_shell'), \
                 patch.object(install, 'kwin', side_effect=AssertionError('Restore must not unload live scripts')), \
                 contextlib.redirect_stdout(io.StringIO()):
                install.restore(backup)
            self.assertEqual((config / 'kwinrc').read_bytes(), original)
            self.assertEqual(protected, install.protected_hashes(config))
            self.assertEqual(obsolete.read_text(), '# superseded toggle\n')

    def test_missing_dependencies_leave_destination_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(install, 'preflight', side_effect=RuntimeError('Missing commands')):
                with self.assertRaisesRegex(RuntimeError, 'Missing commands'):
                    install.apply(install.settings(), root/'config', root/'data', root/'state')
            self.assertEqual(list(root.iterdir()), [])
