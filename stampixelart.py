#!python
# -*- mode: python; Encoding: utf-8; coding: utf-8 -*-
# Last updated: <2016/11/28 11:32:22 +0900>
# pylint: disable=C0103,W0401,W0602,W0603,W0613,W0614,E1101

u"""
Stampixelart - PySideで作ったドット絵作成用ツール.

パーツをスタンプのように置きながらドット絵を作れる。

カレントフォルダにbrushesフォルダを作成して、ブラシ画像を入れておくこと。
ブラシ画像は、256x256dotのpng画像(1ブラシが32x32dot、8x8個が並ぶ)、
グレースケール or RGBA画像が使える。

Author : mieki256
License : CC0 / Public Domain

OS : Windows10 x64
Python Version : 2.7.12
PySide Version : 1.2.4
Pillow Version : 3.4.2
"""

import cStringIO
import os
import re
import sys
import PIL
import platform
import PySide
from PySide import QtCore
from PySide import QtGui
sys.modules['PyQt4.QtCore'] = QtCore
sys.modules['PyQt4.QtGui'] = QtGui
from PySide.QtCore import *     # NOQA
from PySide.QtGui import *      # NOQA
import PySide.QtSvg             # NOQA
import PySide.QtXml             # NOQA
from PIL import Image
from PIL import ImageDraw
# from PIL import ImageQt

__version__ = "0.0.3"
__author__ = "mieki256"
__license__ = "CC0 / Public Domain"
APPLI_NAME = "Stampixelart"

BRUSHES_DIR = "./brushes"
DEF_BRUSHES_IMG_NAME = "00_default.png"
PALETTES_DIR = "./palettes"
DEF_PALETTE_NAME = "nes"
UNDO_MAX = 30
PADDING = 40
canvas_size = (256, 256)

# ズーム倍率
ZOOM_LIST = [
    1.0 / 32, 1.0 / 24, 1.0 / 20, 1.0 / 16, 1.0 / 12, 1.0 / 8,
    1.0 / 6, 1.0 / 4, 1.0 / 3, 1.0 / 2,
    1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 16.0, 20.0, 24.0, 32.0]

URIS = [
    "https://www.python.org/",
    "http://www.python.org/psf/license/",
    "http://www.pyside.org/",
    "https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html",
    "http://python-pillow.org/",
    "https://raw.githubusercontent.com/python-pillow/Pillow/master/LICENSE",
]

brush_image = None
zoom_disp = None


class BrushImageData(object):

    u"""ブラシ全体画像1つ分を保持するクラス."""

    def __init__(self, fpath):
        u"""初期化."""
        self.fpath = fpath
        self.img = Image.open(fpath)
        self.mode = self.img.mode
        self.imgs = []
        self.split_image(self.img)
        self.pixmap = None

    def split_image(self, img):
        u"""32x32ドット単位で画像を分割."""
        del self.imgs[:]  # 配列をクリア
        src = img.copy().convert("RGBA")
        w, h = src.size
        for y in range(0, h, 32):
            for x in range(0, w, 32):
                self.imgs.append(src.crop((x, y, x + 32, y + 32)))


class BrushImages(object):

    u"""ブラシ全体画像群(PIL Image)を保持するクラス。."""

    def __init__(self, imgspath):
        u"""初期化."""
        self.dir_name = imgspath
        self.images = {}

        # フォルダ内のファイル一覧を取得
        files = os.listdir(self.dir_name)
        for s in files:
            ext = os.path.splitext(s)[1]
            if ext.lower() != ".png":  # png以外はスキップ
                continue

            # PILのImageとして読み込み
            fpath = os.path.join(self.dir_name, s).replace(os.path.sep, '/')
            self.images[s] = BrushImageData(fpath)

    def get_image_names(self):
        u"""画像名一覧をリストで返す."""
        return self.images.keys()

    def get_image(self, name):
        u"""ブラシ全体画像の PIL Image を返す."""
        if name in self.images:
            return self.images[name].img
        return None

    def get_mode(self, name):
        u"""ブラシ全体画像の PIL Image モード文字列を返す."""
        if name in self.images:
            return self.images[name].mode
        return ""

    def get_brush_one(self, name, n):
        u"""ブラシ1つ分の PIL Image を返す."""
        if name in self.images:
            return self.images[name].imgs[n]
        return None


class ImageQtPoor(QImage):

    u"""ImageQt substitute. Supports only RGBA image."""

    def __init__(self, im):
        """convert PIL Image to PySide QImage."""
        self.org_mode = im.mode
        if im.mode != "RGBA":
            im = im.convert("RGBA")
        w, h = im.size
        fmt = QImage.Format_ARGB32
        self.__data = im.tobytes("raw", "BGRA")
        super(ImageQtPoor, self).__init__(self.__data, w, h, fmt)

    @staticmethod
    def fromqimage(qim):
        """convert PySide QImage ro PIL Image."""
        buf = QBuffer()
        buf.open(QIODevice.ReadWrite)
        qim.save(buf, "PNG")
        fp = cStringIO.StringIO()
        fp.write(buf.data())
        buf.close()
        fp.seek(0)
        return Image.open(fp)

    @staticmethod
    def toqimage(pim):
        """convert PIL Image to PySide QImage."""
        fp = cStringIO.StringIO()
        pim.save(fp, "PNG")
        qim = QImage()
        qim.loadFromData(fp.getvalue(), "PNG")
        return qim


class LabelSliderSpinBox(QWidget):

    u"""QLabel,QSlider,QSpinBoxをまとめたWidget."""

    # Signalを用意
    valueChanged = Signal(int)

    def __init__(self, text, parent=None):
        """init."""
        super(LabelSliderSpinBox, self).__init__(parent)
        # self.setContentsMargins(0, 0, 0, 0)
        hl = QHBoxLayout()
        hl.setContentsMargins(0, 0, 0, 0)
        # hl.setSpacing(0)
        self.lbl = QLabel(text, self)
        self.sld = QSlider(Qt.Horizontal, self)
        self.spb = QSpinBox(self)
        hl.addWidget(self.lbl)
        hl.addWidget(self.sld)
        hl.addWidget(self.spb)
        self.setLayout(hl)
        self.sld.valueChanged[int].connect(self.changed_slider_value)
        self.spb.valueChanged[int].connect(self.changed_spinbox_value)

        # 用意したシグナルとスロットを関連付ける
        self.valueChanged[int].connect(self.changedValue)

    def setText(self, text):
        """set QLabel text."""
        self.lbl.setText(text)

    def setRange(self, start_v, end_v):
        """set range QSlider and QSpinBox."""
        self.sld.setRange(start_v, end_v)
        self.spb.setRange(start_v, end_v)

    def setValue(self, value):
        """set value to QSlider and QSpinBox."""
        self.sld.setValue(value)
        self.spb.setValue(value)

    def value(self):
        """get value."""
        return self.spb.value()

    def changed_slider_value(self, n):
        """changed slider value."""
        self.spb.setValue(n)

    def changed_spinbox_value(self, n):
        """changed spinbox value."""
        self.sld.setValue(n)
        self.valueChanged.emit(n)  # 値が変わったのでシグナルを発行

    # スロットを用意する
    @Slot(int)
    def changedValue(self, value):
        """changed slider or spinbox value."""
        pass
        # print("value = %d" % value)


