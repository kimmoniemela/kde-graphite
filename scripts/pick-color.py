import re, subprocess
r=subprocess.run(['gdbus','call','--session','--dest','org.kde.KWin','--object-path','/ColorPicker','--method','org.kde.kwin.ColorPicker.pick'],text=True,capture_output=True)
if r.returncode==0:
    m=re.search(r'uint32 (\d+)',r.stdout)
    if m: subprocess.run(['wl-copy',f'#{int(m.group(1)) & 0xffffff:06x}'],check=True)
