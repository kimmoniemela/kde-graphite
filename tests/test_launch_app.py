import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('launch_app', ROOT / 'scripts/launch-app.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class LauncherTests(unittest.TestCase):
    def test_default_terminal_tracks_preference_changes_between_launches(self):
        with patch.object(launcher.pathlib.Path, 'read_text',
                          return_value=json.dumps({'Terminal': ['@default']})), \
             patch.object(launcher.sys, 'argv', ['launch-app.py', 'Terminal']), \
             patch('applications.Path.is_file', return_value=True), \
             patch('applications.subprocess.check_output',
                          side_effect=['kitty.desktop\n', 'org.wezfurlong.wezterm.desktop\n']), \
             patch.object(launcher.os, 'execvp') as launch:
            launcher.main()
            launcher.main()
        self.assertEqual([call.args[1] for call in launch.call_args_list], [
            ['kstart', '--application', 'kitty'],
            ['kstart', '--application', 'org.wezfurlong.wezterm'],
        ])

    def test_legacy_terminal_command_preserves_quoted_arguments(self):
        with patch('applications.subprocess.check_output',
                          side_effect=['\n', 'kitty --title "My Terminal"\n']):
            self.assertEqual(launcher.default_command('Terminal'), ['kitty', '--title', 'My Terminal'])

    def test_unconfigured_kde_terminal_uses_kde_fallback(self):
        with patch('applications.subprocess.check_output', return_value='\n'), \
             patch('applications.shutil.which', side_effect=lambda app: '/bin/konsole' if app == 'konsole' else None):
            self.assertEqual(launcher.default_command('Terminal'), ['konsole'])

    def test_explicit_terminal_override_does_not_read_kde_preferences(self):
        with patch.object(launcher.pathlib.Path, 'read_text',
                          return_value=json.dumps({'Terminal': ['foot', '--login-shell']})), \
             patch.object(launcher.sys, 'argv', ['launch-app.py', 'Terminal']), \
             patch('applications.subprocess.check_output') as read_preference, \
             patch.object(launcher.os, 'execvp') as launch:
            launcher.main()
        read_preference.assert_not_called()
        self.assertEqual(launch.call_args.args[1], ['foot', '--login-shell'])


if __name__ == '__main__':
    unittest.main()
