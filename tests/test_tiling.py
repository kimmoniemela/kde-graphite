import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('tiling', ROOT / 'scripts/tiling-control.py')
tiling = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tiling)


class TilingTests(unittest.TestCase):
    def test_both_panels_toggle_current_running_state_and_save_choice(self):
        with tempfile.TemporaryDirectory() as directory:
            state = {'active': True, 'saved': True}
            def run(*args):
                state['saved'] = args[-1] == 'true'
            def kwin(path, method, *args):
                # Reconfiguring updates mode while retaining the loaded script.
                self.assertFalse(method.endswith('unloadScript'))
                self.assertFalse(method.endswith('start'))
                if method.endswith('reconfigure'):
                    self.fail('Runtime mode must not reconfigure KWin')
            with patch.dict(tiling.os.environ, {'XDG_RUNTIME_DIR': directory}), \
                 patch.object(tiling, 'available', return_value=True), \
                 patch.object(tiling, 'enabled', side_effect=lambda: state['active'] and state['saved']), \
                 patch.object(tiling, 'run', side_effect=run), \
                 patch.object(tiling, 'kwin', side_effect=kwin):
                self.assertFalse(tiling.change('toggle'))
                self.assertEqual(state, {'active': True, 'saved': False})
                self.assertTrue(tiling.change('toggle'))
                self.assertEqual(state, {'active': True, 'saved': True})
                self.assertTrue(tiling.change('on'))
                self.assertFalse(tiling.change('off'))

    def test_missing_tiler_does_not_write_configuration(self):
        with patch.object(tiling, 'available', return_value=False), patch.object(tiling, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'not installed'):
                tiling.change('toggle')
            run.assert_not_called()

    def test_failed_kwin_start_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(tiling.os.environ, {'XDG_RUNTIME_DIR': directory}), \
                 patch.object(tiling, 'available', return_value=True), \
                 patch.object(tiling, 'enabled', return_value=False), \
                 patch.object(tiling, 'run'), patch.object(tiling, 'kwin'), \
                 patch.object(tiling.time, 'monotonic', side_effect=[0, 5]):
                with self.assertRaisesRegex(RuntimeError, 'did not apply'):
                    tiling.change('on')
