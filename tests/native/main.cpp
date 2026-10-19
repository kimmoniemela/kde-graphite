#include <QGuiApplication>
#include <QTimer>
#include <kglobalacceld.h>
int main(int argc, char **argv) {
    QGuiApplication app(argc, argv);
    app.setQuitOnLastWindowClosed(false);
    app.setQuitLockEnabled(false);
    KGlobalAccelD shortcuts;
    if (!shortcuts.init()) return 1;
    QTimer::singleShot(30000, &app, &QGuiApplication::quit);
    return app.exec();
}
