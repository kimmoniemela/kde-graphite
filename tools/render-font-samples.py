#!/usr/bin/env python3
"""Render regular monospace choices with native Qt widgets and Graphite colors."""
import argparse
import configparser
import os
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_FONT_DPI', '96')

from PySide6.QtGui import QColor, QFont, QFontDatabase, QFontInfo, QImage, QPainter, QPalette
from PySide6.QtWidgets import (QApplication, QCheckBox, QHBoxLayout, QLineEdit,
                              QListWidget, QMainWindow, QPushButton, QSplitter, QStyleFactory,
                              QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

ROOT = Path(__file__).resolve().parents[1]
FAMILIES = ('Noto Sans Mono', 'Hack', 'DejaVu Sans Mono')


def palette():
    colors = configparser.ConfigParser()
    colors.read(ROOT / 'assets/color-schemes/TerminalGraphite.colors')
    result = QPalette()
    roles = {
        'Window': ('Window', 'BackgroundNormal'),
        'WindowText': ('Window', 'ForegroundNormal'),
        'Base': ('View', 'BackgroundNormal'),
        'AlternateBase': ('View', 'BackgroundAlternate'),
        'Text': ('View', 'ForegroundNormal'),
        'Button': ('Button', 'BackgroundNormal'),
        'ButtonText': ('Button', 'ForegroundNormal'),
        'Highlight': ('Selection', 'BackgroundNormal'),
        'HighlightedText': ('Selection', 'ForegroundNormal'),
        'ToolTipBase': ('Tooltip', 'BackgroundNormal'),
        'ToolTipText': ('Tooltip', 'ForegroundNormal'),
        'Link': ('View', 'ForegroundLink'),
        'PlaceholderText': ('View', 'ForegroundInactive'),
    }
    for role, (group, key) in roles.items():
        color = QColor(*map(int, colors['Colors:' + group][key].split(',')))
        result.setColor(getattr(QPalette.ColorRole, role), color)
    return result


def sample_window(font):
    window = QMainWindow()
    window.setFont(font)
    for name in ('File', 'Edit', 'View', 'Go', 'Help'):
        window.menuBar().addMenu(name)
    toolbar = window.addToolBar('Navigation')
    toolbar.setMovable(False)
    for label in ('← Back', '↑ Up', 'Home'):
        toolbar.addAction(label)
    address = QLineEdit('/home/kimmo/Projects')
    toolbar.addWidget(address)

    body = QWidget()
    layout = QVBoxLayout(body)
    splitter = QSplitter()
    places = QListWidget()
    places.addItems(('Home', 'Desktop', 'Documents', 'Downloads', 'Projects', 'Pictures'))
    places.setCurrentRow(4)
    splitter.addWidget(places)
    files = QTreeWidget()
    files.setHeaderLabels(('Name', 'Modified', 'Size'))
    for values in (('kde-graphite', 'Today', 'Folder'), ('notes.md', 'Yesterday', '2.4 KiB'),
                   ('wallpaper.png', '12 Nov', '1.2 MiB'), ('Ääkköset.txt', '11 Nov', '640 B')):
        files.addTopLevelItem(QTreeWidgetItem(values))
    files.setCurrentItem(files.topLevelItem(0))
    files.setRootIsDecorated(False)
    files.setColumnWidth(0, 180)
    files.setColumnWidth(1, 112)
    splitter.addWidget(files)
    splitter.setSizes((125, 460))
    layout.addWidget(splitter)
    search = QLineEdit()
    search.setPlaceholderText('Search files and folders…')
    layout.addWidget(search)
    actions = QHBoxLayout()
    actions.addWidget(QCheckBox('Show hidden files'))
    actions.addStretch()
    actions.addWidget(QPushButton('New folder'))
    layout.addLayout(actions)
    window.setCentralWidget(body)
    window.statusBar().showMessage('4 items · 1 selected')
    window.resize(608, 360)
    return window


def draw_text(painter, x, y, text, family, size, color='#d7dbd6'):
    font = QFont(family, size)
    font.setWeight(QFont.Normal)
    painter.setFont(font)
    painter.setPen(QColor(color))
    painter.drawText(x, y, text)


def render_sample(app, family, index):
    font = QFont(family, 10)
    font.setWeight(QFont.Normal)
    app.setFont(font)
    window = sample_window(font)
    window.show()
    app.processEvents()
    image = QImage(640, 570, QImage.Format_RGB32)
    image.fill(QColor('#111416'))
    painter = QPainter(image)
    draw_text(painter, 16, 35, f'{index}. {family}', family, 17, '#a6b8a1')
    draw_text(painter, 16, 62, 'Regular / 400 · 10 pt', family, 10, '#89918c')
    painter.fillRect(16, 82, 608, 30, QColor('#181b1d'))
    draw_text(painter, 28, 102, 'Projects — Graphite', family, 9)
    draw_text(painter, 544, 102, '−  □  ×', family, 9, '#89918c')
    painter.drawPixmap(16, 112, window.grab())
    draw_text(painter, 20, 510, '$ git status --short', family, 11, '#a6b8a1')
    draw_text(painter, 20, 540, 'Il1 O0  0123456789  {}[]  äöå', family, 11)
    painter.end()
    window.close()
    print(f'{family}: resolved to {QFontInfo(font).family()}, weight {QFontInfo(font).weight()}')
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'build/font-samples')
    args = parser.parse_args()
    app = QApplication([])
    if 'Breeze' not in QStyleFactory.keys():
        parser.error('The Breeze Qt widget style must be installed for these previews')
    app.setStyle('Breeze')
    app.setPalette(palette())
    missing = set(FAMILIES) - set(QFontDatabase.families())
    if missing:
        parser.error('Install these fonts before rendering: ' + ', '.join(sorted(missing)))
    args.output.mkdir(parents=True, exist_ok=True)
    sheet = QImage(1952, 658, QImage.Format_RGB32)
    sheet.fill(QColor('#111416'))
    painter = QPainter(sheet)
    draw_text(painter, 24, 34, 'GRAPHITE · Regular monospace choices', 'sans-serif', 17)
    draw_text(painter, 24, 62, 'Native Qt/Breeze widget renders · illustrative windows · all samples use 10 pt / weight 400',
              'sans-serif', 11, '#89918c')
    for index, family in enumerate(FAMILIES, 1):
        sample = render_sample(app, family, index)
        destination = args.output / (family.lower().replace(' ', '-') + '.png')
        if not sample.save(str(destination)):
            raise RuntimeError(f'Could not write {destination}')
        painter.drawImage(8 + (index - 1) * 648, 80, sample)
    painter.end()
    destination = args.output / 'comparison.png'
    if not sheet.save(str(destination)):
        raise RuntimeError(f'Could not write {destination}')
    print(destination)


if __name__ == '__main__':
    main()
