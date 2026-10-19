// KDE workspace and scratchpad bindings; output names are optional overrides.
const shortcuts = @@WORKSPACE_SHORTCUTS@@;
function action(name, text, fn) {
    registerShortcut('KdeHypr' + name, 'Graphite: ' + text, shortcuts[name] || '', fn);
}
// Keep active, unparented QTimers reachable until their callbacks complete.
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
function relative(delta, move) {
    const screen = workspace.activeScreen;
    const index = workspace.desktops.indexOf(current(screen));
    const target = Math.max(0, Math.min(4, index + delta));
    if (move) {
        const w = workspace.activeWindow;
        if (w && !w.specialWindow) w.desktops = [workspace.desktops[target]];
    } else workspace.setCurrentDesktopForScreen(workspace.desktops[target], screen);
}
function nextEmpty() {
    const screen = workspace.activeScreen;
    const windows = workspace.windowList();
    for (let i = 0; i < 5; i++) {
        const d = workspace.desktops[i];
        if (!windows.some(w => !w.specialWindow && w.output === screen && !w.minimized && (w.desktops.length === 0 || w.desktops.indexOf(d) >= 0))) {
            workspace.setCurrentDesktopForScreen(d, screen); return;
        }
    }
}
for (let n = 1; n <= 10; n++) {
    const number = n;
    action('Desktop' + n, 'Workspace ' + n, () => switchNumber(number));
    action('SendDesktop' + n, 'Send window to workspace ' + n, () => sendNumber(number));
}
action('WorkspaceNext', 'Next workspace', () => relative(1, false));
action('WorkspacePrev', 'Previous workspace', () => relative(-1, false));
action('SendNext', 'Send window to next workspace', () => relative(1, true));
action('SendPrev', 'Send window to previous workspace', () => relative(-1, true));
action('Empty', 'Next empty workspace on this monitor', nextEmpty);
let scratch = [], scratchVisible = false;
function hideScratchpad() {
    for (const item of scratch) {
        const w = item.window;
        if (w.deleted) continue;
        w.minimized = true;
        // Undo only the keep-above change made while showing this scratchpad.
        if (item.raised && w.keepAbove) w.keepAbove = item.keepAbove;
        item.raised = false;
    }
    scratchVisible = false;
}
action('ScratchSend', 'Send window to scratchpad', () => {
    const w = workspace.activeWindow;
    if (!w || w.specialWindow) return;
    if (!scratch.some(x => x.window === w)) scratch.push({window:w});
    hideScratchpad();
});
action('ScratchToggle', 'Toggle scratchpad', () => {
    scratch = scratch.filter(x => !x.window.deleted);
    if (scratchVisible) { hideScratchpad(); return; }
    scratchVisible = true;
    for (const item of scratch) {
        const w = item.window;
        workspace.sendClientToScreen(w, workspace.activeScreen);
        w.desktops = [current(workspace.activeScreen)];
        item.keepAbove = w.keepAbove;
        if (!w.keepAbove) w.keepAbove = true;
        item.raised = w.keepAbove !== item.keepAbove;
        w.minimized = false;
        workspace.activeWindow = w;
    }
});
workspace.windowRemoved.connect(w => { scratch = scratch.filter(x => x.window !== w); });
print('KDE_HYPR_BRIDGE_READY ' + JSON.stringify({screens:workspace.screens.map(s=>({name:s.name,desktop:current(s).name})),desktops:workspace.desktops.map(d=>d.name)}));
