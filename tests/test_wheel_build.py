import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('build_wheel', Path(__file__).resolve().parents[1] / 'scripts/build-wheel.py')
wheel_build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wheel_build)


class WheelBuildTests(unittest.TestCase):
    def test_rebuild_replaces_plugin_atomically_and_unchanged_build_preserves_inode(self):
        with tempfile.TemporaryDirectory(prefix='graphite wheel ') as directory:
            root = Path(directory)
            wheel, state = root / 'wheel', root / 'state'
            target = wheel / 'qt6/plugins/kwin/effects/plugins' / wheel_build.PLUGIN
            target.parent.mkdir(parents=True)
            target.write_bytes(b'KWin old version')

            def cmake(command, **kwargs):
                if '--build' in command:
                    build = state / 'wheel-build'
                    build.mkdir(parents=True, exist_ok=True)
                    (build / wheel_build.PLUGIN).write_bytes(b'KWin new version')

            # A loaded compositor must retain an intact mapping of the old inode.
            with target.open('rb') as loaded, patch.object(wheel_build.subprocess, 'run', side_effect=cmake):
                wheel_build.rebuild(wheel, state)
                self.assertEqual(loaded.read(), b'KWin old version')
                self.assertEqual(target.read_bytes(), b'KWin new version')
                inode = target.stat().st_ino
                wheel_build.rebuild(wheel, state)
                self.assertEqual(target.stat().st_ino, inode)

    def test_failed_build_retains_previous_plugin_and_writes_log(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wheel, state = root / 'wheel', root / 'state'
            target = wheel / 'qt6/plugins/kwin/effects/plugins' / wheel_build.PLUGIN
            target.parent.mkdir(parents=True)
            target.write_bytes(b'previous plugin')

            def failure(command, **kwargs):
                kwargs['stdout'].write('missing matching KWin headers\n')
                raise subprocess.CalledProcessError(1, command)

            with patch.object(wheel_build.subprocess, 'run', side_effect=failure):
                with self.assertRaises(subprocess.CalledProcessError):
                    wheel_build.rebuild(wheel, state)
            self.assertEqual(target.read_bytes(), b'previous plugin')
            self.assertIn('missing matching KWin headers', (state / 'wheel-build.log').read_text())

    def test_disabled_or_missing_effect_does_not_run_build_tools(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / 'kwinrc'
            for contents in ['', '[Plugins]\nkwin_hypr_scroll_desktopEnabled=false\n']:
                config.write_text(contents)
                with patch.object(sys, 'argv', ['build-wheel.py', '--config', str(config), '--state', str(root / 'state')]), \
                     patch.object(wheel_build, 'rebuild', side_effect=AssertionError('Disabled effect must not build')):
                    self.assertEqual(wheel_build.main(), 0)
            self.assertFalse((root / 'state').exists())

    def test_build_error_reports_log_and_returns_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / 'kwinrc'
            config.write_text('[Plugins]\nkwin_hypr_scroll_desktopEnabled=true\n')
            with patch.object(sys, 'argv', ['build-wheel.py', '--config', str(config), '--state', str(root / 'state')]), \
                 patch.object(wheel_build, 'rebuild', side_effect=OSError('cmake missing')), \
                 contextlib.redirect_stderr(io.StringIO()) as error:
                self.assertEqual(wheel_build.main(), 1)
            self.assertIn('cmake missing', error.getvalue())
            self.assertIn('wheel-build.log', error.getvalue())
