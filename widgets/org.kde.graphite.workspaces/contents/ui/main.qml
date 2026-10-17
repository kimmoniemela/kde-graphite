// SPDX-License-Identifier: MIT
import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.kirigami as Kirigami
import plasma.applet.org.kde.plasma.pager

PlasmoidItem {
    id: root
    readonly property string primaryOutput: Plasmoid.configuration.primaryOutput
    readonly property int offset: root.Screen.name === primaryOutput || Qt.application.screens.length === 1 ? 0 : 5
    preferredRepresentation: fullRepresentation
    Layout.minimumWidth: 144
    Layout.maximumWidth: 144
    Layout.fillHeight: true
    Plasmoid.status: PlasmaCore.Types.ActiveStatus

    PagerModel {
        id: pager
        enabled: true
        showDesktop: false
        showOnlyCurrentScreen: true
        screenName: root.Screen.name
        screenGeometry: Plasmoid.containment.screenGeometry
        pagerType: PagerModel.VirtualDesktops
    }

    fullRepresentation: Row {
        spacing: 1
        Repeater {
            model: 5
            Rectangle {
                id: button
                required property int index
                readonly property int number: root.offset + index + 1
                readonly property bool selected: pager.currentPage === index
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
                    onClicked: pager.changePage(button.index)
                    onWheel: event => {
                        const direction = event.angleDelta.y > 0 ? -1 : 1;
                        pager.changePage(Math.max(0, Math.min(4, pager.currentPage + direction)));
                        event.accepted = true;
                    }
                }
                Accessible.role: Accessible.Button
                Accessible.name: "Workspace " + number + " on " + root.Screen.name
                Accessible.onPressAction: pager.changePage(index)
            }
        }
    }
}
