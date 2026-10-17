// SPDX-License-Identifier: MIT
import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.kirigami as Kirigami
import org.kde.taskmanager as TaskManager
import org.kde.plasma.plasma5support as Plasma5Support

PlasmoidItem {
    id: root
    readonly property string primaryOutput: Plasmoid.configuration.primaryOutput
    readonly property int offset: root.Screen.name === primaryOutput || Qt.application.screens.length === 1 ? 0 : 5
    preferredRepresentation: fullRepresentation
    Layout.minimumWidth: 144
    Layout.maximumWidth: 144
    Layout.fillHeight: true
    Plasmoid.status: PlasmaCore.Types.ActiveStatus

    TaskManager.VirtualDesktopInfo { id: desktops }
    property int currentPage: 0
    function refreshPage() {
        currentPage = desktops.desktopIds.indexOf(desktops.currentDesktopByScreenName(root.Screen.name));
    }
    function changePage(index) {
        if (index < 0 || index >= 5) return;
        const number = root.offset + index + 1;
        commands.connectSource("gdbus call --session --dest org.kde.kglobalaccel --object-path /component/kwin --method org.kde.kglobalaccel.Component.invokeShortcut KdeHyprDesktop" + number);
    }
    Connections {
        target: desktops
        function onCurrentDesktopForScreenChanged(screenName) { root.refreshPage(); }
        function onDesktopIdsChanged() { root.refreshPage(); }
    }
    Component.onCompleted: refreshPage()
    Plasma5Support.DataSource {
        id: commands
        engine: "executable"
        connectedSources: []
        onNewData: function(source, data) { disconnectSource(source); }
    }

    fullRepresentation: Row {
        spacing: 1
        Repeater {
            model: 5
            Rectangle {
                id: button
                required property int index
                readonly property int number: root.offset + index + 1
                readonly property bool selected: root.currentPage === index
                width: 28
                height: root.height
                color: selected ? Kirigami.Theme.highlightColor : (mouse.containsMouse ? Qt.rgba(1, 1, 1, 0.06) : "transparent")
                Text {
                    anchors.centerIn: parent
                    text: button.number
                    color: button.selected ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor
                    font: Kirigami.Theme.defaultFont
                }
                MouseArea {
                    id: mouse
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: root.changePage(button.index)
                    onWheel: event => {
                        const direction = event.angleDelta.y > 0 ? -1 : 1;
                        root.changePage(Math.max(0, Math.min(4, root.currentPage + direction)));
                        event.accepted = true;
                    }
                }
                Accessible.role: Accessible.Button
                Accessible.name: "Workspace " + number + " on " + root.Screen.name
                Accessible.onPressAction: root.changePage(index)
            }
        }
    }
}
