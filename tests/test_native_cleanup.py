"""Regression checks for native integration, no-op updates and scoped recovery."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import install
import theme


class NativeCleanupTests(unittest.TestCase):
    def test_unchanged_file_and_kconfig_writes_preserve_inode_and_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config'
            original = b'[General]\nValue=same\n'
            install.atomic_write(path, original)
            before = path.stat()
            install.atomic_write(path, original)
            install.merge_config(path, {'General': {'Value': 'same'}})
            after = path.stat()
            self.assertEqual((before.st_ino, before.st_mtime_ns), (after.st_ino, after.st_mtime_ns))

    @unittest.skipUnless(importlib.util.find_spec('PySide6'), 'PySide6 is required')
    def test_installer_preserves_alternative_keys_without_registering_again(self):
        from PySide6.QtGui import QKeySequence
        keys = [QKeySequence(key)[0].toCombined() for key in ['Meta+Q', 'Alt+F4']]
        with patch.object(install, 'dbus', return_value=repr((keys,))) as dbus:
            install.native_shortcuts({('kwin', 'Window Close'): 'Meta+Q'})
        self.assertEqual(dbus.call_count, 1)
        self.assertTrue(dbus.call_args.args[2].endswith('.shortcut'))

    def test_theme_never_generates_panels_or_broad_effect_preferences(self):
        groups = theme.configuration(install.settings(), install)
        self.assertNotIn('kded5rc', groups)
        self.assertNotIn('Plugins', groups['kwinrc'])
        self.assertNotIn('AnimationDurationFactor', groups['kdeglobals']['KDE'])
        self.assertFalse(any('layouts' in path.parts for path in theme.package_files(install.settings())))

    def test_install_preserves_unrelated_effects_names_layout_and_native_integrations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, data, state = [root / name for name in ['config', 'data', 'state']]
            config.mkdir()
            (config / 'kwinrc').write_text('[Plugins]\nblurEnabled=true\ncustom-scriptEnabled=true\n'
                '[Desktops]\nRows=5\nName_1=Personal\n[Windows]\nFocusPolicy=ClickToFocus\n')
            (config / 'kdeglobals').write_text('[KDE]\nAnimationDurationFactor=0.5\n')
            (config / 'kded5rc').write_text('[Module-gtkconfig]\nautoload=true\n')
            panels = config / 'plasma-org.kde.plasma.desktop-appletsrc'
            panels.write_text('personal panel layout\n')
            with patch.object(install, 'preflight'), patch.object(install, 'resolve_outputs', side_effect=lambda o: o), \
                 patch.object(install, 'run', return_value='Fira Code'), \
                 patch.object(install, 'dbus', return_value="('[]',)"), patch.object(install, 'clear_conflicts'), \
                 patch.object(install, 'native_shortcuts'), contextlib.redirect_stdout(io.StringIO()):
                install.apply(install.settings(), config, data, state)
                backup = Path((state / 'kde-graphite/latest-backup').read_text().strip())
                kwin = install.read_config(config / 'kwinrc')
                self.assertEqual(kwin['Plugins']['blurEnabled'], 'true')
                self.assertEqual(kwin['Plugins']['custom-scriptEnabled'], 'true')
                self.assertEqual(kwin['Desktops']['Name_1'], 'Personal')
                self.assertEqual(kwin['Desktops']['Rows'], '5')
                self.assertEqual(kwin['Windows']['FocusPolicy'], 'ClickToFocus')
                self.assertEqual(install.read_config(config / 'kdeglobals')['KDE']['AnimationDurationFactor'], '0.5')
                self.assertIn('autoload=true', (config / 'kded5rc').read_text())
                entries = json.loads((backup / 'manifest.json').read_text())
                self.assertNotIn(str(panels), [entry['path'] for entry in entries])
                panels.write_text('a later user panel edit\n')
                install.merge_config(config / 'kwinrc', {'Plugins': {'custom-scriptEnabled': 'false'},
                    'Script-independent-script': {'UserChoice': 'new'}, 'Desktops': {'Name_1': 'Later name'}})
                install.merge_config(config / 'kdeglobals', {'KDE': {'AnimationDurationFactor': '0.9'}})
                install.restore_files(backup)
                restored = install.read_config(config / 'kwinrc')
                self.assertEqual(restored['Plugins']['custom-scriptEnabled'], 'false')
                self.assertEqual(restored['Script-independent-script']['UserChoice'], 'new')
                self.assertEqual(restored['Desktops']['Name_1'], 'Later name')
                self.assertEqual(install.read_config(config / 'kdeglobals')['KDE']['AnimationDurationFactor'], '0.9')
                self.assertEqual(panels.read_text(), 'a later user panel edit\n')

    def test_legacy_whole_layout_backup_restores_only_wallpaper_through_plasma(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            panels = root / 'config/plasma-org.kde.plasma.desktop-appletsrc'
            install.atomic_write(panels, b'[Containments][1]\nplugin=org.kde.plasma.folder\nwallpaperplugin=org.kde.image\n'
                b'[Containments][1][Wallpaper][org.kde.image][General]\nImage=file:///old.png\n'
                b'[Containments][2]\nplugin=org.kde.panel\nlocation=top\n')
            backup = install.Backup(root / 'state')
            backup.save([panels])
            panels.write_text('new user panels\n')
            with patch.object(install, 'dbus', return_value="('',)") as dbus:
                install.restore_files(backup.path)
            self.assertEqual(panels.read_text(), 'new user panels\n')
            self.assertIn('file:///old.png', dbus.call_args.args[-1])
            self.assertNotIn('new Panel', dbus.call_args.args[-1])

    def test_upgrades_remove_unsafe_theme_layouts_without_removing_installed_widgets(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            old = data / 'plasma/look-and-feel' / theme.THEME_ID / 'contents/layouts/org.kde.plasma.desktop-layout.js'
            widget = data / 'plasma/plasmoids/org.kde.graphite.workspaces/metadata.json'
            install.atomic_write(old, b'old layout')
            install.atomic_write(widget, b'existing user panel component')
            self.assertIn(old, install.retired_files(data))
            self.assertNotIn(widget, install.retired_files(data))

    def test_retired_shortcut_cleanup_refuses_locked_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory)
            (config / 'kglobalshortcutsrc').write_text('[kwin]\nKdeHyprLaunchTerminal[$i]=Meta+Return,none,Terminal\n')
            with patch.object(install, 'dbus') as dbus:
                with self.assertRaisesRegex(RuntimeError, 'locked'):
                    install.retire_shortcuts(config)
                dbus.assert_not_called()

    @unittest.skipUnless(importlib.util.find_spec('PySide6'), 'PySide6 is required')
    def test_check_verifies_native_ownership_and_only_the_managed_script(self):
        from PySide6.QtGui import QKeySequence
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, data = root / 'config', root / 'data'
            install.atomic_write(config / 'kdeglobals', ('[KDE]\nLookAndFeelPackage=' + theme.THEME_ID + '\n').encode())
            install.atomic_write(config / 'kwinrc', b'[Plugins]\nkde-hypr-bridgeEnabled=true\nindependent-scriptEnabled=true\n')
            install.atomic_write(data / 'plasma/look-and-feel' / theme.THEME_ID / 'metadata.json', b'{}')
            install.atomic_write(data / 'kglobalaccel' / install.APPLICATION_COMPONENT, b'native service')
            install.atomic_write(config / 'autostart/org.kde.graphite.workspace-keys.desktop', b'autostart')
            install.atomic_write(data / 'kde-graphite/runtime/launchers.json', b'{"Terminal": ["@default"]}')
            bindings = {**install.shortcut_ids(), **install.application_shortcuts({'Terminal': None}),
                        **{(c,n): seq for c,n,seq in install.workspace_shortcuts()}}
            owners = {QKeySequence(seq)[0].toCombined(): [c,n,c,n]
                      for (c,n), sequences in bindings.items() for seq in sequences.split(';')}
            def dbus(*args):
                if args[2].endswith('.shortcut'):
                    component, name, *_ = json.loads(args[3])
                    return repr(([QKeySequence(s)[0].toCombined() for s in bindings[component,name].split(';')],))
                if args[2].endswith('.action'):
                    return repr((owners[int(args[3])],))
                return '(true,)'
            def kwin(path, method, *args):
                return '(true,)' if method.endswith('isScriptLoaded') else '(<uint32 5>,)'
            with patch.object(install, 'xdg_path', side_effect=lambda name, default: config if name == 'XDG_CONFIG_HOME' else data), \
                 patch.object(install, 'dbus', side_effect=dbus), patch.object(install, 'kwin', side_effect=kwin) as calls, \
                 contextlib.redirect_stdout(io.StringIO()):
                install.check(False)
                script_queries = [c.args[-1] for c in calls.call_args_list if c.args[1].endswith('isScriptLoaded')]
                self.assertEqual(script_queries, ['kde-hypr-bridge'])
                owners[QKeySequence('Meta+Q')[0].toCombined()] = ['kwin', 'IndependentScriptAction', '', '']
                with self.assertRaisesRegex(RuntimeError, 'conflicting handler'):
                    install.check(False)

    def test_scoped_restore_keeps_raw_flags_and_later_unrelated_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'settings'
            target.write_text('[General]\nValue[$e]=$HOME/original')
            backup = install.Backup(root / 'state')
            backup.save([target], {str(target): {'General': ['Value']}})
            target.write_text('[General]\nValue=new\nLater=user value\n')
            install.restore_files(backup.path)
            self.assertIn('Value[$e]=$HOME/original\n', target.read_text())
            self.assertIn('Later=user value\n', target.read_text())

    def test_legacy_kwin_restore_preserves_current_third_party_script_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'kwinrc'
            target.write_text('[Plugins]\nindependent-scriptEnabled=true\n'
                              '[Script-independent-script]\nPreference=old\n'
                              '[Windows]\nBorderlessMaximizedWindows=true\n')
            backup = install.Backup(root / 'state')
            backup.save([target])
            target.write_text('[Plugins]\nindependent-scriptEnabled=false\n'
                              '[Script-independent-script]\nPreference=later\n'
                              '[Windows]\nBorderlessMaximizedWindows=false\n')
            install.restore_files(backup.path)
            config = install.read_config(target)
            self.assertEqual(config['Plugins']['independent-scriptEnabled'], 'false')
            self.assertEqual(config['Script-independent-script']['Preference'], 'later')
            self.assertEqual(config['Windows']['BorderlessMaximizedWindows'], 'true')

    def test_scoped_restore_preserves_a_new_user_file_and_rejects_locks_before_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'settings'
            backup = install.Backup(root / 'state')
            backup.save([target], {str(target): {'General': ['Owned']}})
            target.write_text('[General]\nOwned=installed\nPersonal=later\n')
            install.restore_files(backup.path)
            self.assertIn('Personal=later', target.read_text())
            self.assertNotIn('Owned=', target.read_text())
            target.write_text('[General]\nOwned[$i]=locked\nPersonal=later\n')
            with self.assertRaisesRegex(RuntimeError, 'locked'):
                install.restore_files(backup.path)
            self.assertIn('Owned[$i]=locked', target.read_text())

    @unittest.skipUnless(importlib.util.find_spec('PySide6'), 'PySide6 is required')
    def test_conflict_backup_records_only_actual_native_owners_for_scoped_recovery(self):
        from PySide6.QtGui import QKeySequence
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'kglobalshortcutsrc'
            target.write_text('[services][org.kde.dolphin.desktop]\n_launch=Meta+E\n')
            backup = install.Backup(root / 'state')
            backup.save([target], {str(target): install.shortcut_groups([(install.APPLICATION_COMPONENT, 'Files')])})
            owner = ['org.kde.dolphin.desktop', '_launch', 'Dolphin', 'Launch']
            key = QKeySequence('Meta+E')[0].toCombined()
            with patch.object(install, 'dbus', side_effect=[repr((owner,)), repr(([key],)), '([],)']):
                install.clear_conflicts([(install.APPLICATION_COMPONENT, 'Files', 'Meta+E')], backup)
            target.write_text('[services][org.kde.dolphin.desktop]\n_launch=none\n'
                              '[kwin]\nIndependentScriptAction=Meta+Y,none,Personal\n')
            install.restore_files(backup.path)
            config = install.read_config(target)
            self.assertEqual(config['services][org.kde.dolphin.desktop']['_launch'], 'Meta+E')
            self.assertEqual(config['kwin']['IndependentScriptAction'], 'Meta+Y,none,Personal')
