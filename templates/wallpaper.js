// Static wallpaper only; no panel, shortcut or window-management changes.
var graphiteWallpaperImages = @@WALLPAPER_IMAGES@@;
for (var desktop of desktops()) {
    if (desktop.screen < 0) continue;
    desktop.wallpaperPlugin = 'org.kde.image';
    desktop.currentConfigGroup = ['Wallpaper', 'org.kde.image', 'General'];
    desktop.writeConfig('Image', graphiteWallpaperImages[desktop.screen % graphiteWallpaperImages.length]);
    desktop.writeConfig('FillMode', 2);
}