class ColorSelectSliders(QWidget):

    u"""色選択スライダー群。R,G,B,H,S,Lのスライダーが縦に並ぶ."""

    valueChanged = Signal(QColor)

    def __init__(self, parent=None):
        u"""初期化."""
        super(ColorSelectSliders, self).__init__(parent)
        self.event_ignore = False
        self.lo = QVBoxLayout()
        self.lo.setSpacing(1)
        self.lo.setContentsMargins(1, 1, 1, 1)

        data = [
            ("R", 0, 255, 128), ("G", 0, 255, 128), ("B", 0, 255, 128),
            ("H", 0, 360, 180), ("S", 0, 255, 0), ("L", 0, 255, 128)]
        self.sliders = []
        for (i, d) in enumerate(data):
            text, start_v, end_v, init_v = d
            w = LabelSliderSpinBox(text, self)
            w.setRange(start_v, end_v)
            w.setValue(init_v)
            self.lo.addWidget(w)
            self.sliders.append(w)
            if i < 3:
                w.valueChanged.connect(self.changed_rgb)
            else:
                w.valueChanged.connect(self.changed_hsl)

        self.setLayout(self.lo)

        self.valueChanged[QColor].connect(self.changedValue)

    def set_sliders_rgb(self, col):
        u"""RGBスライダーの値を設定."""
        self.set_sliders(0, (col.red(), col.green(), col.blue()))

    def set_sliders_hsl(self, col):
        u"""HSLスライダーの値を設定."""
        h, s, l = col.hslHue(), col.hslSaturation(), col.lightness()
        self.set_sliders(3, (h, s, l))

    def set_sliders(self, idx, v):
        u"""スライダー3つ分の値を設定."""
        for i in range(3):
            if self.sliders[idx + i].value() != v[i]:
                self.sliders[idx + i].setValue(v[i])

    def get_sliders(self, idx):
        u"""スライダー3つ分の値をタプルで返す."""
        v = []
        for i in range(3):
            v.append(self.sliders[idx + i].value())
        return tuple(v)

    def get_color(self):
        u"""現在色をQColorで返す."""
        r, g, b = self.get_sliders(0)
        col = QColor(r, g, b)
        return col

    def set_color(self, col):
        u"""渡されたQColorでスライダー値を設定."""
        self.event_ignore = True
        self.set_sliders_rgb(col)
        self.set_sliders_hsl(col)
        self.event_ignore = False

    def changed_rgb(self, _):
        u"""RGBスライダーが変更された時に呼ばれる処理."""
        if not self.event_ignore:
            self.event_ignore = True
            r, g, b = self.get_sliders(0)
            col = QColor(r, g, b)
            self.set_sliders_hsl(col)
            self.valueChanged.emit(col)
            self.event_ignore = False

    def changed_hsl(self, _):
        u"""HSLスライダーが変更された時に呼ばれる処理."""
        if not self.event_ignore:
            self.event_ignore = True
            h, s, l = self.get_sliders(3)
            col = QColor()
            col.setHsl(h, s, l)
            self.set_sliders_rgb(col)
            self.valueChanged.emit(col)
            self.event_ignore = False

    @Slot(QColor)
    def changedValue(self, col):
        u"""スライダー群の値が変更されたときに呼ばれる処理."""
        pass


class BrushesView(QGraphicsView):

    u"""ブラシ画像を表示するGraphicsView."""

    brushSelected = Signal()

    def __init__(self, *argv, **keywords):
        u"""初期化."""
        super(BrushesView, self).__init__(*argv, **keywords)

        self.setFixedSize(256, 256)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # ブラシ画像読み込み
        self.brushes = BrushImages(os.path.join(os.getcwdu(), BRUSHES_DIR))

        self.brushes_name = DEF_BRUSHES_IMG_NAME
        self.sel_brush_idx = 0
        self.btn_fg = False
        self.pil_brush_image = None

        scene = QGraphicsScene(self)
        self.setScene(scene)

        self.brushes_pm = QPixmap(256, 256)
        self.brushes_pm.fill(Qt.white)
        self.img_item = QGraphicsPixmapItem(self.brushes_pm)
        self.scene().addItem(self.img_item)
        self.sel_rect = self.scene().addRect(0, 0, 31, 31, QPen(Qt.black))

        self.display_brushes_from_name(self.brushes_name)

        self.brushSelected.connect(self.selectedBrush)

    @Slot()
    def selectedBrush(self):
        u"""ブラシが選択された時に呼ばれる処理."""
        pass

    def mousePressEvent(self, event):
        u"""マウスボタンが押された時の処理."""
        if event.button() == Qt.LeftButton:
            if not self.btn_fg:
                # ブラシ選択
                self.btn_fg = True
                p0 = self.mapToScene(event.pos())
                x = int(p0.x()) / 32
                y = int(p0.y()) / 32
                n = y * 8 + x
                self.set_brush_sel_box(n)
                self.brushSelected.emit()

    def mouseReleaseEvent(self, event):
        u"""マウスボタンが離された時の処理."""
        if event.button() == Qt.LeftButton:
            self.btn_fg = False

    def set_brush_sel_box(self, n):
        u"""ブラシ選択枠を設定."""
        self.sel_brush_idx = n
        y = int(n / 8) * 32
        x = int(n % 8) * 32
        self.sel_rect.setRect(x, y, 31, 31)
        self.update()

    def display_brushes_from_name(self, name):
        u"""ブラシ全体画像を表示."""
        self.brushes_name = name
        src = self.brushes.get_image(name)
        imgn = src.copy()
        if imgn.mode != "RGBA":
            imgn = imgn.convert("RGBA")
        qimg = ImageQtPoor(imgn)
        self.brushes_pm = QPixmap.fromImage(qimg, Qt.NoOpaqueDetection)
        self.img_item.setPixmap(self.brushes_pm)

    def get_current_mode(self):
        u"""現在のブラシ画像のモードを、L,P,RGBAの文字列で返す."""
        mode = self.brushes.get_mode(self.brushes_name)
        return mode

    def get_current_mode_str(self):
        u"""現在のブラシ画像のモード文字列を返す."""
        mode = self.get_current_mode()
        s = "Unknown"
        if mode == "L":
            s = "Grayscale"
        elif mode == "P" or mode == "RGBA":
            s = "RGBA"
        return s

    def get_current_brush_pil_image(self):
        u"""選択されてるブラシ1つ分のpilイメージを返す."""
        im = self.brushes.get_brush_one(self.brushes_name, self.sel_brush_idx)
        self.pil_brush_image = im
        return im


