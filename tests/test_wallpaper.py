"""Native wallpaper scripting remains scoped to desktops and avoids no-op writes."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import install
import theme


class WallpaperTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node is required for Plasma scripting mocks')
    def test_wallpaper_apply_is_idempotent_and_does_not_manage_panels(self):
        script = theme.wallpaper_script(Path('/tmp/graphite wallpaper/data'))
        mock = """
let writes = 0;
const screens = [0,1,-1].map(screen => ({screen, wallpaperPlugin:'org.kde.image', config:{},
    readConfig(key, fallback) { return this.config[key] ?? fallback; },
    writeConfig(key, value) { this.config[key] = value; writes++; }
}));
function desktops() { return screens; }
function panels() { throw Error('Wallpaper script accessed user panels'); }
"""
        checks = """
if (writes !== 2) throw Error('Expected exactly one image write per active desktop');
if (screens[2].config.Image) throw Error('Changed an inactive desktop');
"""
        subprocess.run(['node', '-e', mock + script + checks + script + checks], check=True, capture_output=True, text=True)

    @unittest.skipUnless(shutil.which('node'), 'Node is required for Plasma scripting mocks')
    def test_restore_targets_saved_desktop_ids_and_keeps_new_desktops(self):
        with tempfile.TemporaryDirectory() as directory:
            backup = install.Backup(Path(directory))
            backup.flush()
            (backup.path / 'wallpaper.json').write_text(json.dumps([
                {'id': 7, 'plugin': 'org.kde.color', 'image': 'file:///previous image.png', 'fill': 1}]))
            with patch.object(install, 'dbus', return_value="('',)") as dbus:
                install.restore_files(backup.path)
            script = dbus.call_args.args[-1]
        mock = """
const ds = [7,9].map(id => ({id, wallpaperPlugin:'org.kde.image', config:{},
    writeConfig(k,v) { this.config[k] = v; }
}));
function desktops() { return ds; }
function panels() { throw Error('Restore accessed panels'); }
"""
        checks = """
if (ds[0].wallpaperPlugin !== 'org.kde.color' || ds[0].config.Image !== 'file:///previous image.png')
    throw Error('Original wallpaper was not restored');
if (Object.keys(ds[1].config).length) throw Error('Restore changed a new desktop');
"""
        subprocess.run(['node', '-e', mock + script + script + checks], check=True, capture_output=True, text=True)
