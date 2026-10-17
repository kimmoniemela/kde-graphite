import QtQuick;
import org.kde.kwin;

Item {
    id: dbus;
    function getToggleDock() {
        return toggleDock;
    }
    ShortcutHandler {
        id: toggleDock;

        name: "KrohnkitetoggleDock";
        text: "Krohnkite: Toggle Dock";
        sequence: "";
    }

    function getFocusNext() {
        return focusNext;
    }
    ShortcutHandler {
        id: focusNext;

        name: "KrohnkiteFocusNext";
        text: "Krohnkite: Focus Next";
        sequence: "";
    }
    function getFocusPrev() {
        return focusPrev;
    }
    ShortcutHandler {
        id: focusPrev;

        name: "KrohnkiteFocusPrev";
        text: "Krohnkite: Focus Previous";
        sequence: "";
    }

    function getFocusDown() {
        return focusDown;
    }
    ShortcutHandler {
        id: focusDown;

        name: "KrohnkiteFocusDown";
        text: "Krohnkite: Focus Down";
        sequence: "";
    }
    function getFocusUp() {
        return focusUp;
    }
    ShortcutHandler {
        id: focusUp;

        name: "KrohnkiteFocusUp";
        text: "Krohnkite: Focus Up";
        sequence: "";
    }
    function getFocusLeft() {
        return focusLeft;
    }
    ShortcutHandler {
        id: focusLeft;

        name: "KrohnkiteFocusLeft";
        text: "Krohnkite: Focus Left";
        sequence: "";
    }
    function getFocusRight() {
        return focusRight;
    }
    ShortcutHandler {
        id: focusRight;

        name: "KrohnkiteFocusRight";
        text: "Krohnkite: Focus Right";
        sequence: "";
    }
    function getShiftDown() {
        return shiftDown;
    }
    ShortcutHandler {
        id: shiftDown;

        name: "KrohnkiteShiftDown";
        text: "Krohnkite: Move Down/Next";
        sequence: "";
    }
    function getShiftUp() {
        return shiftUp;
    }
    ShortcutHandler {
        id: shiftUp;

        name: "KrohnkiteShiftUp";
        text: "Krohnkite: Move Up/Prev";
        sequence: "";
    }
    function getShiftLeft() {
        return shiftLeft;
    }
    ShortcutHandler {
        id: shiftLeft;

        name: "KrohnkiteShiftLeft";
        text: "Krohnkite: Move Left";
        sequence: "";
    }
    function getShiftRight() {
        return shiftRight;
    }
    ShortcutHandler {
        id: shiftRight;

        name: "KrohnkiteShiftRight";
        text: "Krohnkite: Move Right";
        sequence: "";
    }
    function getGrowHeight() {
        return growHeight;
    }
    ShortcutHandler {
        id: growHeight;

        name: "KrohnkiteGrowHeight";
        text: "Krohnkite: Grow Height";
        sequence: "";
    }
    function getShrinkHeight() {
        return shrinkHeight;
    }
    ShortcutHandler {
        id: shrinkHeight;

        name: "KrohnkiteShrinkHeight";
        text: "Krohnkite: Shrink Height";
        sequence: "";
    }
    function getShrinkWidth() {
        return shrinkWidth;
    }
    ShortcutHandler {
        id: shrinkWidth;

        name: "KrohnkiteShrinkWidth";
        text: "Krohnkite: Shrink Width";
        sequence: "";
    }
    function getGrowWidth() {
        return growWidth;
    }
    ShortcutHandler {
        id: growWidth;

        name: "KrohnkitegrowWidth";
        text: "Krohnkite: Grow Width";
        sequence: "";
    }
    function getIncrease() {
        return increase;
    }
    ShortcutHandler {
        id: increase;

        name: "KrohnkiteIncrease";
        text: "Krohnkite: Increase";
        sequence: "";
    }
    function getDecrease() {
        return decrease;
    }
    ShortcutHandler {
        id: decrease;

        name: "KrohnkiteDecrease";
        text: "Krohnkite: Decrease";
        sequence: "";
    }
    function getToggleFloat() {
        return toggleFloat;
    }
    ShortcutHandler {
        id: toggleFloat;

        name: "KrohnkiteToggleFloat";
        text: "Krohnkite: Toggle Float";
        sequence: "";
    }
    function getFloatAll() {
        return floatAll;
    }
    ShortcutHandler {
        id: floatAll;

        name: "KrohnkiteFloatAll";
        text: "Krohnkite: Toggle Float All";
        sequence: "";
    }
    function getNextLayout() {
        return nextLayout;
    }
    ShortcutHandler {
        id: nextLayout;

        name: "KrohnkiteNextLayout";
        text: "Krohnkite: Next Layout";
        sequence: "";
    }
    function getPreviousLayout() {
        return previousLayout;
    }
    ShortcutHandler {
        id: previousLayout;

        name: "KrohnkitePreviousLayout";
        text: "Krohnkite: Previous Layout";
        sequence: "";
    }
    function getRotate() {
        return rotate;
    }
    ShortcutHandler {
        id: rotate;

        name: "KrohnkiteRotate";
        text: "Krohnkite: Rotate";
        sequence: "";
    }
    function getRotatePart() {
        return rotatePart;
    }
    ShortcutHandler {
        id: rotatePart;

        name: "KrohnkiteRotatePart";
        text: "Krohnkite: Rotate Part";
        sequence: "";
    }
    function getSetMaster() {
        return setMaster;
    }
    ShortcutHandler {
        id: setMaster;

        name: "KrohnkiteSetMaster";
        text: "Krohnkite: Set master";
        sequence: "";
    }
    function getTileLayout() {
        return tileLayout;
    }
    ShortcutHandler {
        id: tileLayout;

        name: "KrohnkiteTileLayout";
        text: "Krohnkite: Tile Layout";
        sequence: "";
    }
    function getMonocleLayout() {
        return monocleLayout;
    }
    ShortcutHandler {
        id: monocleLayout;

        name: "KrohnkiteMonocleLayout";
        text: "Krohnkite: Monocle Layout";
        sequence: "";
    }
    function getThreeColumnLayout() {
        return treeColumnLayout;
    }
    ShortcutHandler {
        id: treeColumnLayout;

        name: "KrohnkiteTreeColumnLayout";
        text: "Krohnkite: Three Column Layout";
        sequence: "";
    }
    function getSpreadLayout() {
        return spreadLayout;
    }
    ShortcutHandler {
        id: spreadLayout;

        name: "KrohnkiteSpreadLayout";
        text: "Krohnkite: Spread Layout";
        sequence: "";
    }
    function getStairLayout() {
        return stairLayout;
    }
    ShortcutHandler {
        id: stairLayout;

        name: "KrohnkiteStairLayout";
        text: "Krohnkite: Stair Layout";
        sequence: "";
    }
    function getFloatingLayout() {
        return floatingLayout;
    }
    ShortcutHandler {
        id: floatingLayout;

        name: "KrohnkiteFloatingLayout";
        text: "Krohnkite: Floating Layout";
        sequence: "";
    }
    function getQuarterLayout() {
        return quarterLayout;
    }
    ShortcutHandler {
        id: quarterLayout;

        name: "KrohnkiteQuarterLayout";
        text: "Krohnkite: Quarter Layout";
        sequence: "";
    }
    function getStackedLayout() {
        return stackedLayout;
    }
    ShortcutHandler {
        id: stackedLayout;

        name: "KrohnkiteStackedLayout";
        text: "Krohnkite: Stacked Layout";
        sequence: "";
    }
    function getBTreeLayout() {
        return bTreeLayout;
    }
    ShortcutHandler {
        id: bTreeLayout;

        name: "KrohnkiteBTreeLayout";
        text: "Krohnkite: BTree Layout";
        sequence: "";
    }
    function getSpiralLayout() {
        return spiralLayout;
    }
    ShortcutHandler {
        id: spiralLayout;

        name: "KrohnkiteSpiralLayout";
        text: "Krohnkite: Spiral Layout";
        sequence: "";
    }
    function getColumnsLayout() {
        return columnsLayout;
    }
    ShortcutHandler {
        id: columnsLayout;

        name: "KrohnkiteColumnsLayout";
        text: "Krohnkite: Columns Layout";
        sequence: "";
    }
}