class BrushSelectArea(QWidget):

    u"""ブラシ選択領域."""

    brushChanged = Signal()

    def __init__(self, *argv, **keywords):
        u"""初期化."""
        super(BrushSelectArea, self).__init__(*argv, **keywords)
        self.brushes_name = DEF_BRUSHES_IMG_NAME
        self.col_vari_type = 0
        self.col_mode = "RGBA"
        self.brush_pil_img = None

        self.gview = BrushesView(self)
        self.brushes = self.gview.brushes

        self.lo = QVBoxLayout()
        self.lo.setSpacing(2)
        self.lo.setContentsMargins(0, 0, 0, 0)
        self.init_brushes_sel(self.brushes.get_image_names())

        # ブラシ画像表示用 GraphicsScene,Viewを生成
        self.lo.addWidget(self.gview)
        self.show_brushes()

        self.init_color_vari()
        self.init_flip_rot()

        self.setLayout(self.lo)

        self.gview.brushSelected.connect(self.selected_brush)
        self.brushChanged.connect(self.changedBrush)

    @Slot()
    def changedBrush(self):
        u"""ブラシが変更された時に呼ばれる処理."""
        pass

    def init_brushes_sel(self, lst):
        u"""ブラシ画像選択用ComboBoxを生成."""
        hb = QHBoxLayout()
        hb.setSpacing(6)

        # ブラシ画像選択用 ComboBox
        cb = QComboBox(self)
        for s in lst:
            cb.addItem(s)
        cb.currentIndexChanged.connect(self.changed_current_brushes)
        hb.addWidget(cb)
        self.brushes_sel_cb = cb

        # ブラシモード表示用Label
        lb = QLabel("RGBA Mode", self)
        hb.addWidget(lb)
        self.brush_mode_lbl = lb

        self.lo.addLayout(hb)

    def init_color_vari(self):
        u"""色反映処理選択 ComboBoxを生成."""
        hb = QHBoxLayout()
        lb = QLabel("Color variation :", self)
        hb.addWidget(lb)
        cb = QComboBox(self)
        for s in ["Colorize", "Multiply", "Shift"]:
            cb.addItem("%s" % s)
        cb.currentIndexChanged.connect(self.changed_current_color_vari)
        hb.addWidget(cb)

        spc = QSpacerItem(8, 8, hData=QSizePolicy.Expanding)
        hb.addSpacerItem(spc)

        self.lo.addLayout(hb)
        self.col_vari = cb

    def init_flip_rot(self):
        u"""反転と回転と選択."""
        l = QHBoxLayout()
        l.setSpacing(4)
        self.flip_ck_boxs = []

        size = QSize(26, 26)

        lst = [("H Flip", "./res/flip-horizontal.svg"),
               ("V Flip", "./res/flip-vertical.svg")]
        for (i, d) in enumerate(lst):
            tooltip, icon_path = d
            icon = QIcon(icon_path)
            btn = QPushButton(icon, "", self)
            btn.setFixedSize(size)
            btn.setCheckable(True)
            btn.setToolTip(tooltip)
            btn.clicked.connect(self.changed_flip)
            l.addWidget(btn)
            self.flip_ck_boxs.append(btn)

        rot_grp = QButtonGroup()
        lst = [("+0", "./res/transform-rotate-0.svg"),
               ("+90", "./res/transform-rotate-90.svg"),
               ("+180", "./res/transform-rotate-180.svg"),
               ("+270(-90)", "./res/transform-rotate-270.svg")]
        for (i, d) in enumerate(lst):
            tooltip, icon_path = d
            icon = QIcon(icon_path)
            btn = QPushButton(icon, "", self)
            btn.setFixedSize(size)
            btn.setCheckable(True)
            btn.setToolTip(tooltip)
            btn.setChecked(True if i == 0 else False)
            l.addWidget(btn)
            rot_grp.addButton(btn, i)

        self.rot_grp = rot_grp
        rot_grp.buttonClicked.connect(self.changed_rot)

        spc = QSpacerItem(8, 8, hData=QSizePolicy.Expanding)
        l.addSpacerItem(spc)

        self.lo.addLayout(l)

    def changed_flip(self):
        u"""反転チェックボックスの状態が変わった時に呼ばれる処理."""
        self.brushChanged.emit()

    def changed_rot(self):
        u"""回転指定の状態が変わった時に呼ばれる処理."""
        self.brushChanged.emit()

    def is_h_flip(self):
        u"""水平反転チェックボックスの状態をTrue/Falseで返す."""
        return self.flip_ck_boxs[0].isChecked()

    def is_v_flip(self):
        u"""垂直反転チェックボックスの状態をTrue/Falseで返す."""
        return self.flip_ck_boxs[1].isChecked()

    def rot_id(self):
        u"""回転IDを 0,1,2,3 で返す."""
        return self.rot_grp.checkedId()

    def changed_current_brushes(self, n):
        u"""ブラシ全体画像を変更する時に呼ばれる処理."""
        self.brushes_name = self.brushes.get_image_names()[n]
        self.gview.display_brushes_from_name(self.brushes_name)
        s = self.gview.get_current_mode_str()
        self.brush_mode_lbl.setText("%s Mode" % s)
        self.brushChanged.emit()

    def changed_current_color_vari(self, n):
        u"""色反映処理が変更されたときに呼ばれる処理."""
        self.col_vari_type = n
        self.brushChanged.emit()

    def show_brushes(self):
        u"""ブラシ画像を表示するように設定."""
        self.gview.display_brushes_from_name(self.brushes_name)

    def selected_brush(self):
        u"""ブラシがマウスクリックで選択された時に呼ばれる処理."""
        self.brushChanged.emit()

    def get_brush_pil_image(self):
        u"""現在ブラシのPIL画像を返す."""
        return self.gview.get_current_brush_pil_image()

    def get_col_mode(self):
        u"""現在ブラシのモードを、L,P,RGBAで返す."""
        return self.gview.get_current_mode()

    def get_col_vari(self):
        u"""現在の色変え種類を整数で返す."""
        return self.col_vari_type


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


