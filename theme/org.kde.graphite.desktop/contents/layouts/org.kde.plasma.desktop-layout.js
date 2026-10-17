// Generated from templates/panel.js. No monitor names or widget IDs are stored.
var plugins = new ConfigFile('kwinrc', 'Plugins');
var bridge = new ConfigFile('kwinrc', 'Script-kde-hypr-bridge');
var graphiteBridge = String(plugins.readEntry('kde-hypr-bridgeEnabled')) === 'true';
var graphitePagerType = graphiteBridge && knownWidgetTypes.includes('org.kde.graphite.workspaces')
    ? 'org.kde.graphite.workspaces' : 'org.kde.plasma.pager';
var graphiteAssignShortcuts = graphiteBridge;
var graphitePrimaryOutput = String(bridge.readEntry('PrimaryOutput') || '');
// One bar per connected screen. Set graphiteOnlyMissing for a live addition.
var ps = panels();
var screens = desktops().map(d => d.screen).filter((s, i, all) => s >= 0 && all.indexOf(s) === i);
function configurePanel(p, primary) {
    p.location = 'top';
    p.height = 28;
    p.hiding = 'none';
    p.floating = false;
    p.opacity = 'opaque';
    for (var w of p.widgets()) w.remove();
    var pagerType = typeof graphitePagerType === 'undefined' ? 'org.kde.graphite.workspaces' : graphitePagerType;
    var pager = p.addWidget(pagerType);
    pager.currentConfigGroup = ['General'];
    if (pagerType === 'org.kde.graphite.workspaces') pager.writeConfig('primaryOutput', graphitePrimaryOutput);
    else {
        pager.writeConfig('displayedText', 1);
        pager.writeConfig('showOnlyCurrentScreen', true);
        pager.writeConfig('showWindowIcons', false);
    }
    var tasks = p.addWidget('org.kde.plasma.taskmanager');
    tasks.currentConfigGroup = ['General'];
    tasks.writeConfig('launchers', []);
    tasks.writeConfig('showOnlyCurrentDesktop', true);
    tasks.writeConfig('showOnlyCurrentScreen', true);
    tasks.writeConfig('taskMaxWidth', 0);
    tasks.writeConfig('maxTextLines', 1);
    tasks.writeConfig('groupingStrategy', 1);
    tasks.writeConfig('onlyGroupWhenFull', false);
    tasks.writeConfig('groupedTaskVisualization', 3);
    tasks.writeConfig('indicateAudioStreams', false);
    tasks.writeConfig('tooltipControls', false);
    p.addWidget('org.kde.plasma.panelspacer');
    var tray = p.addWidget('org.kde.plasma.systemtray');
    tray.currentConfigGroup = ['General'];
    tray.writeConfig('shownItems', ['org.kde.plasma.networkmanagement', 'org.kde.plasma.volume', 'org.kde.plasma.battery']);
    tray.writeConfig('hiddenItems', ['org.kde.kdeconnect', 'org.kde.plasma.vault', 'org.kde.plasma.clipboard', 'org.kde.plasma.devicenotifier', 'org.kde.plasma.manage-inputmethod', 'org.kde.plasma.mediacontroller', 'org.kde.plasma.brightness', 'org.kde.plasma.keyboardlayout', 'org.kde.plasma.keyboardindicator', 'org.kde.plasma.printmanager', 'org.kde.kscreen', 'org.kde.plasma.weather', 'org.kde.plasma.bluetooth'].concat([]));
    tray.writeConfig('showAllItems', false);
    tray.writeConfig('iconSpacing', 1);
    tray.globalShortcut = primary && (typeof graphiteAssignShortcuts === 'undefined' || graphiteAssignShortcuts) ? 'Meta+X' : '';
    var clock = p.addWidget('org.kde.plasma.digitalclock');
    clock.currentConfigGroup = ['Appearance'];
    clock.writeConfig('showDate', false);
    clock.writeConfig('showSeconds', 0);
    clock.writeConfig('use24hFormat', 2);
}
for (var screen of screens) {
    var existing = ps.find(p => p.screen === screen && p.location === 'top');
    if (existing && typeof graphiteOnlyMissing !== 'undefined' && graphiteOnlyMissing) continue;
    var p = existing || new Panel;
    p.screen = screen;
    configurePanel(p, screen === screens[0]);
}
for (var d of desktops()) {
    if (typeof graphiteOnlyMissing !== 'undefined' && graphiteOnlyMissing) continue;
    d.currentConfigGroup = ['General'];
    d.writeConfig('showToolbox', false);
}
print('Graphite panels applied');
// Static wallpaper only; no panel, shortcut or window-management changes.
var graphiteWallpaperImages = ["file://" + userDataPath("data", "plasma/look-and-feel/org.kde.graphite.desktop/contents/wallpapers/GraphiteContours/contents/images/3840x2160.png").split("/").map(encodeURIComponent).join("/"), "file://" + userDataPath("data", "plasma/look-and-feel/org.kde.graphite.desktop/contents/wallpapers/GraphiteContoursAlternate/contents/images/3840x2160.png").split("/").map(encodeURIComponent).join("/")];
for (var desktop of desktops()) {
    if (desktop.screen < 0) continue;
    desktop.wallpaperPlugin = 'org.kde.image';
    desktop.currentConfigGroup = ['Wallpaper', 'org.kde.image', 'General'];
    desktop.writeConfig('Image', graphiteWallpaperImages[desktop.screen % graphiteWallpaperImages.length]);
    desktop.writeConfig('FillMode', 2);
}
