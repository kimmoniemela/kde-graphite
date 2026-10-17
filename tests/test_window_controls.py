from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WindowControlsTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node is needed for the KWin window mock')
    def test_floating_after_reload_restores_titlebar_but_tiling_stays_borderless(self):
        source = (ROOT / 'vendor/krohnkite/contents/code/script.js').read_text()
        wrapper = source[source.index('class KWinWindow {'):source.index('function debugWin(')]
        code = 'const LOG = null;\n' + wrapper + """
const client = {normalWindow: true, noBorder: true, move: false, resize: false};
const wrapper = Object.create(KWinWindow.prototype);
wrapper.window = client;
// Simulate a tiler reload while the existing tile was already borderless.
wrapper.noBorderManaged = true;
wrapper.noBorderOriginal = true;
wrapper.commit(undefined, false);
if (client.noBorder) throw Error('Floating window did not regain titlebar');
wrapper.commit(undefined, true);
if (!client.noBorder) throw Error('Tiled window gained unwanted chrome');
wrapper.commit(undefined, false);
if (client.noBorder) throw Error('Second float did not restore titlebar');
// Preserve the original decoration policy for non-normal windows.
client.normalWindow = false;
client.noBorder = true;
wrapper.noBorderManaged = true;
wrapper.noBorderOriginal = true;
wrapper.commit(undefined, false);
if (!client.noBorder) throw Error('Non-normal window decoration was overridden');
"""
        subprocess.run(['node', '-e', code], capture_output=True, text=True, check=True)


if __name__ == '__main__':
    unittest.main()