class BrushSelectDockWidget(QWidget):

    u"""メインウインドウ左側に配置するウィジェット."""

    def __init__(self, parent=None):
        u"""初期化."""
        super(BrushSelectDockWidget, self).__init__(parent)
        self.event_ignore = False

        self.lo = QVBoxLayout()
        self.lo.setSpacing(2)
        self.lo.setContentsMargins(6, 1, 6, 1)

        # ブラシ選択領域
        self.brush_sel = BrushSelectArea(self)
        self.brush_sel.brushChanged.connect(self.changed_brush)
        self.lo.addWidget(self.brush_sel)

        # 色表示ボタン
        l = QHBoxLayout()
        btn = QPushButton()
        btn.setFixedSize(32, 32)
        btn.clicked.connect(self.show_color_dialog)
        l.addWidget(btn)
        self.color_disp_btn = btn

        # ブラシ表示ラベル
        lbl = QLabel("", self)
        lbl.setPixmap(QPixmap(32, 32))
        lbl.setFixedSize(32, 32)
        l.addWidget(lbl)
        self.brush_result_lbl = lbl

        spc = QSpacerItem(32, 32, hData=QSizePolicy.Expanding)
        l.addSpacerItem(spc)

        self.lo.addLayout(l)

        # パレットプレビューをレイアウトに登録
        self.palview = PaletteSelect(self)
        self.lo.addWidget(self.palview)
        self.palview.valueGetted[QColor].connect(self.clicked_palette)

        # 色選択用スライダー群をレイアウトに登録
        self.slds = ColorSelectSliders(self)
        self.slds.valueChanged[QColor].connect(self.changed_sliders)
        self.lo.addWidget(self.slds)
        self.update_color_disp_btn(self.slds.get_color())

        # スペーサーをレイアウトに登録
        spc = QSpacerItem(16, 4, vData=QSizePolicy.Expanding)
        self.lo.addSpacerItem(spc)

        self.setLayout(self.lo)

    def clicked_palette(self, col):
        u"""パレットプレビューがクリックされた時の処理."""
        self.set_color(col)

    def set_color(self, col):
        u"""スライダー群に色を設定."""
        self.slds.set_color(col)
        self.changed_sliders(col)

    def get_color(self):
        u"""現在色をQColorで返す."""
        return self.slds.get_color()

    def changed_sliders(self, col):
        u"""スライダー群が操作された時に呼ばれる処理."""
        self.update_color_disp_btn(col)
        self.update_brush()

    def update_color_disp_btn(self, col):
        u"""色表示用ボタンの背景色を変更."""
        ss = "QWidget { background-color: %s }" % col.name()
        self.color_disp_btn.setStyleSheet(ss)

    def show_color_dialog(self):
        u"""色選択ダイアログを表示."""
        old_col = self.slds.get_color()
        col = QColorDialog.getColor(old_col, self)
        if col.isValid():
            self.slds.set_color(col)
            self.changed_sliders(col)

    def check_flip_rot(self):
        u"""反転・回転指定を得る."""
        hflip = self.brush_sel.is_h_flip()
        vflip = self.brush_sel.is_v_flip()
        rot_id = self.brush_sel.rot_id()
        hs = "H" if hflip else "_"
        vs = "V" if vflip else "_"
        print("flip %s %s Rot ID %d" % (hs, vs, rot_id))

    def changed_brush(self):
        u"""ブラシが変更された時に呼ばれる処理."""
        self.update_brush()

    def update_brush(self):
        u"""ブラシを更新."""
        col = self.slds.get_color()
        src = self.brush_sel.get_brush_pil_image()
        mode = self.brush_sel.get_col_mode()
        vari = self.brush_sel.get_col_vari()
        hflip = self.brush_sel.is_h_flip()
        vflip = self.brush_sel.is_v_flip()
        rot_id = self.brush_sel.rot_id()

        if mode == "L":
            # ブラシ画像が元グレースケール
            qimg = self.make_brush_grayscale(src, col)
        elif mode == "P" or mode == "RGBA":
            # ブラシ画像がパレットモード or RGBA
            if vari == 0:
                qimg = self.make_brush_rgba_typea(src, col)
            elif vari == 1:
                qimg = self.make_brush_rgba_typeb(src, col)
            elif vari == 2:
                qimg = self.make_brush_rgba_typec(src, col)
            else:
                print("Unknown color vari %d" % vari)
                return
        else:
            print("Unknown mode %s" % mode)
            return

        if hflip:
            qimg = self.get_hflip_image(qimg)
        if vflip:
            qimg = self.get_vflip_image(qimg)

        if rot_id > 0:
            qimg = self.get_rot_image(qimg, rot_id)

        global brush_image
        pm = QPixmap.fromImage(qimg, Qt.NoOpaqueDetection)
        brush_image = pm

        # ブラシ表示部分を更新
        w, h = pm.width(), pm.height()
        pix = QPixmap(w, h)
        pix.fill(QColor(Qt.white))
        qp = QPainter()
        qp.begin(pix)
        qp.drawPixmap(0, 0, pm)
        qp.end()
        del qp
        self.brush_result_lbl.setPixmap(pix)
        self.brush_result_lbl.update()

    def make_brush_grayscale(self, src_img, col):
        u"""元グレースケール画像から色を反映したブラシを生成."""
        r, g, b = col.red(), col.green(), col.blue()
        src = src_img.copy()
        w, h = src.size
        dst = QImage(w, h, QImage.Format_ARGB32)
        c2 = QColor()
        for y in range(h):
            for x in range(w):
                sr = src.getpixel((x, y))[0]
                # アルファチャンネルのみ元画像の明るさ情報を使って
                # RGBには指定されたRGB値を使う
                c2.setRgb(r, g, b, 255 - sr)
                dst.setPixel(x, y, c2.rgba())
        return dst

    def make_brush_rgba_typea(self, src, col):
        u"""HSLを反映したブラシを生成."""
        w, h = src.size
        b_h, b_s, b_l = col.hslHue(), col.hslSaturation(), col.lightness()
        dst = QImage(w, h, QImage.Format_ARGB32)
        c2 = QColor()
        for y in range(h):
            for x in range(w):
                r, g, b, a = src.getpixel((x, y))

                # 輝度を求める
                l = int(0.2126 * r + 0.7152 * g + 0.0722 * b)
                # l = int(0.299 * r + 0.587 * g + 0.114 * b)
                if l < 0:
                    l = 0
                if l > 255:
                    l = 255

                # HSLを反映
                if b_l > 128:
                    l *= (255.0 - b_l) / 127.0
                    l += (255.0 - ((255 - b_l) * 255.0 / 127.0))
                elif b_l < 128:
                    l *= b_l / 128.0
                l = int(l)
                if l < 0:
                    l = 0
                if l > 255:
                    l = 255
                c2.setHsl(b_h, b_s, l, a)
                dst.setPixel(x, y, c2.rgba())

        return dst

    def make_brush_rgba_typeb(self, src, col):
        u"""ブラシ生成。ドット値が128で指定色が出る."""
        r, g, b = col.red(), col.green(), col.blue()
        w, h = src.size
        dst = QImage(w, h, QImage.Format_ARGB32)
        c2 = QColor()
        for y in range(h):
            for x in range(w):
                sr, sg, sb, sa = src.getpixel((x, y))
                sr = self.multiply_value(sr, r)
                sg = self.multiply_value(sg, g)
                sb = self.multiply_value(sb, b)
                c2.setRgb(sr, sg, sb, sa)
                dst.setPixel(x, y, c2.rgba())
        return dst

    @classmethod
    def multiply_value(cls, v, a):
        u"""128を基準にして値を掛ける."""
        v = int(v * a / 128)
        if v < 0:
            v = 0
        if v > 255:
            v = 255
        return v

    def make_brush_rgba_typec(self, src, col):
        u"""ブラシ生成。ドット値を上下にずらす."""
        r, g, b = col.red(), col.green(), col.blue()
        w, h = src.size
        dst = QImage(w, h, QImage.Format_ARGB32)
        c2 = QColor()
        for y in range(h):
            for x in range(w):
                sr, sg, sb, sa = src.getpixel((x, y))
                sr = self.shift_value(sr, r)
                sg = self.shift_value(sg, g)
                sb = self.shift_value(sb, b)
                c2.setRgb(sr, sg, sb, sa)
                dst.setPixel(x, y, c2.rgba())
        return dst

    @classmethod
    def shift_value(cls, v, a):
        u"""与えられた値を128を基準に上下にずらす."""
        v = int(v + a - 128)
        if v < 0:
            v = 0
        if v > 255:
            v = 255
        return v

    def get_hflip_image(self, img):
        u"""水平反転したQImageを返す."""
        nimg = img.mirrored(True, False)
        return nimg

    def get_vflip_image(self, img):
        u"""垂直反転したQImageを返す."""
        nimg = img.mirrored(False, True)
        return nimg

    def get_rot_image(self, img, id):
        u"""回転したQImageを返す."""
        deg = id * 90
        rot = QTransform()
        rot = rot.rotate(deg)
        nimg = img.transformed(rot)
        return nimg


