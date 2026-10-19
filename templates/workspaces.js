// KDE workspace and scratchpad bindings; output names are optional overrides.
function action(name, text, keys, fn) {
    registerShortcut('KdeHypr' + name, 'Graphite: ' + text, keys, fn);
}
const pendingTimers = new Set();
const idleTimers = [];
function later(delay, callback) {
    let job = idleTimers.pop();
    if (!job) {
        job = {timer: new QTimer(), callback: null};
        job.timer.singleShot = true;
        job.timer.timeout.connect(() => {
            const run = job.callback;
            job.callback = null;
            pendingTimers.delete(job);
            idleTimers.push(job);
            run();
        });
    }
    job.callback = callback;
    job.timer.interval = delay;
    pendingTimers.add(job);
    job.timer.start();
}
function screenForNumber(n) {
    const screens = workspace.screens;
    const primaryName = readConfig('PrimaryOutput', '');
    const secondaryName = readConfig('SecondaryOutput', '');
    const primary = screens.find(s => s.name === primaryName) || screens[0];
    const secondary = screens.find(s => s.name === secondaryName) || screens.find(s => s !== primary) || primary;
    return n <= 5 ? primary : secondary;
}
function current(screen) { return workspace.currentDesktopForScreen(screen); }
function focusScreen(screen) {
    for (let i = 0; i < workspace.screens.length && workspace.activeScreen !== screen; i++) {
        workspace.slotSwitchToNextScreen();
    }
}
function switchNumber(n) {
    const screen = screenForNumber(n);
    const desktop = workspace.desktops[(n - 1) % 5];
    focusScreen(screen);
    // Native screen focus may first activate a window on its previous desktop.
    later(30, () => {
        workspace.setCurrentDesktopForScreen(desktop, screen);
        const windows = workspace.windowList().filter(w => !w.specialWindow && !w.minimized && w.output === screen &&
            (w.desktops.length === 0 || w.desktops.indexOf(desktop) >= 0));
        if (windows.length) workspace.activeWindow = windows[windows.length - 1];
    });
}
function sendNumber(n) {
    const w = workspace.activeWindow;
    if (!w || w.specialWindow) return;
    const screen = screenForNumber(n);
    const desktop = workspace.desktops[(n - 1) % 5];
    workspace.sendClientToScreen(w, screen);
    w.desktops = [desktop];
}
function bank(screen) { return 0; } // Five native desktops, independently selected on each output.
function relative(delta, move) {
    const screen = workspace.activeScreen;
    const first = bank(screen);
    const index = workspace.desktops.indexOf(current(screen));
    const target = Math.max(first, Math.min(first + 4, index + delta));
    if (move) {
        const w = workspace.activeWindow;
        if (w && !w.specialWindow) w.desktops = [workspace.desktops[target]];
    } else workspace.setCurrentDesktopForScreen(workspace.desktops[target], screen);
}
function nextEmpty() {
    const screen = workspace.activeScreen, first = bank(screen);
    const windows = workspace.windowList();
    for (let i = first; i < first + 5; i++) {
        const d = workspace.desktops[i];
        if (!windows.some(w => !w.specialWindow && w.output === screen && !w.minimized && (w.desktops.length === 0 || w.desktops.indexOf(d) >= 0))) {
            workspace.setCurrentDesktopForScreen(d, screen); return;
        }
    }
}
for (let n = 1; n <= 10; n++) {
    const number = n, key = n % 10;
    action('Desktop' + n, 'Workspace ' + n, 'Meta+' + key, () => switchNumber(number));
    action('SendDesktop' + n, 'Send window to workspace ' + n, 'Meta+Shift+' + key, () => sendNumber(number));
}
for (let n = 1; n <= 5; n++) {
    const number = n;
    action('LocalDesktop' + n, 'Workspace ' + n + ' on this monitor', 'Meta+Ctrl+' + n,
        () => workspace.setCurrentDesktopForScreen(workspace.desktops[bank(workspace.activeScreen) + number - 1], workspace.activeScreen));
}
action('WorkspaceNext', 'Next workspace', 'Meta+Ctrl+Right', () => relative(1, false));
action('WorkspacePrev', 'Previous workspace', 'Meta+Ctrl+Left', () => relative(-1, false));
action('SendNext', 'Send window to next workspace', 'Meta+Ctrl+Shift+Right', () => relative(1, true));
action('SendPrev', 'Send window to previous workspace', 'Meta+Ctrl+Shift+Left', () => relative(-1, true));
action('Empty', 'Next empty workspace on this monitor', 'Meta+Ctrl+Down', nextEmpty);
action('MonitorPrev', 'Move window to previous monitor', '', () => {
    const w = workspace.activeWindow;
    workspace.slotWindowToPrevScreen();
    if (w) w.desktops = [current(w.output)];
});
action('MonitorNext', 'Move window to next monitor', '', () => {
    const w = workspace.activeWindow;
    workspace.slotWindowToNextScreen();
    if (w) w.desktops = [current(w.output)];
});
let scratch = [], scratchVisible = false;
action('ScratchSend', 'Send window to scratchpad', 'Meta+Shift+S', () => {
    const w = workspace.activeWindow;
    if (!w || w.specialWindow) return;
    if (!scratch.some(x => x.window === w)) scratch.push({window:w});
    w.keepAbove = true;
    w.minimized = true;
    scratchVisible = false;
});
action('ScratchToggle', 'Toggle scratchpad', 'Meta+S', () => {
    scratch = scratch.filter(x => !x.window.deleted);
    scratchVisible = !scratchVisible;
    for (const item of scratch) {
        const w = item.window;
        if (scratchVisible) {
            workspace.sendClientToScreen(w, workspace.activeScreen);
            w.desktops = [current(workspace.activeScreen)];
            w.minimized = false;
            workspace.activeWindow = w;
        } else w.minimized = true;
    }
});
workspace.windowRemoved.connect(w => { scratch = scratch.filter(x => x.window !== w); });
print('KDE_HYPR_BRIDGE_READY ' + JSON.stringify({screens:workspace.screens.map(s=>({name:s.name,desktop:current(s).name})),desktops:workspace.desktops.map(d=>d.name)}));
