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
    def test_wheel_install_is_user_only_and_restorable_without_tiler_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, data, state = [root / name for name in ['config', 'data', 'state']]
            config.mkdir()
            original = '[Plugins]\nkde-hypr-bridgeEnabled=true\nkrohnkiteEnabled=false\n[Script-krohnkite]\ncustom=keep\n'
            (config / 'kwinrc').write_text(original)
            build = root / 'build/wheel'
            build.mkdir(parents=True)
            (build / (install.WHEEL + '.so')).write_bytes(b'new plugin')
            plugin = data / 'kde-graphite/wheel/qt6/plugins/kwin/effects/plugins' / (install.WHEEL + '.so')
            plugin.parent.mkdir(parents=True)
            plugin.write_bytes(b'old plugin')
            old_inode = plugin.stat().st_ino
            with patch.object(install, 'ROOT', root), patch.object(install, 'run') as run, \
                 patch.object(install.shutil, 'which', return_value='/installed/tool'), \
                 patch.object(install.os, 'geteuid', return_value=1000), \
                 contextlib.redirect_stdout(io.StringIO()):
                install.install_wheel(config, data, state)
            self.assertTrue(all(call.args[0] == 'cmake' for call in run.call_args_list))
            self.assertEqual(plugin.read_bytes(), b'new plugin')
            self.assertNotEqual(plugin.stat().st_ino, old_inode)
            self.assertEqual(install.read_config(config / 'kwinrc')['Script-krohnkite']['custom'], 'keep')
            self.assertEqual(install.read_config(config / 'kwinrc')['Plugins']['krohnkiteEnabled'], 'false')
            backup = Path((state / 'kde-graphite/latest-backup').read_text().strip())
            install.restore_files(backup)
            self.assertEqual(plugin.read_bytes(), b'old plugin')
            self.assertEqual((config / 'kwinrc').read_text(), original)
            self.assertFalse((config / 'plasma-workspace/env/graphite-wheel.sh').exists())

    def test_install_preserves_third_party_scripts_effects_and_bars(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, data, state = [root / name for name in ['config', 'data', 'state']]
            config.mkdir()
            (config / 'kwinrc').write_text('[Plugins]\nkrohnkiteEnabled=false\ngraphite-window-controlsEnabled=true\n'
                                          + install.WHEEL + 'Enabled=true\n'
                                          '[Script-krohnkite]\ncustom=value\nruntimeEnabled=false\n'
                                          '[Windows]\nFocusPolicy=ClickToFocus\n')
            (config / 'kglobalshortcutsrc').write_text('[kwin]\nKrohnkiteFocusLeft=Meta+Left,none,Focus\nOverview=Meta+O,none,Overview\n')
            applets = config / 'plasma-org.kde.plasma.desktop-appletsrc'
            applets.write_text('existing bars\n')
            tiler = data / 'kwin/scripts/krohnkite/contents/code/script.js'
            tiler.parent.mkdir(parents=True)
            tiler.write_bytes(b'existing tiler')
            helper = data / 'kwin/scripts/graphite-window-controls/contents/code/main.js'
            helper.parent.mkdir(parents=True)
            helper.write_bytes(b'existing helper')
            runtime = data / 'kde-graphite/runtime'
            runtime.mkdir(parents=True)
            for filename in install.RETIRED_UTILITIES.values():
                (runtime / filename).write_bytes(b'old Graphite utility')
            with (config / 'kglobalshortcutsrc').open('a') as handle:
                for name in install.RETIRED_UTILITIES:
                    handle.write('KdeHyprLaunch' + name + '=Meta+P,none,Old utility\n')
            with patch.object(install, 'preflight'), patch.object(install, 'resolve_outputs', side_effect=lambda o: o), \
                 patch.object(install, 'run', return_value='Fira Code'), patch.object(install, 'dbus'), \
                 patch.object(install, 'clear_conflicts'), patch.object(install, 'native_shortcuts'), \
                 patch.object(install, 'restart_shell', side_effect=AssertionError('Do not restart Plasma')), \
                 contextlib.redirect_stdout(io.StringIO()):
                install.apply(install.settings(), config, data, state)
            kwin = install.read_config(config / 'kwinrc')
            self.assertEqual(dict(kwin['Script-krohnkite']), {'custom': 'value', 'runtimeEnabled': 'false'})
            self.assertEqual(kwin['Plugins']['krohnkiteEnabled'], 'false')
            self.assertEqual(kwin['Plugins']['graphite-window-controlsEnabled'], 'true')
            self.assertEqual(kwin['Plugins'][install.WHEEL + 'Enabled'], 'true')
            self.assertEqual(kwin['Windows']['FocusPolicy'], 'ClickToFocus')
            self.assertEqual(tiler.read_bytes(), b'existing tiler')
            self.assertEqual(applets.read_text(), 'existing bars\n')
            shortcuts = install.read_config(config / 'kglobalshortcutsrc')['kwin']
            self.assertEqual(shortcuts['KrohnkiteFocusLeft'], 'Meta+Left,none,Focus')
            self.assertEqual(shortcuts['Overview'], 'Meta+O,none,Overview')
            self.assertEqual(helper.read_bytes(), b'existing helper')
            for name, filename in install.RETIRED_UTILITIES.items():
                self.assertNotIn('KdeHyprLaunch' + name, shortcuts)
                self.assertFalse((runtime / filename).exists())
            backup = Path((state / 'kde-graphite/latest-backup').read_text().strip())
            entries = json.loads((backup / 'manifest.json').read_text())
            self.assertFalse(any(Path(entry['path']).is_relative_to(data / 'kwin/scripts/krohnkite') for entry in entries))
            install.restore_files(backup)
            for filename in install.RETIRED_UTILITIES.values():
                self.assertEqual((runtime / filename).read_bytes(), b'old Graphite utility')

    def test_doctor_uses_qt_runtime_without_development_tools(self):
        api = SimpleNamespace(kwin=Mock(return_value='KWin version: 6.7.5'),
                              dbus=Mock(side_effect=RuntimeError('stop before widget query')),
                              run=Mock(return_value='/usr/lib/qt6/qml'))
        def which(name):
            return None if name in ['qtpaths6', 'qtpaths-qt6'] else name
        with patch('doctor.shutil.which', side_effect=which), \
             patch('doctor.os.geteuid', return_value=1000), \
             patch('doctor.Path.is_file', return_value=True), \
             patch('doctor.importlib.util.find_spec', return_value=True), \
             patch('doctor.qml_import_path', return_value=Path('/runtime/qt6/qml')) as qml_import_path, \
             patch('doctor.importlib.import_module'), \
             patch.dict(os.environ, {'XDG_CURRENT_DESKTOP': 'KDE', 'WAYLAND_DISPLAY': 'wayland-1'}):
            errors = doctor.problems(api, install.settings(), full=True)
        api.run.assert_not_called()
        qml_import_path.assert_called_once_with()
        self.assertFalse(any('Missing command: qtpaths' in error for error in errors))

    def test_doctor_reports_all_missing_commands_without_modification(self):
        with patch('doctor.shutil.which', return_value=None), patch('doctor.os.geteuid', return_value=1000), \
             patch.dict(os.environ, {'XDG_CURRENT_DESKTOP': 'KDE', 'WAYLAND_DISPLAY': 'wayland-1'}):
            api = SimpleNamespace(kwin=Mock(), dbus=Mock())
            errors = doctor.problems(api, install.settings(), full=True)
            for command in ['gdbus', 'kstart', 'kscreen-doctor', 'kreadconfig6']:
                self.assertIn('Missing command: ' + command, errors)
            self.assertFalse(any('dolphin' in error for error in errors))
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
        for args, function in [(['--dry-run'], 'apply'), (['restore', '--dry-run'], 'restore'),
                               (['wheel', '--dry-run'], 'install_wheel')]:
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
            (config / 'kwinrc').write_text('[Windows]\nUnrelated=keep\n')
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
            self.assertNotIn(install.WHEEL + 'Enabled', install.read_config(config / 'kwinrc')['Plugins'])
            shortcuts = install.read_config(config / 'kglobalshortcutsrc')['kwin']
            self.assertTrue(shortcuts['KdeHyprLaunchTerminal'].startswith('Meta+Return,'))
            self.assertTrue(shortcuts['KdeHyprSendDesktop10'].startswith('Meta+Shift+0,'))
            self.assertFalse((data / 'plasma/plasmoids/org.kde.graphite.workspaces/metadata.json').is_file())
            backup = Path((state / 'kde-graphite/latest-backup').read_text().strip())
            with patch.object(install, 'restart_shell'), \
                 patch.object(install, 'kwin', side_effect=AssertionError('Restore must not unload live scripts')), \
                 contextlib.redirect_stdout(io.StringIO()):
                install.restore(backup)
            self.assertEqual((config / 'kwinrc').read_bytes(), original)
            self.assertEqual(protected, install.protected_hashes(config))

    def test_missing_dependencies_leave_destination_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(install, 'preflight', side_effect=RuntimeError('Missing commands')):
                with self.assertRaisesRegex(RuntimeError, 'Missing commands'):
                    install.apply(install.settings(), root/'config', root/'data', root/'state')
            self.assertEqual(list(root.iterdir()), [])
