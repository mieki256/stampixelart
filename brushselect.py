#!python
# -*- mode: python; Encoding: utf-8; coding: utf-8 -*-
# Last updated: <2016/11/29 04:55:09 +0900>
# pylint: disable=C0103,W0401,W0602,W0603,W0613,W0614,E1101
u"""ブラシ選択関係のクラス群."""

import os
from PySide.QtCore import *     # NOQA
from PySide.QtGui import *      # NOQA
from brushimage import BrushImages
from imageqtpoor import ImageQtPoor

BRUSHES_DIR = "./brushes"
DEF_BRUSHES_IMG_NAME = "00_default.png"


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
