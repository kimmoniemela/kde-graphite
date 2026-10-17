import QtQuick
import org.kde.kwin
import org.kde.plasma.plasma5support as Plasma5Support
Item {
    Plasma5Support.DataSource {
        id: runner
        engine: "executable"
        connectedSources: []
        property int serial: 0
        property string commandPrefix: @@COMMAND_PREFIX@@
        onNewData: function(sourceName, data) { disconnectSource(sourceName); }
        function exec(name) {
            connectSource(commandPrefix + " " + name + " " + Date.now() + "-" + (++serial));
        }
    }
@@SHORTCUT_HANDLERS@@
}
