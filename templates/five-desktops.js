while (workspace.desktops.length < 5) workspace.createDesktop(workspace.desktops.length, String(workspace.desktops.length + 1));
const old = workspace.desktops.slice();
const selected = workspace.screens.map(screen => ({screen:screen, index:old.indexOf(workspace.currentDesktopForScreen(screen))}));
for (const window of workspace.windowList()) {
    if (!window.desktops.length) continue;
    const targets = window.desktops.map(d => old[old.indexOf(d) % 5]);
    window.desktops = targets.filter((d, i) => targets.indexOf(d) === i);
}
for (const item of selected) workspace.setCurrentDesktopForScreen(old[item.index % 5], item.screen);
for (const desktop of old.slice(5).reverse()) workspace.removeDesktop(desktop);
