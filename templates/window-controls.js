// SPDX-License-Identifier: MIT
// KDE-only policy: normal windows retain mouse controls, including tiled windows.
function restoreControls(window) {
    if (window && !window.deleted && window.normalWindow && !window.specialWindow && !window.fullScreen)
        window.noBorder = false;
}
function refreshControls() {
    workspace.windowList().forEach(restoreControls);
}
const pending = new QTimer();
pending.singleShot = true;
pending.interval = 150;
pending.timeout.connect(refreshControls);
workspace.windowAdded.connect(() => pending.start());
// KDE's script loader may still be processing a reconfiguration at this point.
if (typeof options !== 'undefined' && options.configChanged)
    options.configChanged.connect(() => pending.start());
pending.start();
