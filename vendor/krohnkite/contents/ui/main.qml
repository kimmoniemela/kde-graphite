// Copyright (c) 2018 Eon S. Jeon <esjeon@hyunmu.am>
//
// Permission is hereby granted, free of charge, to any person obtaining a
// copy of this software and associated documentation files (the "Software"),
// to deal in the Software without restriction, including without limitation
// the rights to use, copy, modify, merge, publish, distribute, sublicense,
// and/or sell copies of the Software, and to permit persons to whom the
// Software is furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
// THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
// FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
// DEALINGS IN THE SOFTWARE.

import QtQuick 2.15
import org.kde.plasma.core as PlasmaCore;
import org.kde.plasma.components as Plasma;
import org.kde.plasma.plasma5support as Plasma5Support
import org.kde.kwin 3.0;
import org.kde.taskmanager as TaskManager
import "../code/script.js" as K

Item {
    id: scriptRoot
    property var driver: null
    property bool runtimeEnabled: KWin.readConfig("runtimeEnabled", true)
    property bool runtimeRequested: KWin.readConfig("runtimeEnabled", true)
    property bool enabledInSettings: true
    property int pollSerial: 0
    function updateMode(value) {
        if (value === runtimeEnabled) return;
        runtimeEnabled = value;
        if (driver) driver.setRuntimeEnabled(value);
        else K.setGraphiteTilingEnabled(value);
        if (!value) {
            for (const w of Workspace.stackingOrder) {
                if (w && !w.deleted && w.normalWindow && !w.fullScreen) w.noBorder = false;
            }
        }
    }
    Plasma5Support.DataSource {
        id: modeReader
        engine: "executable"
        connectedSources: []
        onNewData: function(source, data) {
            disconnectSource(source);
            if (data["exit code"] !== 0) return;
            if (source.includes("--group Plugins"))
                scriptRoot.enabledInSettings = data.stdout.trim() !== "false";
            else
                scriptRoot.runtimeRequested = data.stdout.trim() !== "false";
            scriptRoot.updateMode(scriptRoot.runtimeRequested && scriptRoot.enabledInSettings);
        }
    }
    Timer {
        interval: 500; running: true; repeat: true; triggeredOnStart: true
        onTriggered: {
            // A unique source prevents the executable engine from returning cached output.
            const prefix = "env GRAPHITE_READ_ID=" + Date.now() + "-" + (++scriptRoot.pollSerial) + " ";
            modeReader.connectSource(prefix + "kreadconfig6 --file kwinrc --group Script-krohnkite --key runtimeEnabled --default true");
            modeReader.connectSource(prefix + "kreadconfig6 --file kwinrc --group Plugins --key krohnkiteEnabled --default false");
        }
    }

    TaskManager.ActivityInfo {
        id: activityInfo
    }

    Loader {
        id: popupDialog
        source: "popup.qml"

        function show(text, duration) {
            var area = Workspace.clientArea(KWin.FullScreenArea, Workspace.activeScreen, Workspace.currentDesktop);
            this.item.show(text, area, duration);
        }
    }

    Component.onCompleted: {
        console.log("KROHNKITE: starting the script");
        const api = {
            "workspace": Workspace,
            // "options": Options,
            "kwin": KWin,
            "shortcuts": shortcutsLoader.item
        };

        K.setGraphiteTilingEnabled(runtimeEnabled);
        driver = new K.KWinDriver(api);
        driver.main();
    }
    Component.onDestruction: {
        // Workspace/window signals outlive this QML root unless explicitly disconnected.
        if (driver) driver.shutdown();
        else K.setGraphiteTilingEnabled(false);
        // Also restore controls when tiling is disabled from System Settings.
        for (const window of Workspace.stackingOrder) {
            if (window && !window.deleted && window.normalWindow && !window.fullScreen)
                window.noBorder = false;
        }
    }
    Loader {
        id: shortcutsLoader;

        source: "shortcuts.qml";
    }
}