class DrawScene(QGraphicsScene):

    u"""描画ウインドウ用Scene."""

    BR_PREVIEW = 0
    BR_DRAW = 1
    BR_ERASE = 2

    def __init__(self, *argv, **keywords):
        u"""初期化."""
        super(DrawScene, self).__init__(*argv, **keywords)

        self.undo_buf = []

        # チェック柄用ブラシを生成
        self.chkbrd_brush = QBrush(self.make_checkboard_pixmap())

        # ブラシを描き込むための、中身が空のQPixmapを用意
        global canvas_size
        w, h = canvas_size
        self.canvas_pixmap = QPixmap(w, h)
        self.canvas_pixmap.fill(QColor(0, 0, 0, 0))

        bg = QPixmap(w, h)
        bg.fill(QColor(0, 0, 0, 0))

        # Scene に Item を追加
        self.chkbrd_item = QGraphicsPixmapItem(bg)
        self.addItem(self.chkbrd_item)
        self.chkbrd_item.setOffset(PADDING, PADDING)

        self.canvas_item = QGraphicsPixmapItem(self.canvas_pixmap)
        self.addItem(self.canvas_item)
        self.canvas_item.setOffset(PADDING, PADDING)

        self.brush_pixmap = QPixmap(32, 32)
        self.brush_pixmap.fill(QColor(0, 0, 0, 0))
        self.brush_item = QGraphicsPixmapItem(self.brush_pixmap)
        self.addItem(self.brush_item)

        self.set_chkbrd_bg()

    def load_canvas_image(self, fpath):
        u"""キャンバスに表示する画像ファイルを読み込む."""
        global canvas_size
        self.canvas_pixmap = QPixmap(fpath)
        self.update_canvas()

    def make_new_canvas(self, w, h):
        u"""キャンバスを新規作成."""
        self.canvas_pixmap = QPixmap(w, h)
        self.canvas_pixmap.fill(QColor(0, 0, 0, 0))
        self.update_canvas()

    def update_canvas(self):
        u"""キャンバスを更新."""
        global canvas_size
        w = self.canvas_pixmap.width()
        h = self.canvas_pixmap.height()
        canvas_size = (w, h)
        self.set_chkbrd_bg()
        self.canvas_item.setPixmap(self.canvas_pixmap)
        self.canvas_item.setOffset(PADDING, PADDING)
        self.update()

    def set_chkbrd_bg(self):
        u"""背景のチェックボード柄画像を更新."""
        global canvas_size
        w, h = canvas_size
        bg = QPixmap(w, h)
        qp = QPainter()
        qp.begin(bg)
        qp.fillRect(0, 0, w, h, self.chkbrd_brush)
        qp.end()
        del qp
        self.chkbrd_item.setPixmap(bg)

    @classmethod
    def make_checkboard_pixmap(cls, bgcol=255, graycol=204):
        u"""チェックボード柄のQPixmapを生成して返す."""
        bg = QPixmap(16, 16)
        qp = QPainter()
        qp.begin(bg)
        qp.fillRect(0, 0, 16, 16, QColor(bgcol, bgcol, bgcol))
        col = QColor(graycol, graycol, graycol)
        qp.fillRect(0, 0, 8, 8, col)
        qp.fillRect(8, 8, 8, 8, col)
        qp.end()
        del qp
        return bg

    def set_new_brush_image(self):
        u"""ブラシ画像を設定."""
        global brush_image
        self.brush_item.setPixmap(brush_image)

    def move_brush_cursor(self, pos, draw_kind):
        u"""ブラシカーソルを移動."""
        self.set_visible_brush(True)
        self.set_new_brush_image()
        global brush_image
        x = int(pos.x() - (brush_image.width() / 2))
        y = int(pos.y() - (brush_image.height() / 2))
        self.brush_item.setOffset(x, y)
        if draw_kind != DrawScene.BR_PREVIEW:
            self.drawing(x, y, draw_kind)

    def drawing(self, x, y, draw_kind):
        u"""ブラシで描画、もしくは消しゴム."""
        x = int(x - self.canvas_item.offset().x())
        y = int(y - self.canvas_item.offset().y())
        global brush_image
        qp = QPainter()
        qp.begin(self.canvas_pixmap)

        if draw_kind == DrawScene.BR_ERASE:
            qp.setCompositionMode(QPainter.CompositionMode_DestinationOut)
        else:
            qp.setCompositionMode(QPainter.CompositionMode_SourceOver)

        qp.drawPixmap(x, y, brush_image)
        qp.end()
        del qp

        if not self.canvas_pixmap.hasAlphaChannel():
            print("canvas not have alphachannel. (draw)")

        self.canvas_item.setPixmap(self.canvas_pixmap)

    def get_cur_pos(self, pos):
        u"""キャンバス上でのカーソル座標を取得."""
        x = int(pos.x() - self.canvas_item.offset().x())
        y = int(pos.y() - self.canvas_item.offset().y())
        return (x, y)

    def out_of_range_canvas(self, x, y):
        u"""キャンバス範囲外ならTrueを返す."""
        pm = self.canvas_pixmap
        w, h = pm.width(), pm.height()
        if x < 0 or x >= w or y < 0 or y >= h:
            return True
        return False

    def floodfill(self, pos, col):
        u"""塗り潰しツール."""
        x, y = self.get_cur_pos(pos)
        r, g, b, a = col.red(), col.green(), col.blue(), col.alpha()
        if self.out_of_range_canvas(x, y):
            return
        qim = self.canvas_pixmap.toImage()
        pim = ImageQtPoor.fromqimage(qim)
        if pim.mode != "RGBA":
            pim = pim.convert("RGBA")
        ImageDraw.floodfill(pim, (x, y), (r, g, b, a))  # 塗り潰し(Flood Fill)
        qim2 = ImageQtPoor(pim)
        self.canvas_pixmap = QPixmap.fromImage(qim2, Qt.NoOpaqueDetection)
        self.canvas_item.setPixmap(self.canvas_pixmap)

    def get_rgb_from_canvas(self, pos):
        u"""キャンバスの指定座標から色(QColor)を取得."""
        x, y = self.get_cur_pos(pos)
        if self.out_of_range_canvas(x, y):
            return None
        qim = self.canvas_pixmap.toImage()
        rgba = QColor()
        rgba.setRgba(qim.pixel(x, y))
        return rgba

    def set_visible_brush(self, flag):
        u"""ブラシ表示の有効無効切り替え。Trueなら表示有効化."""
        if flag:
            if not self.brush_item.isVisible():
                self.brush_item.setVisible(True)
        else:
            if self.brush_item.isVisible():
                self.brush_item.setVisible(False)

    def set_brush_opacity(self, value):
        u"""ブラシ表示画像の透明度を指定。0.0で透明。1.0で不透明."""
        self.brush_item.setOpacity(value)

    def clear_canvas(self):
        u"""キャンバス相当をクリア."""
        self.canvas_pixmap.fill(QColor(0, 0, 0, 0))
        self.canvas_item.setPixmap(self.canvas_pixmap)

    def save_canvas(self, fpath):
        u"""キャンバスを画像ファイルとして保存."""
        self.canvas_pixmap.save(fpath, "PNG")

    def save_undo(self):
        u"""キャンバスをUndoバッファに記憶."""
        if len(self.undo_buf) > UNDO_MAX:
            del(self.undo_buf[0])
        self.undo_buf.append(self.canvas_pixmap.copy())

    def undo(self):
        u"""キャンバスをUndo."""
        if len(self.undo_buf) <= 0:
            return False

        pm = self.undo_buf.pop()
        self.canvas_pixmap = pm.copy()
        self.canvas_item.setPixmap(self.canvas_pixmap)
        return True


