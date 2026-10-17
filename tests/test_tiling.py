import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('tiling', ROOT / 'widgets/org.kde.graphite.tiling/contents/code/tiling-control.py')
tiling = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tiling)


class TilingTests(unittest.TestCase):
    def test_both_panels_toggle_current_running_state_and_save_choice(self):
        with tempfile.TemporaryDirectory() as directory:
            state = {'active': True, 'saved': True}
            def run(*args):
                state['saved'] = args[-1] == 'true'
            def kwin(path, method, *args):
                if method.endswith('unloadScript'):
                    state['active'] = False
                elif method.endswith('start'):
                    state['active'] = state['saved']
            with patch.dict(tiling.os.environ, {'XDG_RUNTIME_DIR': directory}), \
                 patch.object(tiling, 'available', return_value=True), \
                 patch.object(tiling, 'enabled', side_effect=lambda: state['active']), \
                 patch.object(tiling, 'run', side_effect=run), \
                 patch.object(tiling, 'kwin', side_effect=kwin):
                self.assertFalse(tiling.change('toggle'))
                self.assertEqual(state, {'active': False, 'saved': False})
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
