import subprocess
subprocess.run(['gdbus','call','--session','--dest','org.kde.plasmashell','--object-path','/PlasmaShell','--method','org.kde.PlasmaShell.evaluateScript','desktops()[0].showConfigurationInterface()'],check=True)