class DrawAreaView(QGraphicsView):

    u"""メインとなるビュー."""

    def __init__(self, *argv, **keywords):
        u"""初期化."""
        super(DrawAreaView, self).__init__(*argv, **keywords)

        # マウスカーソル画像を読み込み
        self.init_mouse_cursor()
        self.change_mouse_cursor("pen")

        self.zoom_factor = 1.0
        self.buttonKind = Qt.NoButton
        self.oldCurPos = QPoint(0, 0)
        self.setCacheMode(QGraphicsView.CacheBackground)

        # 背景色を設定
        self.setBackgroundBrush(Qt.darkGray)

        # sceneを登録
        gview_scene = DrawScene(self)
        self.setScene(gview_scene)
        self.set_scene_new_rect()

        # 子のSceneに対してマウストラッキングを有効に
        self.viewport().setMouseTracking(True)

    def resizeEvent(self, event):
        u"""ビューをリサイズ時にシーンの矩形を更新."""
        super(DrawAreaView, self).resizeEvent(event)
        self.set_scene_new_rect()

    def scrollContentsBy(self, dx, dy):
        u"""スクロールバー操作時に呼ばれる処理."""
        # スクロール中、Scene内にブラシがあるとゴミが残るのでブラシを非表示に
        self.scene().set_visible_brush(False)
        super(DrawAreaView, self).scrollContentsBy(dx, dy)

    def set_scene_new_rect(self):
        u"""Sceneの矩形を更新."""
        global canvas_size
        w, h = canvas_size

        # キャンバスサイズに余白をつける
        w += PADDING * 2
        h += PADDING * 2

        # Sceneの矩形を更新。自動でスクロールバーの長さも変わってくれる
        self.scene().setSceneRect(QRectF(0, 0, w, h))

    def add_scrollbar_value(self, dx, dy):
        u"""スクロールバーの現在値を変化させる."""
        x = self.horizontalScrollBar().value()
        y = self.verticalScrollBar().value()
        self.horizontalScrollBar().setValue(x + dx)
        self.verticalScrollBar().setValue(y + dy)

    def init_mouse_cursor(self):
        u"""マウスカーソル画像を読み込み."""
        lst = [
            ("pen", "./res/mouse_cursor_pen.png", 0, 0),
            ("eraser", "./res/mouse_cursor_eraser.png", 0, 0),
            ("picker", "./res/mouse_cursor_picker.png", 9, 22),
            ("fill", "./res/mouse_cursor_fill.png", 9, 22),
        ]
        self.curs = {}
        for d in lst:
            name, filepath, hx, hy = d
            cur = QPixmap(filepath)
            self.curs[name] = QCursor(cur, hotX=hx, hotY=hy)

    def change_mouse_cursor(self, kind):
        u"""マウスカーソルを変更させる."""
        if kind in self.curs:
            self.setCursor(self.curs[kind])
        elif kind == "scroll":
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.unsetCursor()

    def unset_mouse_cursor(self):
        u"""マウスカーソルを元に戻す."""
        self.unsetCursor()

    def mousePressEvent(self, event):
        u"""マウスボタンが押された際の処理."""
        if event.button() == Qt.LeftButton:
            # 左クリックでブラシ描画開始
            self.buttonKind = Qt.LeftButton
            self.scene().save_undo()
            if self.tools_kind() == "pen":
                self.move_brush(event.pos(), DrawScene.BR_DRAW)
            elif self.tools_kind() == "eraser":
                self.move_brush(event.pos(), DrawScene.BR_ERASE)
            elif self.tools_kind() == "fill":
                self.floodfill(event.pos())
        elif event.button() == Qt.MidButton:
            # 中ボタンでスクロール開始
            self.buttonKind = Qt.MidButton
            self.change_mouse_cursor("scroll")
        elif event.button() == Qt.RightButton:
            # 右クリックで色取得
            self.buttonKind = Qt.RightButton
            self.scene().set_visible_brush(False)
            self.change_mouse_cursor("picker")
            self.get_rgb_from_canvas(event.pos())
        self.oldCurPos = event.pos()

    def mouseMoveEvent(self, event):
        u"""マウスカーソル移動中の処理."""
        if self.buttonKind == Qt.LeftButton:
            if self.tools_kind() == "pen":
                self.move_brush(event.pos(), DrawScene.BR_DRAW)
            elif self.tools_kind() == "eraser":
                self.move_brush(event.pos(), DrawScene.BR_ERASE)
        elif self.buttonKind == Qt.MidButton:
            mv = self.oldCurPos - event.pos()
            self.oldCurPos = event.pos()
            self.add_scrollbar_value(mv.x(), mv.y())
        elif self.buttonKind == Qt.RightButton:
            self.get_rgb_from_canvas(event.pos())
        else:
            if self.tools_kind() != "fill":
                self.move_brush(event.pos(), DrawScene.BR_PREVIEW)

    def mouseReleaseEvent(self, event):
        u"""マウスボタンが離されたときの処理."""
        if event.button() == Qt.LeftButton:
            self.buttonKind = Qt.NoButton
        elif event.button() == Qt.MidButton:
            self.buttonKind = Qt.NoButton
            self.change_mouse_cursor(self.tools_kind())
        elif event.button() == Qt.RightButton:
            self.buttonKind = Qt.NoButton
            self.change_mouse_cursor(self.tools_kind())

    def wheelEvent(self, event):
        u"""マウスホイール回転時の処理。ズーム変更."""
        d = 1 if event.delta() > 0 else -1
        v = self.change_zoom_value(d)
        p0 = self.mapToScene(event.pos())
        self.resetMatrix()
        self.scale(v, v)
        p1 = self.mapFromScene(p0)
        mv = p1 - event.pos()
        self.add_scrollbar_value(mv.x(), mv.y())

    def move_brush(self, pos, draw_kind=DrawScene.BR_PREVIEW):
        u"""ブラシカーソル移動."""
        scenePos = self.mapToScene(pos)
        self.scene().move_brush_cursor(scenePos, draw_kind)

    def floodfill(self, pos):
        u"""塗り潰し."""
        col = self.parent().get_color()
        scenePos = self.mapToScene(pos)
        self.scene().floodfill(scenePos, col)

    def get_rgb_from_canvas(self, pos):
        u"""キャンバスから色を取得."""
        scenePos = self.mapToScene(pos)
        rgba = self.scene().get_rgb_from_canvas(scenePos)
        if rgba is not None:
            self.parent().set_color(rgba)

    def change_zoom_ratio(self, d):
        u"""外部から与えられた値でズーム変更."""
        v = self.change_zoom_value(d)
        self.resetMatrix()
        self.scale(v, v)

    def fit_zoom(self):
        u"""ウインドウサイズに合わせてズーム変更."""
        cr = self.scene().sceneRect()
        vr = self.viewport().rect()
        ax = float(vr.width()) / float(cr.width())
        ay = float(vr.height()) / float(cr.height())
        v = ax if ax <= ay else ay
        self.resetMatrix()
        self.scale(v, v)
        self.zoom_factor = v
        self.disp_zoom_factor(self.zoom_factor)

    def zoom_actual_pixels(self):
        u"""等倍表示."""
        v = 1.0
        self.resetMatrix()
        self.scale(v, v)
        self.zoom_factor = v
        self.disp_zoom_factor(self.zoom_factor)

    def change_zoom_value(self, d):
        u"""ズーム倍率を持つ変数をテーブルと比較しつつ変更."""
        global ZOOM_LIST
        if d > 0:
            for v in ZOOM_LIST:
                if self.zoom_factor < v:
                    self.zoom_factor = v
                    break
            else:
                self.zoom_factor = ZOOM_LIST[-1]
        elif d < 0:
            for v in reversed(ZOOM_LIST):
                if self.zoom_factor > v:
                    self.zoom_factor = v
                    break
            else:
                self.zoom_factor = ZOOM_LIST[0]

        self.disp_zoom_factor(self.zoom_factor)
        return self.zoom_factor

    @classmethod
    def disp_zoom_factor(cls, v):
        u"""ズーム倍率をステータスバー右に表示."""
        global zoom_disp
        zoom_disp.setText("%d%s" % (int(v * 100), '%'))

    def clear_canvas(self):
        u"""キャンバスクリア."""
        self.scene().clear_canvas()

    def load_canvas_image(self, fpath):
        u"""画像ファイルを読み込み."""
        self.scene().load_canvas_image(fpath)
        self.set_scene_new_rect()

    def make_new_canvas(self, w, h):
        u"""キャンバスを新規作成."""
        self.scene().make_new_canvas(w, h)
        self.set_scene_new_rect()

    def undo(self):
        u"""キャンバスをUndo."""
        return self.scene().undo()

    def tools_kind(self):
        u"""ツール種類を文字列('pen', 'eraser')で返す."""
        return self.parent().tools_kind

    def set_brush_opacity(self, value):
        u"""ブラシ表示画像の透明度を指定。0.0で透明。1.0で不透明."""
        self.scene().set_brush_opacity(value)

    def set_visible_brush(self, fg):
        u"""ブラシカーソルの表示・表示を設定."""
        self.scene().set_visible_brush(fg)


class CanvasSizeInputDialog(QDialog):

    u"""キャンバスサイズ入力ダイアログ."""

    DEF_W = 256
    DEF_H = 256

    def __init__(self, *argv, **keywords):
        """init."""
        super(CanvasSizeInputDialog, self).__init__(*argv, **keywords)
        self.setWindowTitle("Input new canvas size")

        # スピンボックスを用意
        self.input_w = QSpinBox(self)
        self.input_h = QSpinBox(self)
        self.input_w.setRange(1, 8192)  # 値の範囲
        self.input_h.setRange(1, 8192)
        self.input_w.setFixedWidth(80)  # 表示する横幅を指定
        self.input_h.setFixedWidth(80)
        self.input_w.setValue(CanvasSizeInputDialog.DEF_W)  # 初期値を設定
        self.input_h.setValue(CanvasSizeInputDialog.DEF_H)

        # ダイアログのOK/キャンセルボタンを用意
        btns = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        # 各ウィジェットをレイアウト
        gl = QGridLayout()
        gl.addWidget(QLabel("Input new canvas size", self), 0, 0, 1, 4)
        gl.addWidget(self.input_w, 1, 0)
        gl.addWidget(QLabel("x", self), 1, 1)
        gl.addWidget(self.input_h, 1, 2)
        gl.addWidget(btns, 2, 3)
        self.setLayout(gl)

    def canvas_size(self):
        u"""キャンバスサイズを取得。(w, h)で返す."""
        w = int(self.input_w.value())
        h = int(self.input_h.value())
        return (w, h)

    @staticmethod
    def get_canvas_size(parent=None):
        u"""ダイアログを開いてキャンバスサイズとOKキャンセルを返す."""
        dialog = CanvasSizeInputDialog(parent)
        result = dialog.exec_()  # ダイアログを開く
        w, h = dialog.canvas_size()  # キャンバスサイズを取得
        return (w, h, result == QDialog.Accepted)


