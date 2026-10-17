from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WindowControlsTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node is needed for the KWin window mock')
    def test_normal_window_controls_restore_after_reload_or_initial_floating(self):
        source = (ROOT / 'vendor/krohnkite/contents/code/script.js').read_text()
        wrapper = source[source.index('class KWinWindow {'):source.index('function debugWin(')]
        code = 'const LOG = null; let GRAPHITE_SCRIPT_ACTIVE = true;\n' + wrapper + """
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
wrapper.noBorderManaged = false;
client.noBorder = true;
wrapper.commit(undefined, false);
if (client.noBorder) throw Error('New floating window did not regain titlebar');
// Unloaded tiling must not change window decoration or geometry.
GRAPHITE_SCRIPT_ACTIVE = false;
client.noBorder = false;
wrapper.commit({x: 1}, true);
if (client.noBorder) throw Error('Unloaded tiler changed a window');
GRAPHITE_SCRIPT_ACTIVE = true;
// Preserve the original decoration policy for non-normal windows.
client.normalWindow = false;
client.noBorder = true;
wrapper.noBorderManaged = true;
wrapper.noBorderOriginal = true;
wrapper.commit(undefined, false);
if (!client.noBorder) throw Error('Non-normal window decoration was overridden');
"""
        subprocess.run(['node', '-e', code], capture_output=True, text=True, check=True)

    @unittest.skipUnless(shutil.which('node'), 'Node is needed for the KWin window mock')
    def test_controls_restore_at_startup_and_for_new_windows(self):
        script = (ROOT / 'templates/window-controls.js').read_text()
        mock = """
function Signal() { this.handlers = []; this.connect = fn => this.handlers.push(fn); this.emit = () => this.handlers.forEach(fn => fn()); }
const queue = [];
function QTimer() { this.timeout = new Signal(); this.start = () => queue.push(() => this.timeout.emit()); }
const normal = {normalWindow: true, noBorder: true};
const fullscreen = {normalWindow: true, fullScreen: true, noBorder: true};
const popup = {normalWindow: true, specialWindow: true, noBorder: true};
const clients = [normal, fullscreen, popup];
const workspace = {windowList: () => clients, windowAdded: new Signal()};
const options = {configChanged: new Signal()};
function drain() { while(queue.length) queue.shift()(); }
"""
        checks = """
drain();
if (normal.noBorder || !fullscreen.noBorder || !popup.noBorder) throw Error('Startup decoration policy incorrect');
const fresh = {normalWindow: true, noBorder: true};
clients.push(fresh);
workspace.windowAdded.emit();
drain();
if (fresh.noBorder) throw Error('New terminal did not regain controls');
fresh.noBorder = true;
options.configChanged.emit();
drain();
if (fresh.noBorder) throw Error('Configuration reload did not restore controls');
"""
        subprocess.run(['node', '-e', mock + script + checks], capture_output=True, text=True, check=True)


if __name__ == '__main__':
    unittest.main()
