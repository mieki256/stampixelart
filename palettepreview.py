#!python
# -*- mode: python; Encoding: utf-8; coding: utf-8 -*-
# Last updated: <2016/11/29 04:12:16 +0900>
# pylint: disable=C0103,W0401,W0602,W0603,W0613,W0614,E1101
u"""パレットプレビュー関係のクラス群."""

import os
import re
from PySide.QtCore import *     # NOQA
from PySide.QtGui import *      # NOQA

PALETTES_DIR = "./palettes"
DEF_PALETTE_NAME = "nes"


class PalettePreview(QGraphicsView):

    u"""パレットプレビュー用QGraphicsView."""

    valueGetted = Signal(QColor)

    def __init__(self, *argv, **keywords):
        """init."""
        super(PalettePreview, self).__init__(*argv, **keywords)
        self.rgb_data = []
        self.w = 256
        self.h = 64
        self.columns = 16
        self.rows = 8
        self.cw = self.w / self.columns
        self.ch = self.h / self.rows
        self.select_color = QColor(Qt.black)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFixedSize(self.w, self.h)
        self.setBackgroundBrush(QBrush(self.get_bg_chip_image()))

        self.setScene(QGraphicsScene(self))
        pm = QPixmap(self.w, self.h)
        pm.fill(Qt.black)
        self.pal_canvas_item = QGraphicsPixmapItem(pm)
        self.scene().addItem(self.pal_canvas_item)
        self.pal_canvas_item.setOffset(0, 0)

    def make_palette_preview(self, columns, rgb_data):
        u"""パレットプレビュー画像を生成."""
        self.rgb_data = rgb_data
        self.columns = columns
        n = len(rgb_data)
        self.rows = n / columns
        if n % columns != 0 or n < columns:
            self.rows += 1
        self.cw = self.w / self.columns
        self.ch = self.h / self.rows

        # QPixmapに描画
        pm = QPixmap(self.w, self. h)
        pm.fill(QColor(0, 0, 0, 0))
        x, y = 0, 0
        for d in self.rgb_data:
            r, g, b, _ = d
            self.draw_one_palette(pm, x, y, self.cw, self.ch, (r, g, b))
            x += self.cw
            if x >= self.w or x + self.cw > self.w:
                x = 0
                y += self.ch

        self.pal_canvas_item.setPixmap(pm)
        self.scene().setSceneRect(QRectF(0, 0, self.w, self.h))

    def draw_one_palette(self, pm, x, y, w, h, rgb):
        u"""色を一つだけ描画."""
        r, g, b = rgb
        brush = QPixmap(w, h)
        brush.fill(QColor(r, g, b, 255))
        qp = QPainter()
        qp.begin(pm)
        qp.drawPixmap(x, y, brush)
        qp.end()
        del qp
        del brush

    def get_bg_chip_image(self):
        u"""背景塗りつぶし用のパターンを作成して返す."""
        c0, c1 = 128, 80
        im = QImage(16, 16, QImage.Format_ARGB32)
        qp = QPainter()
        qp.begin(im)
        qp.fillRect(0, 0, 16, 16, QColor(c0, c0, c0, 255))
        qp.fillRect(0, 0, 8, 8, QColor(c1, c1, c1, 255))
        qp.fillRect(8, 8, 8, 8, QColor(c1, c1, c1, 255))
        qp.end()
        del qp
        return im

    def mousePressEvent(self, event):
        u"""マウスボタンが押された時の処理."""
        if event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            x = int(scene_pos.x())
            y = int(scene_pos.y())
            if x < 0 or x >= self.w or y < 0 or y >= self.h:
                return
            idx = (y / self.ch) * self.columns + (x / self.cw)
            if idx < len(self.rgb_data):
                r, g, b, _ = self.rgb_data[idx]
                self.select_color.setRgb(r, g, b, 255)
                self.valueGetted.emit(self.select_color)

    @Slot(QColor)
    def changedValue(self, value):
        """get color."""
        pass


class PaletteSelect(QWidget):

    u"""パレット選択ウィジェット."""

    valueGetted = Signal(QColor)

    def __init__(self, *argv, **keywords):
        """init."""
        super(PaletteSelect, self).__init__(*argv, **keywords)
        self.gpl_data = self.get_gpl_data()

        self.gview = PalettePreview(self)

        idx = 0
        self.combo = QComboBox(self)
        lst = sorted(self.gpl_data.keys())
        for (i, key) in enumerate(lst):
            self.combo.addItem(key)
            if key == DEF_PALETTE_NAME:
                idx = i

        vl = QVBoxLayout()
        vl.setSpacing(2)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.addWidget(self.combo)
        vl.addWidget(self.gview)
        self.setLayout(vl)

        self.combo.activated[str].connect(self.change_combo)
        self.gview.valueGetted[QColor].connect(self.clicked_palette_view)

        self.combo.setCurrentIndex(idx)
        self.update_preview(DEF_PALETTE_NAME)

    def change_combo(self, str):
        u"""comboboxが変更された時に呼ばれる処理."""
        self.update_preview(str)

    def clicked_palette_view(self, col):
        u"""パレットプレビューがクリックされた時に呼ばれる処理."""
        self.valueGetted.emit(col)

    def update_preview(self, pal_name):
        u"""パレットプレビューを更新."""
        _, columns, rgb_data = self.gpl_data[pal_name]
        self.gview.make_palette_preview(columns, rgb_data)

    def get_gpl_data(self):
        u"""パレットファイル(.gpl)を読み込み."""
        dir = PALETTES_DIR
        dt = {}
        for fname in os.listdir(dir):
            path, ext = os.path.splitext(fname)
            if ext.lower() == ".gpl":
                d = self.read_gpl_file(dir, fname)
                if d is not None:
                    fname, name, columns, rgb_data = d
                    name = name.lower()
                    dt[name] = (fname, columns, rgb_data)
        return dt

    def read_gpl_file(self, dir, fname):
        u"""gplファイルを1つ読み込んで内容をタブルで返す."""
        name = fname
        columns = 16
        rgb_data = []
        fpath = os.path.join(dir, fname).replace(os.path.sep, '/')

        r1 = re.compile(r"Name:\s+(.+)$")
        r2 = re.compile(r"Columns:\s+(\d+)$")
        r4 = re.compile(r"^\s*(\d+)\s+(\d+)\s+(\d+)\s+(.+)$")
        r5 = re.compile(r"^\s*$")

        f = open(fpath, 'r')
        for (i, s) in enumerate(f):
            s = s.rstrip()
            if i == 0:
                if s != "GIMP Palette":
                    return None
            elif i == 1:
                m = r1.match(s)
                if m:
                    name = m.group(1)
                else:
                    print("Error : %s" & s)
                    return None
            elif i == 2:
                m = r2.match(s)
                if m:
                    columns = int(m.group(1))
                else:
                    print("Error : %s" & s)
                    return None
            elif s.find("#") == 0:
                continue
            elif r5.match(s):
                continue
            else:
                m = r4.match(s)
                if m:
                    r, g, b, colname = m.groups()
                    rgb_data.append([int(r), int(g), int(b), colname])
                else:
                    print("Error : %s" & s)
                    return None
        f.close()
        return (fname, name, columns, rgb_data)
