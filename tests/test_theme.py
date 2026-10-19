import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import install
import theme


class ThemeTests(unittest.TestCase):
    def test_standalone_package_matches_canonical_palette_and_layout(self):
        options = {'font': 'Fira Code', 'font_size': 10}
        files = theme.package_files(options)
        self.assertEqual(files[Path('contents/colors')], (install.ROOT / 'assets/color-schemes/TerminalGraphite.colors').read_bytes())
        self.assertFalse(any('layouts' in path.parts for path in files))
        metadata = json.loads(files[Path('metadata.json')])
        self.assertEqual(metadata['KPackageStructure'], 'Plasma/LookAndFeel')
        self.assertEqual(metadata['KPlugin']['Name'], 'Graphite')
        for preview in ['preview.png', 'fullscreenpreview.jpg', 'lockscreen.png']:
            self.assertGreater(len(files[Path('contents/previews') / preview]), 1000)

    def test_theme_install_preserves_panels_workspaces_shortcuts_and_other_desktops(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, data, state = [root / name for name in ['config', 'data', 'state']]
            config.mkdir()
            original = {
                'kwinrc': '[Plugins]\nkrohnkiteEnabled=true\nkde-hypr-bridgeEnabled=true\n\n[Desktops]\nNumber=5\n\n[Windows]\nPerOutputVirtualDesktops=true\n\n[Script-kde-hypr-bridge]\nPrimaryOutput=DP-9\n',
                'kglobalshortcutsrc': '[kwin]\nWindow Close=Meta+Q,none,Close\n',
                'plasma-org.kde.plasma.desktop-appletsrc': '[Containments][7]\nplugin=org.kde.panel\n',
            }
            for name, text in original.items():
                (config / name).write_text(text)
            for name in ['hypr', 'sway', 'gtk-3.0']:
                (config / name).mkdir()
                (config / name / 'keep.conf').write_text('unchanged\n')
            protected = install.protected_hashes(config)
            api = SimpleNamespace(**{key: getattr(install, key) for key in ['read_config', 'merge_config', 'protected_hashes', 'Backup', 'transaction', 'atomic_write', 'plasma_script']},
                                  run=Mock(return_value='Fira Code'), dbus=Mock(), kwin=Mock())
            with patch('doctor.require'), patch('install.dbus', return_value="('[]',)"), \
                 patch.dict(os.environ, {'XDG_CURRENT_DESKTOP': 'KDE'}), contextlib.redirect_stdout(io.StringIO()):
                theme.install_theme(install.settings(), config, data, state, api)
            for name in ['kglobalshortcutsrc', 'plasma-org.kde.plasma.desktop-appletsrc']:
                self.assertEqual((config / name).read_text(), original[name])
            kwin = install.read_config(config / 'kwinrc')
            self.assertEqual(kwin['Plugins']['krohnkiteEnabled'], 'true')
            self.assertEqual(kwin['Plugins']['kde-hypr-bridgeEnabled'], 'true')
            self.assertEqual(kwin['Script-kde-hypr-bridge']['PrimaryOutput'], 'DP-9')
            self.assertEqual(kwin['Windows']['PerOutputVirtualDesktops'], 'true')
            self.assertEqual(kwin['Desktops']['Number'], '5')
            self.assertEqual(kwin['org.kde.kdecoration2']['ButtonsOnRight'], 'IAX')
            self.assertEqual(kwin['Windows']['BorderlessMaximizedWindows'], 'false')
            self.assertEqual(protected, install.protected_hashes(config))
            self.assertEqual(install.read_config(config / 'kdeglobals')['KDE']['LookAndFeelPackage'], theme.THEME_ID)
            self.assertTrue((data / 'plasma/look-and-feel' / theme.THEME_ID / 'metadata.json').exists())
            self.assertFalse((data / 'kwin/scripts').exists())
            backup = Path((state / 'kde-graphite/latest-backup').read_text().strip())
            install.restore_files(backup)
            self.assertEqual((config / 'kwinrc').read_text(), original['kwinrc'])
            self.assertFalse((config / 'kdedefaults/package').exists())

    @unittest.skipUnless(shutil.which('kpackagetool6'), 'KPackage tools are needed to validate native import')
    def test_archive_imports_as_graphite_in_an_isolated_kde_data_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = theme.build_archive(root / 'Graphite.tar.gz')
            env = dict(os.environ, QT_QPA_PLATFORM='offscreen', HOME=directory,
                       XDG_DATA_HOME=str(root / 'data'), XDG_CONFIG_HOME=str(root / 'config'),
                       XDG_CACHE_HOME=str(root / 'cache'), DBUS_SESSION_BUS_ADDRESS='unix:path=/nonexistent')
            subprocess.run(['kpackagetool6', '--type', 'Plasma/LookAndFeel', '--install', str(archive)],
                           env=env, text=True, capture_output=True, check=True)
            info = subprocess.run(['kpackagetool6', '--type', 'Plasma/LookAndFeel', '--show', theme.THEME_ID],
                                  env=env, text=True, capture_output=True, check=True).stdout
            self.assertIn('Name       : Graphite', info)
            self.assertIn('Plugin     : ' + theme.THEME_ID, info)
            self.assertIn(str(root / 'data/plasma/look-and-feel' / theme.THEME_ID), info)


if __name__ == '__main__':
    unittest.main()
