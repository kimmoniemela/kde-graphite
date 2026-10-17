#!/usr/bin/env python3
"""Render illustrative package previews; never capture a user's desktop."""
import os
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QImage, QPainter, QPen

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'theme/org.kde.graphite.desktop/contents/previews'
app = QGuiApplication([])
FAMILY = next((f for f in ['FiraCode Nerd Font Mono', 'Fira Code'] if f in QFontDatabase.families()), 'monospace')
BG, PANEL, TEXT, MUTED, SAGE, SELECT, LINE = '#111416', '#181b1d', '#d7dbd6', '#89918c', '#a6b8a1', '#445145', '#303735'


def rect(painter, x, y, width, height, color):
    painter.fillRect(QRectF(x, y, width, height), QColor(color))


def text(painter, x, y, content, size=14, color=TEXT, bold=False):
    font = QFont(FAMILY, size)
    font.setStyleHint(QFont.TypeWriter)
    font.setBold(bold)
    painter.setFont(font)
    painter.setPen(QColor(color))
    painter.drawText(x, y, content)


def window(p, x, y, width, height, title):
    rect(p, x, y, width, height, PANEL)
    rect(p, x + 1, y + 30, width - 2, height - 31, BG)
    p.setPen(QPen(QColor(LINE), 1))
    p.drawRect(QRectF(x, y, width, height))
    text(p, x + 16, y + 21, title, 11, MUTED)
    text(p, x + width - 25, y + 21, '×', 12, MUTED)


def desktop():
    image = QImage(1600, 900, QImage.Format_RGB32)
    image.fill(QColor(BG))
    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing)
    rect(p, 0, 0, 1600, 32, PANEL)
    rect(p, 8, 3, 28, 26, SELECT)
    for n in range(1, 6):
        text(p, 16 + (n - 1) * 32, 23, str(n), 12, TEXT if n == 1 else MUTED)
    text(p, 188, 23, 'terminal', 11)
    text(p, 316, 23, 'notes', 11, MUTED)
    text(p, 1444, 23, '12:34', 11)
    window(p, 40, 74, 928, 744, 'terminal — graphite')
    window(p, 984, 74, 576, 744, 'notes')
    text(p, 68, 142, 'graphite ~', 15, SAGE, True)
    text(p, 68, 179, '$ cat /etc/os-release', 14)
    text(p, 68, 219, 'NAME="Linux"', 14, MUTED)
    text(p, 68, 250, 'DESKTOP="KDE Plasma"', 14, MUTED)
    text(p, 68, 312, '$ printf "ready\\n"', 14)
    text(p, 68, 351, 'ready', 14, SAGE)
    text(p, 68, 413, '$', 14, SAGE)
    rect(p, 95, 396, 10, 20, SAGE)
    text(p, 1012, 143, '# workspace', 15, SAGE, True)
    lines = ['A place to focus.', '', 'Charcoal surfaces.', 'Muted sage accents.', 'Monospace type.', '', 'Five spaces per display.', 'One quiet top bar.']
    for n, line in enumerate(lines):
        text(p, 1012, 193 + n * 32, line, 13, MUTED if n in [0, 6, 7] else TEXT)
    for n, color in enumerate([BG, PANEL, LINE, SELECT, MUTED, SAGE]):
        rect(p, 1012 + n * 76, 674, 64, 40, color)
    text(p, 1012, 762, 'GRAPHITE', 20, TEXT, True)
    text(p, 42, 864, 'GRAPHITE', 11, SAGE)
    text(p, 188, 864, 'KDE PLASMA', 10, MUTED)
    p.end()
    return image


def lockscreen():
    image = QImage(1600, 900, QImage.Format_RGB32)
    image.fill(QColor(BG))
    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing)
    text(p, 604, 341, '12:34', 76, TEXT)
    text(p, 589, 398, 'Saturday, 17 October', 16, MUTED)
    rect(p, 616, 510, 368, 42, PANEL)
    text(p, 638, 538, 'Password', 13, MUTED)
    text(p, 947, 539, '→', 14, SAGE)
    text(p, 700, 788, 'GRAPHITE', 15, SAGE)
    p.end()
    return image


if __name__ == '__main__':
    DEST.mkdir(parents=True, exist_ok=True)
    image = desktop()
    assert image.save(str(DEST / 'fullscreenpreview.jpg'), 'JPG', 95)
    assert image.scaled(960, 540, Qt.KeepAspectRatio, Qt.SmoothTransformation).save(str(DEST / 'preview.png'))
    assert lockscreen().scaled(960, 540, Qt.KeepAspectRatio, Qt.SmoothTransformation).save(str(DEST / 'lockscreen.png'))
    print(DEST)
