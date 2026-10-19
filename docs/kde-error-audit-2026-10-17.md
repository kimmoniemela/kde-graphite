# KDE error investigation — 17 October 2026

Read-only investigation of this boot's journal, failed user services, installed
session providers, portal configuration and crash stack traces. No desktop,
Hyprland, GNOME, system-service or device-permission settings were changed.
Times below are local EEST. The new KDE login began at **15:31:30**.

## Conclusion

The errors have several distinct causes. There is one confirmed notification
service conflict between desktop components, some earlier custom-script errors,
a KDE clipboard shutdown hang, graphics/dock warnings and unrelated application
or hardware messages. The evidence does not support blaming the whole setup on
KDE being installed alongside Fedora Workstation and Hyprland.

The active session declares `XDG_CURRENT_DESKTOP=KDE` and
`XDG_SESSION_DESKTOP=plasma`. KWin is the running compositor; neither Hyprland nor
GNOME Shell was running when checked. Fedora Workstation's GDM is launching the
Plasma session. The installed KDE portal backend is active. KDE's packaged portal
configuration prefers KDE, uses GTK as a settings fallback, KWallet for secrets
and Plasma for notifications. There was no user portal override in the paths
checked. Multiple backends can be installed; desktop-specific selection is the
intended mechanism. See [portal configuration](https://flatpak.github.io/xdg-desktop-portal/docs/portals.conf.html).

## Findings

| Message / event | Meaning and evidence | Assessment |
| --- | --- | --- |
| `swaync.service` repeatedly fails; `Could not acquire notification name` | Plasma already owns `org.freedesktop.Notifications`. SwayNC tried six times at 15:31:34–36 and hit its restart limit. The unit is disabled, but its installed D-Bus activation file still advertises that same notification name and starts the service. The triggering caller was not identified. | **Confirmed overlap between notification providers.** It is the only failed user unit at inspection. Session-specific activation needs correction; globally removing/masking it could affect another desktop. |
| Duplicate D-Bus names for Notifications | SwayNC and Plasma both provide the standard notification interface. The broker ignores one candidate. | Related to the notification overlap; not evidence of a second compositor. |
| Duplicate `org.freedesktop.FileManager1` | The installed generic service starts Nautilus; Dolphin advertises the same interface from another service file. | Package/provider overlap. It can affect which file manager handles a request, but does not control workspace geometry. |
| Plasma crashes during logout at 15:31:16 | The journal explicitly says its stop operation timed out and systemd sent SIGABRT. The main thread waits inside `WaylandClipboard::~WaylandClipboard()`; the clipboard thread waits on a recursive mutex. | **Clipboard shutdown deadlock pattern.** Consistent with KDE bug 524538. It is a real logout failure, separate from custom scripts. |
| KWin SIGSEGV at 14:37:59 | Stack enters Qt QML's JavaScript garbage collector, `collectFromJSStack`, while evaluating a module/class. | **Real earlier compositor crash.** Script loading/reloading was the suspected trigger during customization; the stack does not conclusively name the initiating script. |
| `QTimer ... deleteLater is not a function` | 132 warnings from the custom workspace bridge, last seen at 15:16:55. KWin's exposed script timer does not offer that method. | Our script error, corrected with reusable timers. No recurrence in the new session at inspection. |
| Read-only `activeScreen`, duplicate launcher property, versioned QML file-name mismatch | Earlier setup/diagnostic attempts used an unsupported property, a faulty obsolete launcher, or failed to load a newly generated component. | Historical custom setup errors. The duplicate launcher is removed and canonical QML entry handling corrected. These messages have not recurred after the fresh login. |
| `No QSGTexture provided`, render-query cleanup warnings and deprecated Overview signal handlers | Qt/KWin scene-graph and built-in Overview messages. There were 114 missing-texture warnings at 15:31:03–10 in the old session, shortly before logout. The same rendering warnings were not observed in the fresh session at inspection. | Native rendering warnings; their exact trigger remains unproven. Possible symptoms include incomplete previews/rendering. The messages alone do not establish a Hyprland conflict. |
| Missing DRM device nodes at login | Four startup warnings. The machine has four EVDI devices from DisplayLink plus the Intel `xe` GPU. The matching counts suggest virtual/dock device enumeration, but do not prove the exact offending nodes. | Graphics/dock investigation if there are visible problems. No compositor failure follows these startup messages in the fresh session. |
| PowerDevil cannot open `/dev/i2c-14` | That bus is the **DisplayLink I2C Adapter** and is root-only. DDC/CI is used to control external-monitor settings such as brightness. | Dock/display-control permissions, not competing desktop environments. Normal desktop rendering does not require granting every I2C bus to the user. |
| Host portal registration errors: app info missing / already associated | Several KDE programs cannot register their application identity with the portal registry. The portal services and KDE backend are nevertheless running. | Portal/app-identification integration warnings. These do not by themselves prove broken file selection or screen sharing; those functions need direct testing if symptoms occur. |
| DrKonqi cannot find metadata / metadata incomplete | On the new login, the crash reporter attempted to process old crashes and could not find complete matching metadata. | Reporting failures about historical crashes, not evidence that those programs crashed again at login. |
| `plasma-apply-lookandfeel` and Spectacle SIGABRT | Logs show `Failed to create wl_display (Operation not permitted)`, failed X display connection and Qt platform initialization aborts. These occurred during earlier setup/testing. | **Restricted display-access failures**, consistent with launching GUI tools from a sandboxed/non-session context. Not evidence that installed Qt platform plugins are missing. |
| `python3.13` SIGTRAP at 15:30:36 | The crash belongs to the **ZapZap Flatpak**, not a Graphite Python helper. Its stack is in bundled QtWebEngine. | Separate application crash. Available symbols do not establish the exact WebEngine failure. |
| Bluetooth timeouts, profile inconsistencies and missing `bluez_output` objects | Connection/profile failures followed by an audio device disappearing. PipeWire, BlueZ and the kernel reported related messages. | Bluetooth/audio stack or device/connection issue; not caused merely by installing multiple desktops. |
| GDM/SELinux status-query denial | The GNOME login worker was denied a systemd graphical-session status query at the greeter/login transition. | Fedora login/security-policy integration. The KDE session still starts; no basis to disable SELinux. |
| `xcb_connect`, `xrdb` empty display, early QPixmap warnings | Startup helpers attempt X-related work before the Wayland/Xwayland application context is ready. | Startup-path warnings. Assess by actual failure; the desktop subsequently starts successfully. |
| QML deprecations, overridden properties, invalid-null connects, missing idle polling | Native Plasma/Qt components report compatibility or defensive-programming warnings. | Generally low priority without a corresponding broken feature. |
| `filepicker.upd` says Version=5 instead of 6 | The file belongs to the installed `kf5-kio-core` package. | Legacy configuration migration/package warning; not a custom theme file. |
| TIFF `ImageLength` missing | KIO's image reader encountered malformed image metadata. | File/thumbnail issue rather than desktop-session integration. |

The clipboard stack matches the scenario described in
[KDE bug 524538](https://bugs.kde.org/show_bug.cgi?id=524538).
The installed KGuiAddons package is 6.31.0; this investigation did not establish
whether a later distribution update fixes it. The local timeout and stack
frames are the primary evidence for the diagnosis.

DDC access is governed by device permissions and normally packaged udev rules;
see [ddcutil's I2C permissions documentation](https://www.ddcutil.com/i2c_permissions/).
The portal warnings also occur in an upstream report on Plasma/Fedora, so they
are not unique evidence of mixing GNOME and Hyprland:
[upstream portal report](https://github.com/flatpak/xdg-desktop-portal/issues/1962).
That report does not establish that this machine has its separate portal-crash bug.

## Current status and priorities

1. Isolate the notification provider by desktop session. Avoid a global SwayNC
   mask or uninstall while other desktops may need it.
2. Track the Plasma clipboard logout hang separately, with the recorded
   `WaylandClipboard` / `ClipboardThread` stack and timeout evidence.
3. Reassess any visible graphics problems in the fresh session. The large
   missing-texture burst belongs to the session that was logged out.
4. Investigate DisplayLink DDC permissions only if external-monitor brightness
   control is needed or broken. Do not grant blanket I2C permissions.
5. Test file picking and screen sharing if portal symptoms occur; do not remove
   functioning portal backends solely because their names include GTK/GNOME.

The fresh session passes the repository's read-only check: the selected scripts,
five desktops, 15 application shortcuts and 20 workspace shortcuts are present.
The earlier custom-script warnings have not recurred since login. This verifies
registrations, not every interactive workspace or script lifecycle path.

The audit covers the retained messages from this boot and the inspected crash
records. It does not prove that rare issues cannot recur, identify every graphics
warning's root cause, or establish a fix version for upstream bugs.
