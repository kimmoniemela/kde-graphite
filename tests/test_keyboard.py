"""The optional AltGr mapping preserves normal Super keys and existing options."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import install


class KeyboardTests(unittest.TestCase):
    def test_keyboard_option_preserves_existing_layouts_rules_and_options(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory)
            install.atomic_write(config / 'kxkbrc', b'[Layout]\nLayoutList=fi,us\nVariantList=,\nOptions=grp:win_space_toggle,compose:menu\n')
            install.atomic_write(config / 'xkb/rules/evdev', b'! include %S/evdev\n// existing custom rules\n')
            files, groups = install.keyboard_configuration(config)
            for path, content in files.items():
                install.atomic_write(path, content)
            install.merge_config(config / 'kxkbrc', groups)
            settings = install.read_config(config / 'kxkbrc')['Layout']
            self.assertEqual(settings['LayoutList'], 'fi,us')
            self.assertEqual(settings['VariantList'], ',')
            self.assertEqual(settings['Options'], 'grp:win_space_toggle,compose:menu,graphite:altgr_super')
            again, _ = install.keyboard_configuration(config)
            self.assertEqual(again, files)
            self.assertIn(b'// existing custom rules', files[config / 'xkb/rules/evdev'])

    @unittest.skipUnless(shutil.which('xkbcli'), 'xkbcli is required for compiled keyboard checks')
    def test_altgr_and_both_super_keys_are_super_in_finnish_and_us(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory)
            files, _ = install.keyboard_configuration(config)
            for path, content in files.items():
                install.atomic_write(path, content)
            for layout in ['fi', 'us', 'fi,us']:
                with self.subTest(layout=layout):
                    keymap = subprocess.run(['xkbcli', 'compile-keymap', '--include', str(config / 'xkb'),
                        '--include-defaults', '--layout', layout, '--options', 'graphite:altgr_super'],
                        capture_output=True, text=True, check=True).stdout
                    for name, symbol in [('RALT', 'Super_R'), ('LWIN', 'Super_L'), ('RWIN', 'Super_R')]:
                        definition = re.search(r'key\s+<' + name + r'>\s*\{([^}]+)\}', keymap).group(1)
                        self.assertIn(symbol, definition)
                    mod4 = re.search(r'modifier_map Mod4\s*\{([^}]+)\}', keymap).group(1)
                    for name in ['RALT', 'LWIN', 'RWIN']:
                        self.assertIn('<' + name + '>', mod4)
                    for modifier in ['Mod1', 'Mod5']:
                        group = re.search(r'modifier_map ' + modifier + r'\s*\{([^}]+)\}', keymap)
                        if group:
                            self.assertNotIn('<RALT>', group.group(1))

    def test_environment_options_are_retained_without_user_keyboard_config(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(os.environ, XKB_DEFAULT_OPTIONS='compose:menu'):
            _, groups = install.keyboard_configuration(Path(directory))
        self.assertEqual(groups['Layout']['Options'], 'compose:menu,graphite:altgr_super')
