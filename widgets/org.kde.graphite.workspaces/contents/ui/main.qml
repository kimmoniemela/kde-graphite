// SPDX-License-Identifier: MIT
pragma ComponentBehavior: Bound
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
    TaskManager.ActivityInfo { id: activities }
    TaskManager.TasksModel {
        id: windows
        groupMode: TaskManager.TasksModel.GroupDisabled
        filterByScreen: true
        screenGeometry: Plasmoid.containment.screenGeometry
        filterByVirtualDesktop: false
        filterByCurrentVirtualDesktop: false
        filterByActivity: true
        activity: activities.currentActivity
        onCountChanged: occupancyRefresh.restart()
        onScreenGeometryChanged: occupancyRefresh.restart()
    }
    property var occupiedPages: [false, false, false, false, false]
    readonly property color occupiedColor: Kirigami.Theme.focusColor
    function refreshOccupancy() {
        const occupied = [false, false, false, false, false];
        const ids = desktops.desktopIds;
        for (let row = 0; row < windows.count; row++) {
            const item = windows.index(row, 0);
            if (!windows.data(item, TaskManager.AbstractTasksModel.IsWindow)
                || windows.data(item, TaskManager.AbstractTasksModel.SkipPager)) continue;
            const all = windows.data(item, TaskManager.AbstractTasksModel.IsOnAllVirtualDesktops);
            const assigned = windows.data(item, TaskManager.AbstractTasksModel.VirtualDesktops) || [];
            for (let page = 0; page < Math.min(5, ids.length); page++) {
                if (all || assigned.indexOf(ids[page]) >= 0) occupied[page] = true;
            }
        }
        occupiedPages = occupied;
    }
    Timer { id: occupancyRefresh; interval: 0; onTriggered: root.refreshOccupancy() }
    Connections {
        target: windows
        function onDataChanged() { occupancyRefresh.restart(); }
        function onModelReset() { occupancyRefresh.restart(); }
        function onLayoutChanged() { occupancyRefresh.restart(); }
    }
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
        function onDesktopIdsChanged() { root.refreshPage(); occupancyRefresh.restart(); }
    }
    Component.onCompleted: { refreshPage(); occupancyRefresh.restart(); }
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
                readonly property bool occupied: root.occupiedPages[index]
                width: 28
                height: root.height
                color: selected ? Kirigami.Theme.highlightColor : (mouse.containsMouse ? Qt.rgba(1, 1, 1, 0.06) : "transparent")
                Text {
                    anchors.centerIn: parent
                    text: button.number
                    color: button.selected ? Kirigami.Theme.highlightedTextColor
                           : (button.occupied ? root.occupiedColor : Kirigami.Theme.textColor)
                    opacity: button.selected || button.occupied ? 1 : 0.4
                    font: Kirigami.Theme.defaultFont
                }
                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 3
                    width: 10
                    height: 2
                    radius: 1
                    visible: button.occupied && !button.selected
                    color: root.occupiedColor
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
                                 + (occupied ? ", contains windows" : ", empty")
                Accessible.onPressAction: root.changePage(index)
            }
        }
    }
}
