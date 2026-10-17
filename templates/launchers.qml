import QtQuick
import org.kde.kwin
import org.kde.plasma.plasma5support as Plasma5Support
Item {
    Component.onCompleted: runner.connectSource(runner.workspaceKeysCommand)
    Plasma5Support.DataSource {
        id: runner
        engine: "executable"
        connectedSources: []
        property int serial: 0
        property string commandPrefix: @@COMMAND_PREFIX@@
        property string workspaceKeysCommand: @@WORKSPACE_KEYS_COMMAND@@
        onNewData: function(sourceName, data) {
            if (sourceName === workspaceKeysCommand && data["exit code"] === undefined) return;
            disconnectSource(sourceName);
        }
        function exec(name) {
            connectSource(commandPrefix + " " + name + " " + Date.now() + "-" + (++serial));
        }
    }
@@SHORTCUT_HANDLERS@@
}
