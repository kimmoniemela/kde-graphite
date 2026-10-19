import ctypes.util
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('workspace_keys', ROOT/'scripts/workspace-keys.py')
keys = importlib.util.module_from_spec(spec)
spec.loader.exec_module(keys)


class WorkspaceKeysTests(unittest.TestCase):
    @unittest.skipUnless(ctypes.util.find_library('xkbcommon'), 'XKB is required')
    def test_shifted_number_row_follows_finnish_and_us_layouts(self):
        fi, us = keys.shifted_symbols('fi'), keys.shifted_symbols('us')
        self.assertEqual(fi[2], '"')
        self.assertEqual(us[2], '@')
        self.assertEqual(fi[7], '/')
        self.assertEqual(us[7], '&')
        self.assertIn('Meta+"', keys.sequences(2, fi[2]))
        self.assertNotIn('Meta+@', keys.sequences(2, fi[2]))
        self.assertEqual(keys.sequences(10, '')[0], 'Meta+Shift+0')

    @unittest.skipUnless(importlib.util.find_spec('PySide6'), 'PySide6 is required for shortcut keys')
    def test_layout_change_releases_previous_symbols_before_rebinding(self):
        calls = []
        def run(*args):
            calls.append(args)
            if args[-1].endswith('getLayoutsList'):
                return "([('fi', '', 'Finnish'), ('us', '', 'English')],)"
            return '(@as [],)'

        with patch.object(keys, '_last_symbols', None), patch.object(keys, 'run', side_effect=run), \
             patch.object(keys, 'shifted_symbols', return_value={n: '!' if n == 1 else '' for n in range(1,11)}):
            keys.apply_layout(0)
        setters = [call for call in calls if 'org.kde.KGlobalAccel.setShortcut' in call]
        self.assertEqual(len(setters), 20)
        self.assertTrue(all(len(__import__('json').loads(call[-2])) == 1 for call in setters[:10]))
        self.assertEqual(len(__import__('json').loads(setters[10][-2])), 3)

    @unittest.skipUnless(importlib.util.find_spec('PySide6'), 'PySide6 is required for shortcut keys')
    def test_layout_alias_conflict_does_not_modify_another_script(self):
        calls = []
        def run(*args):
            calls.append(args)
            if args[-1].endswith('getLayoutsList'):
                return "([('fi', '', 'Finnish')],)"
            return "(['kwin', 'IndependentScriptAction', 'Other', 'Other'],)"
        with patch.object(keys, '_last_symbols', None), patch.object(keys, 'run', side_effect=run), \
             patch.object(keys, 'shifted_symbols', return_value={n: '!' for n in range(1, 11)}):
            with self.assertRaisesRegex(RuntimeError, 'shortcut conflict'):
                keys.apply_layout(0)
        self.assertFalse(any('org.kde.KGlobalAccel.setShortcut' in call for call in calls))

    @unittest.skipUnless(importlib.util.find_spec('PySide6'), 'PySide6 is required for shortcut keys')
    def test_duplicate_layout_signal_does_not_register_shortcuts_again(self):
        symbols = {n: '!' for n in range(1, 11)}
        def run(*args):
            if args[-1].endswith('getLayoutsList'):
                return "([('fi', '', 'Finnish')],)"
            raise AssertionError('Unchanged layout must not touch shortcut registrations')
        with patch.object(keys, '_last_symbols', symbols), patch.object(keys, 'run', side_effect=run), \
             patch.object(keys, 'shifted_symbols', return_value=symbols):
            keys.apply_layout(0)
