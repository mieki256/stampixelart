#!python
# -*- mode: python; Encoding: utf-8; coding: utf-8 -*-
# Last updated: <2016/12/01 05:30:19 +0900>
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

import os
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

from colorselect import ColorSelectSliders
from brushselect import BrushSelectArea
from palettepreview import PaletteSelect
from drawview import DrawAreaView
from canvassizedialog import CanvasSizeDialog
from gridsizedialog import GridSizeDialog

__version__ = "0.0.4"
__author__ = "mieki256"
__license__ = "CC0 / Public Domain"
APPLI_NAME = "Stampixelart"

URIS = [
    "https://www.python.org/",
    "http://www.python.org/psf/license/",
    "http://www.pyside.org/",
    "https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html",
    "http://python-pillow.org/",
    "https://raw.githubusercontent.com/python-pillow/Pillow/master/LICENSE",
]


class BrushSelectDockWidget(QWidget):

    u"""メインウインドウ左側に配置するウィジェット."""

    def __init__(self, parent=None):
        u"""初期化."""
        super(BrushSelectDockWidget, self).__init__(parent)
        self.event_ignore = False

        self.brush_image = QPixmap(32, 32)
        self.brush_image.fill(Qt.black)

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

        pm = QPixmap.fromImage(qimg, Qt.NoOpaqueDetection)
        self.brush_image = pm

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

    def get_brush_image(self):
        u"""現在のブラシ画像を返す."""
        return self.brush_image


class MyMainWindow(QMainWindow):

    u"""メインウインドウ."""

    def __init__(self, parent=None):
        u"""初期化."""
        super(MyMainWindow, self).__init__(parent)
        self.setWindowTitle("%s %s" % (APPLI_NAME, __version__))
        self.setWindowIcon(QIcon("./res/stampixelart.ico"))

        self.cur_dir = QDesktopServices.storageLocation(
            QDesktopServices.DesktopLocation)
        self.cur_filepath = ""
        self.cur_filename = ""
        self.tools_kind = 'pen'

        self.grid_size = QSize(8, 8)
        self.grid_opacity = 0.25
        self.grid_col = QColor(255, 0, 0, 255)

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

        self.gridshow_act = QAction(QIcon("./res/show-grid.svg"),
                                    "Show &Grid", self,
                                    checkable=True,
                                    shortcut="Ctrl+G",
                                    triggered=self.show_grid)

        self.gridcfg_act = QAction(QIcon("./res/configure-grid.svg"),
                                   "Grid &Setting", self,
                                   shortcut=QKeySequence(
                                       Qt.CTRL + Qt.SHIFT + Qt.Key_G),
                                   triggered=self.setting_grid)

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
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.gridshow_act)
        self.view_menu.addAction(self.gridcfg_act)

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
        self.view_menu.addSeparator()
        self.view_tb.addAction(self.gridshow_act)
        self.view_tb.addAction(self.gridcfg_act)

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
        zoom_lbl = QLabel("100%", self.statusBar())
        zoom_lbl.setFixedWidth(64)
        zoom_lbl.setFrameStyle(QFrame.Box | QFrame.Sunken)
        zoom_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.zoom_lbl = zoom_lbl

        # ステータスバーに追加
        self.statusBar().addPermanentWidget(zoomout_btn)
        self.statusBar().addPermanentWidget(zoom_lbl)
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

    def set_zoom_lbl_text(self, str):
        u"""ズーム率表示用ラベルのテキストを設定."""
        self.zoom_lbl.setText(str)

    def clear_canvas(self):
        u"""キャンバスをクリア."""
        self.gview.clear_canvas()
        self.set_status("Cleared Canvas.")

    def show_grid(self):
        u"""グリッドの表示切替."""
        if self.gridshow_act.isChecked():
            self.set_status("Show Grid.")
            self.gview.show_grid(self.grid_opacity)
        else:
            self.set_status("Hide Grid.")
            self.gview.hide_grid()

    def setting_grid(self):
        u"""グリッド設定ダイアログを表示."""
        w, h = self.grid_size.width(), self.grid_size.height()
        a = self.grid_opacity
        col = self.grid_col
        dlg = GridSizeDialog(parent=self, w=w, h=h, a=a, col=col)
        result = dlg.exec_()
        if result:
            w, h, a, col = dlg.get_data()
            self.grid_size = QSize(w, h)
            self.grid_opacity = a
            self.grid_col = col
            self.gview.set_grid(self.grid_size, a, col)
            self.set_status("Grid Setting. %d x %d" % (w, h))
            del dlg

    def make_new_canvas(self):
        u"""キャンバス新規作成ダイアログを表示."""
        w, h, result = CanvasSizeDialog.get_canvas_size(self)
        if result:
            self.gview.make_new_canvas(w, h)
            self.gview.set_grid(8, 8, col=Qt.red)
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
        w, h = self.gview.get_canvas_size()
        s = "%s - (%d x %d) - %s %s" % (bn, w, h, APPLI_NAME, __version__)
        self.setWindowTitle(s)

    def set_color(self, col):
        u"""サイドバー上に色を設定."""
        self.sidebar.set_color(col)

    def get_color(self):
        u"""現在色をQColorで返す."""
        return self.sidebar.get_color()

    def get_brush_image(self):
        u"""現在のブラシ画像を返す."""
        return self.sidebar.get_brush_image()

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
