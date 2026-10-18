"""Exercise the system-theme installer against temporary system directories."""
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('graphite_sddm', ROOT / 'sddm/install.py')
sddm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sddm)


class SddmTests(unittest.TestCase):
    def test_install_and_restore_touch_only_the_theme_and_its_dropin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            theme = root / 'themes/graphite'
            config = root / 'sddm.conf.d/99-graphite.conf'
            backups = root / 'backups'
            theme.mkdir(parents=True)
            (theme / 'original').write_text('old theme')
            config.parent.mkdir()
            config.write_text('[Theme]\nCurrent=breeze\n')
            unrelated = config.parent / 'autologin.conf'
            unrelated.write_text('[Autologin]\nSession=unchanged\n')
            with patch.multiple(sddm, THEME=theme, CONFIG=config, BACKUPS=backups), \
                 patch.object(sddm, 'runtime_check'), \
                 patch.object(sddm.os, 'geteuid', return_value=0), \
                 patch.object(sddm.configparser.ConfigParser, 'read'), \
                 contextlib.redirect_stdout(io.StringIO()):
                sddm.apply()
                self.assertTrue((theme / 'background.png').is_file())
                self.assertIn('Current=graphite', config.read_text())
                self.assertEqual((theme / 'Main.qml').stat().st_mode & 0o777, 0o644)
                sddm.restore(next(backups.iterdir()))
            self.assertEqual((theme / 'original').read_text(), 'old theme')
            self.assertEqual(config.read_text(), '[Theme]\nCurrent=breeze\n')
            self.assertEqual(unrelated.read_text(), '[Autologin]\nSession=unchanged\n')

    def test_empty_backup_cannot_delete_the_installed_login_theme(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            theme = root / 'themes/graphite'
            theme.mkdir(parents=True)
            (theme / 'original').write_text('keep')
            backup = root / 'backups/invalid'
            backup.mkdir(parents=True)
            with patch.multiple(sddm, THEME=theme, CONFIG=root/'config', BACKUPS=root/'backups'), \
                 patch.object(sddm.os, 'geteuid', return_value=0):
                with self.assertRaisesRegex(RuntimeError, 'manifest missing'):
                    sddm.restore(backup)
            self.assertEqual((theme / 'original').read_text(), 'keep')

    def test_late_config_failure_restores_previous_theme(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            theme = root / 'themes/graphite'
            theme.mkdir(parents=True)
            (theme / 'original').write_text('keep')
            config = root / 'conf.d/99-graphite.conf'
            config.parent.mkdir()
            config.write_text('[Theme]\nCurrent=old\n')
            with patch.multiple(sddm, THEME=theme, CONFIG=config, BACKUPS=root/'backups'), \
                 patch.object(sddm, 'runtime_check'), patch.object(sddm.os, 'geteuid', return_value=0), \
                 patch.object(sddm.configparser.ConfigParser, 'read'), \
                 patch.object(Path, 'replace', side_effect=OSError('simulated write failure')), \
                 contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(OSError, 'simulated write failure'):
                    sddm.apply()
            self.assertEqual((theme / 'original').read_text(), 'keep')
            self.assertEqual(config.read_text(), '[Theme]\nCurrent=old\n')

    def test_later_theme_override_fails_before_creating_backups(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / 'conf.d/99-graphite.conf'
            config.parent.mkdir()
            (config.parent / 'zz-local.conf').write_text('[Theme]\nCurrent=other\n')
            with patch.multiple(sddm, THEME=root/'themes/graphite', CONFIG=config,
                                MAIN_CONFIG=root/'sddm.conf', BACKUPS=root/'backups'), \
                 patch.object(sddm, 'runtime_check'), patch.object(sddm.os, 'geteuid', return_value=0):
                with self.assertRaisesRegex(RuntimeError, 'higher-priority'):
                    sddm.apply()
            self.assertFalse((root/'backups').exists())
