from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT/'vendor/krohnkite/contents/code/script.js').read_text()


@unittest.skipUnless(shutil.which('node'), 'Node is required')
class TilerShutdownTests(unittest.TestCase):
    def test_shutdown_disconnects_window_signals_and_ignores_pending_callbacks(self):
        driver = SOURCE[SOURCE.index('class KWinDriver {'):SOURCE.index('KWinDriver.backendName =')]
        code = 'let GRAPHITE_TILING_ENABLED = true;\n' + driver + """
const driver = Object.create(KWinDriver.prototype);
Object.assign(driver, {workspace: {}, connections: [], entered: false, disposed: false});
const handlers = new Set();
const signal = {connect: fn => handlers.add(fn), disconnect: fn => handlers.delete(fn)};
let mutations = 0;
const pending = driver.connect(signal, () => mutations++);
pending();
if (mutations !== 1) throw Error('Handler did not run while enabled');
driver.shutdown();
if (handlers.size || GRAPHITE_TILING_ENABLED) throw Error('Shutdown retained window callbacks');
pending();
driver.enter(() => mutations++);
if (mutations !== 1) throw Error('An old callback changed a window after shutdown');
"""
        subprocess.run(['node', '-e', code], check=True, capture_output=True, text=True)

    def test_suspended_tiler_leaves_moves_resizes_and_desktop_changes_alone(self):
        controller = SOURCE[SOURCE.index('class TilingController {'):SOURCE.index('class TilingEngine {')]
        code = 'let GRAPHITE_TILING_ENABLED = false;\n' + controller + """
const controller = Object.create(TilingController.prototype);
const engine = new Proxy({}, {get() {throw Error('Disabled tiler changed layout');}});
controller.engine = engine;
const window = new Proxy({}, {get() {throw Error('Disabled tiler touched a window');}});
for (const method of ['onWindowDragging', 'onWindowMoveOver', 'onWindowResize', 'onWindowResizeOver', 'onWindowChanged'])
    controller[method]({}, window);
"""
        subprocess.run(['node', '-e', code], check=True, capture_output=True, text=True)
