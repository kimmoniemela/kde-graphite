// SPDX-License-Identifier: MIT
import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PlasmaComponents
import org.kde.plasma.plasma5support as Plasma5Support
import org.kde.kirigami as Kirigami

PlasmoidItem {
    id: root
    property bool tiling: false
    property bool available: false
    property bool busy: false
    property bool pending: false
    property string error: "Checking tiling status"
    property int serial: 0
    preferredRepresentation: fullRepresentation
    Layout.minimumWidth: metrics.width + 20
    Layout.maximumWidth: Layout.minimumWidth
    Layout.fillHeight: true
    Plasmoid.status: PlasmaCore.Types.ActiveStatus
    toolTipMainText: "Automatic tiling"
    toolTipSubText: error || (available ? (tiling ? "Click to disable tiling on all monitors" : "Click to enable tiling on all monitors") : "Kröhnkite is not installed")

    TextMetrics { id: metrics; font: Kirigami.Theme.defaultFont; text: "TILE OFF" }

    function request(action) {
        if (pending) return;
        pending = true;
        busy = action !== "status";
        const path = decodeURIComponent(Qt.resolvedUrl("../code/tiling-control.py").toString().replace(/^file:\/\//, ""));
        const quoted = "'" + path.replace(/'/g, "'\\''") + "'";
        runner.connectSource("python3 " + quoted + " " + action + " " + Date.now() + "-" + (++serial));
    }

    Plasma5Support.DataSource {
        id: runner
        engine: "executable"
        connectedSources: []
        onNewData: function(sourceName, data) {
            disconnectSource(sourceName);
            try {
                const state = JSON.parse(data.stdout);
                root.tiling = state.enabled === true;
                root.available = state.available;
                root.error = state.error;
            } catch (e) {
                root.available = false;
                root.error = "Cannot read tiling status: " + (data.stderr || e);
            }
            root.busy = false;
            root.pending = false;
        }
    }
    Timer {
        interval: 2000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: root.request("status")
    }
    fullRepresentation: PlasmaComponents.ToolButton {
        id: button
        enabled: root.available && !root.pending
        text: root.busy ? "TILE …" : (root.error ? "TILE ?" : (root.tiling ? "TILE ON" : "TILE OFF"))
        Accessible.name: "Automatic tiling " + (root.tiling ? "on" : "off")
        onClicked: root.request("toggle")
        contentItem: Text {
            id: label
            text: button.text
            font: Kirigami.Theme.defaultFont
            color: root.tiling && !root.error ? Kirigami.Theme.highlightColor : Kirigami.Theme.textColor
            opacity: root.tiling ? 1 : 0.65
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }
}
