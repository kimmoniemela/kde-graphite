// SPDX-License-Identifier: GPL-2.0-or-later
// Based on R0h1tAnand/kwin-meta-scroll-switcher.
#include "workspace-scroll.h"
#include <effect/effecthandler.h>
#include <QAction>
#include <QDBusConnection>
#include <QDBusMessage>
#include <QDBusPendingCall>
namespace KWin {
MetaScrollDesktopEffect::MetaScrollDesktopEffect() {
    const auto bind = [this](Qt::KeyboardModifiers modifiers, PointerAxisDirection direction, const QString &shortcut) {
        auto action = new QAction(this);
        connect(action, &QAction::triggered, this, [shortcut] {
            auto message = QDBusMessage::createMethodCall(QStringLiteral("org.kde.kglobalaccel"), QStringLiteral("/component/kwin"), QStringLiteral("org.kde.kglobalaccel.Component"), QStringLiteral("invokeShortcut"));
            message.setArguments({shortcut});
            QDBusConnection::sessionBus().asyncCall(message);
        });
        effects->registerAxisShortcut(modifiers, direction, action);
    };
    bind(Qt::MetaModifier, PointerAxisUp, QStringLiteral("KdeHyprWorkspaceNext"));
    bind(Qt::MetaModifier, PointerAxisDown, QStringLiteral("KdeHyprWorkspacePrev"));
}
bool MetaScrollDesktopEffect::supported() { return true; }

}
