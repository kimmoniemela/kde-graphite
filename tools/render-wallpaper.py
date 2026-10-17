#!/usr/bin/env python3
"""Build Graphite's original vector contour wallpapers and pre-rendered PNGs."""
import json
import math
import os
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'theme/org.kde.graphite.desktop/contents/wallpapers'
app = QGuiApplication([])
WIDTH, HEIGHT = 3840, 2160


def contours(phase):
    paths = []
    for radius in range(180, 2090, 112):
        points = []
        for step in range(181):
            angle = 2 * math.pi * step / 180
            # A nested, gently distorted ridge; most of it lies beyond the canvas.
            wobble = 1 + .075 * math.sin(3 * angle + phase) + .035 * math.cos(5 * angle - phase)
            x = .99 * WIDTH + radius * wobble * math.cos(angle)
            y = 1.04 * HEIGHT + .78 * radius * wobble * math.sin(angle)
            points.append(f'{x:.2f},{y:.2f}')
        paths.append('<path d="M ' + ' L '.join(points) + ' Z"/>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="3840" height="2160" viewBox="0 0 3840 2160">\n'
            '<rect width="3840" height="2160" fill="#111416"/>\n'
            '<g fill="none" stroke="#344139" stroke-opacity="0.38" stroke-width="1.8" stroke-linejoin="round">\n'
            + '\n'.join(paths) + '\n</g>\n</svg>\n')


for ident, name, phase in [('GraphiteContours', 'Graphite Contours', .2),
                            ('GraphiteContoursAlternate', 'Graphite Contours — Alternate', 1.8)]:
    svg = contours(phase)
    (ROOT / 'assets/wallpapers' / (ident + '.svg')).write_text(svg)
    package = DEST / ident
    (package / 'contents/images').mkdir(parents=True, exist_ok=True)
    (package / 'metadata.json').write_text(json.dumps({'KPlugin': {'Id': ident, 'Name': name,
        'Authors': [{'Name': 'Graphite contributors'}], 'License': 'MIT'}}, indent=2) + '\n')
    image = QImage(WIDTH, HEIGHT, QImage.Format.Format_RGB32)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    QSvgRenderer(svg.encode()).render(painter, QRectF(0, 0, WIDTH, HEIGHT))
    painter.end()
    assert image.save(str(package / 'contents/images/3840x2160.png'))
    preview = image.scaled(960, 540, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    assert preview.save(str(package / 'contents/screenshot.png'))
    print(package)