class MyMainWindow(QMainWindow):

    u"""メインウインドウ."""

    def __init__(self, parent=None):
        u"""初期化."""
        super(MyMainWindow, self).__init__(parent)
        self.setWindowTitle("%s %s" % (APPLI_NAME, __version__))
        self.cur_dir = QDesktopServices.storageLocation(
            QDesktopServices.DesktopLocation)
        self.cur_filepath = ""
        self.cur_filename = ""
        self.brush_image = None
        self.tools_kind = 'pen'

        self.init_action()
        self.init_menubar()
        self.init_toolbar()
        self.init_central()
        self.init_sidebar()
        self.init_statusbar()

        self.sidebar.update_brush()      # ブラシ初期化

    def init_action(self):
        u"""アクション初期化."""
        self.new_act = QAction(QIcon("./res/document-new.svg"),
                               "&New", self,
                               shortcut=QKeySequence.New,
                               statusTip="New Canvas",
                               triggered=self.make_new_canvas)

        self.open_act = QAction(QIcon("./res/document-open.svg"),
                                "&Open", self,
                                shortcut=QKeySequence.Open,
                                statusTip="Open Image File",
                                triggered=self.show_open_dialog)

        self.save_act = QAction(QIcon("./res/document-save.svg"),
                                "&Save", self,
                                shortcut=QKeySequence.Save,
                                statusTip="Save Canvas Image",
                                triggered=self.override_save_canvas)

        self.save_as_act = QAction("Save &As...", self,
                                   shortcut=QKeySequence(
                                       Qt.CTRL + Qt.SHIFT + Qt.Key_S),
                                   statusTip="Save Canvas Image",
                                   triggered=self.show_save_dialog)

        self.exit_act = QAction(QIcon("./res/application-exit.svg"),
                                "E&xit", self,
                                shortcut="Alt+X",
                                triggered=qApp.quit)

        self.undo_act = QAction(QIcon("./res/edit-undo.svg"),
                                "&Undo", self,
                                shortcut=QKeySequence.Undo,
                                triggered=self.undo)

        self.cclr_act = QAction("&All Clear", self,
                                statusTip="Canvas All Clear",
                                triggered=self.clear_canvas)

        self.zoomin_act = QAction(QIcon("./res/zoom-in.svg"),
                                  "Zoom &In", self,
                                  shortcut=QKeySequence.ZoomIn,
                                  triggered=self.zoom_in)

        self.zoomout_act = QAction(QIcon("./res/zoom-out.svg"),
                                   "Zoom &Out", self,
                                   shortcut=QKeySequence.ZoomOut,
                                   triggered=self.zoom_out)

        self.zoomact_act = QAction(QIcon("./res/zoom-original.svg"),
                                   "Zoom &1:1", self,
                                   shortcut="Ctrl+1",
                                   triggered=self.zoom_actual_pixels)

        self.zoomfit_act = QAction(QIcon("./res/zoom-fit-best.svg"),
                                   "Zoom &Fit", self,
                                   shortcut="Ctrl+0",
                                   triggered=self.zoom_fit)

        self.pen_act = QAction(QIcon("./res/draw-freehand.svg"),
                               "Pen", self,
                               checkable=True,
                               shortcut="P",
                               triggered=self.pen_tool)

        self.eraser_act = QAction(QIcon("./res/draw-eraser.svg"),
                                  "Eraser", self,
                                  checkable=True,
                                  shortcut="E",
                                  triggered=self.eraser_tool)

        self.fill_act = QAction(QIcon("./res/color-fill.svg"),
                                "Fill", self,
                                checkable=True,
                                shortcut="F",
                                triggered=self.fill_tool)

        self.about_act = QAction("&About", self,
                                 triggered=self.about)

        self.about_qt_act = QAction("About &Qt", self,
                                    triggered=qApp.aboutQt)

        # ツール群をグループ化
        self.tools_grp = QActionGroup(self)
        self.tools_grp.addAction(self.pen_act)
        self.tools_grp.addAction(self.eraser_act)
        self.tools_grp.addAction(self.fill_act)
        self.pen_act.setChecked(True)

    def init_menubar(self):
        u"""メニューに登録."""
        self.file_menu = QMenu("&File", self)
        self.file_menu.addAction(self.new_act)
        self.file_menu.addAction(self.open_act)
        self.file_menu.addAction(self.save_act)
        self.file_menu.addAction(self.save_as_act)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.exit_act)

        self.edit_menu = QMenu("&Edit", self)
        self.edit_menu.addAction(self.undo_act)

        self.canvas_menu = QMenu("&Canvas", self)
        self.canvas_menu.addAction(self.cclr_act)

        self.view_menu = QMenu("&View", self)
        self.view_menu.addAction(self.zoomin_act)
        self.view_menu.addAction(self.zoomout_act)
        self.view_menu.addAction(self.zoomact_act)
        self.view_menu.addAction(self.zoomfit_act)

        self.tools_menu = QMenu("&Tools", self)
        self.tools_menu.addAction(self.pen_act)
        self.tools_menu.addAction(self.eraser_act)
        self.tools_menu.addAction(self.fill_act)

        self.help_menu = QMenu("&Help", self)
        self.help_menu.addAction(self.about_act)
        self.help_menu.addAction(self.about_qt_act)

        # メインウインドウ上のメニューに登録
        mb = QMenuBar(self)
        mb.addMenu(self.file_menu)
        mb.addMenu(self.edit_menu)
        mb.addMenu(self.canvas_menu)
        mb.addMenu(self.view_menu)
        mb.addMenu(self.tools_menu)
        mb.addMenu(self.help_menu)
        self.setMenuBar(mb)

    def init_toolbar(self):
        u"""ツールバーを初期化."""
        # ファイル関係ツールバーを作成
        self.file_tb = QToolBar("File")
        self.file_tb.addAction(self.new_act)
        self.file_tb.addAction(self.open_act)
        self.file_tb.addAction(self.save_act)
        self.file_tb.addSeparator()
        self.file_tb.addAction(self.undo_act)

        # ツール関係ツールバーを作成
        self.tools_tb = QToolBar("Tools")
        self.tools_tb.addAction(self.pen_act)
        self.tools_tb.addAction(self.eraser_act)
        self.tools_tb.addAction(self.fill_act)

        # ズーム関係ツールバーを作成
        self.view_tb = QToolBar("View")
        self.view_tb.addAction(self.zoomout_act)
        self.view_tb.addAction(self.zoomin_act)
        self.view_tb.addAction(self.zoomact_act)
        self.view_tb.addAction(self.zoomfit_act)

        # size = QSize(32, 32)
        # self.file_tb.setIconSize(size)
        # self.tools_tb.setIconSize(size)
        # self.view_tb.setIconSize(size)

        self.addToolBar(self.file_tb)
        self.addToolBar(self.tools_tb)
        self.addToolBar(self.view_tb)

    def init_sidebar(self):
        u"""サイドバー(ブラシ選択部分)初期化."""
        self.sidebar = BrushSelectDockWidget(self)
        self.left_dock = QDockWidget("Brush", self)
        self.left_dock.setWidget(self.sidebar)

        # 移動とフローティングは有効にするが、閉じるボタンは無効にする
        # 注意： メインウインドウが十分大きくないと、
        # フローティング後、元に戻せなくなる
        self.left_dock.setAllowedAreas(
            Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.left_dock.setFeatures(
            QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)

        self.addDockWidget(Qt.LeftDockWidgetArea, self.left_dock)

    def init_central(self):
        u"""中央ウィジェット初期化."""
        self.gview = DrawAreaView(self)
        self.setCentralWidget(self.gview)

    def init_statusbar(self):
        u"""ステータスバー初期化."""
        self.statusBar().showMessage("Ready")

        zoomout_icon = QIcon("./res/zoom-out.svg")
        zoomin_icon = QIcon("./res/zoom-in.svg")
        zoomact_icon = QIcon("./res/zoom-original.svg")
        zoomfit_icon = QIcon("./res/zoom-fit-best.svg")

        # 縮小、拡大、ウインドウに合わせる、等倍表示ボタン
        zoomout_btn = QPushButton(zoomout_icon, "", self.statusBar())
        zoomin_btn = QPushButton(zoomin_icon, "", self.statusBar())
        zoomact_btn = QPushButton(zoomact_icon, "", self.statusBar())
        zoomfit_btn = QPushButton(zoomfit_icon, "", self.statusBar())

        # ボタンが押されたときの処理を登録
        zoomout_btn.clicked.connect(self.zoom_out)
        zoomin_btn.clicked.connect(self.zoom_in)
        zoomact_btn.clicked.connect(self.zoom_actual_pixels)
        zoomfit_btn.clicked.connect(self.zoom_fit)

        # 倍率表示用ラベル
        global zoom_disp
        zoom_disp = QLabel("100%", self.statusBar())
        zoom_disp.setFixedWidth(64)
        zoom_disp.setFrameStyle(QFrame.Box | QFrame.Sunken)
        zoom_disp.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # ステータスバーに追加
        self.statusBar().addPermanentWidget(zoomout_btn)
        self.statusBar().addPermanentWidget(zoom_disp)
        self.statusBar().addPermanentWidget(zoomin_btn)
        self.statusBar().addPermanentWidget(zoomact_btn)
        self.statusBar().addPermanentWidget(zoomfit_btn)

    def set_status(self, msg):
        u"""ステータスバーメッセージを設定."""
        self.statusBar().showMessage(msg)

    def zoom_out(self):
        u"""縮小ボタンを押した時の処理."""
        self.gview.change_zoom_ratio(-1)

    def zoom_in(self):
        u"""拡大ボタンを押した時の処理."""
        self.gview.change_zoom_ratio(1)

    def zoom_fit(self):
        u"""ウインドウに合わせるボタンを押した時の処理."""
        self.gview.fit_zoom()

    def zoom_actual_pixels(self):
        u"""等倍表示."""
        self.gview.zoom_actual_pixels()

    def clear_canvas(self):
        u"""キャンバスをクリア."""
        self.gview.clear_canvas()
        self.set_status("Cleared Canvas.")

    def make_new_canvas(self):
        u"""キャンバス新規作成ダイアログを表示."""
        w, h, result = CanvasSizeInputDialog.get_canvas_size(self)
        if result:
            self.gview.make_new_canvas(w, h)
            self.cur_filepath = ""
            self.set_status("Maked New Canvas.")
            self.set_title()

    def show_open_dialog(self):
        u"""ファイルオープンダイアログを表示."""
        filter = "Image Files (*.png *.bmp *.jpg *.jpeg)"
        fpath, _ = QFileDialog.getOpenFileName(self, "Open File",
                                               self.cur_dir, filter)
        if fpath:
            self.gview.load_canvas_image(fpath)
            self.save_cur_filepath(fpath, "Load")

    def show_save_dialog(self):
        u"""ファイル保存ダイアログを表示."""
        filter = "Image Files (*.png)"
        fpath, _ = QFileDialog.getSaveFileName(self, "Save File",
                                               self.cur_dir, filter)
        if fpath:
            self.gview.scene().save_canvas(fpath)
            self.save_cur_filepath(fpath, "Save As")

    def save_cur_filepath(self, fpath, msg):
        u"""現在ファイルパスを記憶."""
        self.cur_filepath = fpath
        self.cur_dir = os.path.dirname(fpath)
        self.set_status("%s %s" % (msg, fpath))
        self.set_title()

    def override_save_canvas(self):
        u"""キャンバスを上書き保存."""
        if self.cur_filepath == "":
            self.show_save_dialog()
        else:
            self.gview.scene().save_canvas(self.cur_filepath)
            self.set_status("Save %s" % self.cur_filepath)
            self.set_title()

    def set_title(self):
        u"""ウインドウタイトルを設定."""
        if self.cur_filepath == "":
            bn = "<New>"
        else:
            bn = os.path.basename(self.cur_filepath)
        global canvas_size
        w, h = canvas_size
        s = "%s - (%d x %d) - %s %s" % (bn, w, h, APPLI_NAME, __version__)
        self.setWindowTitle(s)

    def set_color(self, col):
        u"""サイドバー上に色を設定."""
        self.sidebar.set_color(col)

    def get_color(self):
        u"""現在色をQColorで返す."""
        return self.sidebar.get_color()

    def undo(self):
        """Undo."""
        if self.gview.undo():
            self.set_status("Undo.")
        else:
            self.set_status("Can not undo any more.")

    def pen_tool(self):
        """pen tool."""
        self.statusBar().showMessage("Pen / LMB:Draw / RMB:Color Picker")
        self.tools_kind = 'pen'
        self.gview.set_brush_opacity(1.0)
        self.gview.set_visible_brush(True)
        self.gview.change_mouse_cursor("pen")

    def eraser_tool(self):
        """eraser tool."""
        self.statusBar().showMessage("Eraser / LMB:Erase")
        self.tools_kind = 'eraser'
        self.gview.set_brush_opacity(0.5)
        self.gview.set_visible_brush(True)
        self.gview.change_mouse_cursor("eraser")

    def fill_tool(self):
        """fill tool."""
        self.statusBar().showMessage("Fill / LMB:Fill")
        self.tools_kind = 'fill'
        self.gview.set_visible_brush(False)
        self.gview.change_mouse_cursor("fill")

    def about(self):
        """display about."""
        py_uri = URIS[0]
        py_ver = platform.python_version()
        py_lic = "PSFL"
        py_licu = URIS[1]

        pys_uri = URIS[2]
        pys_ver = PySide.__version__
        pys_lic = "LGPL 2.1"
        pys_licu = URIS[3]

        pil_uri = URIS[4]
        pil_ver = PIL.PILLOW_VERSION
        pil_lic = "PIL Software License"
        pil_licu = URIS[5]

        ss = '&nbsp;&nbsp;&nbsp;&nbsp;'

        s = "%s %s<br><br>" % (APPLI_NAME, __version__)
        s += "Author : %s<br>License : %s" % (__author__, __license__)
        s += "<br><br><br>"

        s += "Python %s" % (py_ver)
        s += ss
        s += "<a href=\"%s\">%s</a>" % (py_uri, py_uri)
        s += ss
        s += "License : <a href=\"%s\">%s</a><br>" % (py_licu, py_lic)

        s += "PySide %s" % (pys_ver)
        s += ss
        s += "<a href=\"%s\">%s</a>" % (pys_uri, pys_uri)
        s += ss
        s += "License : <a href=\"%s\">%s</a><br>" % (pys_licu, pys_lic)

        s += "Pillow %s" % (pil_ver)
        s += ss
        s += "<a href=\"%s\">%s</a>" % (pil_uri, pil_uri)
        s += ss
        s += "License : <a href=\"%s\">%s</a>" % (pil_licu, pil_lic)

        QMessageBox.about(self, "About Application", s)


def main():
    u"""メイン."""
    app = QApplication(sys.argv)
    # app.setStyle(QStyleFactory.create("motif"))
    # app.setStyle(QStyleFactory.create("windows"))
    w = MyMainWindow()
    w.resize(800, 700)
    w.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
