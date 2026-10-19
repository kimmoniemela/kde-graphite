// Static wallpaper only; no panel, shortcut or window-management changes.
var graphiteWallpaperImages = @@WALLPAPER_IMAGES@@;
for (var desktop of desktops()) {
    if (desktop.screen < 0) continue;
    if (desktop.wallpaperPlugin !== 'org.kde.image') desktop.wallpaperPlugin = 'org.kde.image';
    desktop.currentConfigGroup = ['Wallpaper', 'org.kde.image', 'General'];
    var image = graphiteWallpaperImages[desktop.screen % graphiteWallpaperImages.length];
    if (desktop.readConfig('Image', '') !== image) desktop.writeConfig('Image', image);
    if (Number(desktop.readConfig('FillMode', 2)) !== 2) desktop.writeConfig('FillMode', 2);
}
