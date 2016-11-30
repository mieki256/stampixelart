#!python
# -*- mode: python; Encoding: utf-8; coding: utf-8 -*-
# Last updated: <2016/12/01 04:52:20 +0900>
# pylint: disable=C0103,W0401,W0602,W0603,W0613,W0614,E1101
u"""キャンバス関係クラス群."""

import sys
from PySide import QtCore
from PySide import QtGui
sys.modules['PyQt4.QtCore'] = QtCore
sys.modules['PyQt4.QtGui'] = QtGui
from PySide.QtCore import *     # NOQA
from PySide.QtGui import *      # NOQA
from PIL import ImageDraw
from brushimage import *        # NOQA
from imageqtpoor import ImageQtPoor


class DrawScene(QGraphicsScene):

    u"""描画ウインドウ用Scene."""

    UNDO_MAX = 30
    PADDING = 40

    BR_PREVIEW = 0
    BR_DRAW = 1
    BR_ERASE = 2

    DEF_CANVAS_SIZE = (256, 256)

    def __init__(self, *argv, **keywords):
        u"""初期化."""
        super(DrawScene, self).__init__(*argv, **keywords)

        self.grid_size = QSize(8, 8)
        self.grid_opacity = 0.25
        self.grid_color = QColor(255, 0, 0, 255)
        self.undo_buf = []

        # チェック柄用ブラシを生成
        self.chkbrd_brush = QBrush(self.make_checkboard_pixmap())

        # ブラシを描き込むための、中身が空のQPixmapを用意
        w, h = DrawScene.DEF_CANVAS_SIZE
        self.canvas_pixmap = QPixmap(w, h)
        self.canvas_pixmap.fill(Qt.transparent)

        bg = QPixmap(w, h)
        bg.fill(Qt.transparent)

        grid = QPixmap(w, h)
        grid.fill(Qt.transparent)

        # Scene に Item を追加
        # 背景のチェック柄
        self.chkbrd_item = QGraphicsPixmapItem(bg)
        self.addItem(self.chkbrd_item)
        self.chkbrd_item.setOffset(DrawScene.PADDING, DrawScene.PADDING)

        # キャンバス
        self.canvas_item = QGraphicsPixmapItem(self.canvas_pixmap)
        self.addItem(self.canvas_item)
        self.canvas_item.setOffset(DrawScene.PADDING, DrawScene.PADDING)

        # ブラシ
        self.brush_pixmap = QPixmap(32, 32)
        self.brush_pixmap.fill(QColor(0, 0, 0, 0))
        self.brush_item = QGraphicsPixmapItem(self.brush_pixmap)
        self.addItem(self.brush_item)

        # グリッド
        self.grid_pixmap = QPixmap(w, h)
        self.grid_pixmap.fill(Qt.transparent)
        self.grid_item = QGraphicsPixmapItem(self.grid_pixmap)
        self.addItem(self.grid_item)
        self.grid_item.setOffset(DrawScene.PADDING, DrawScene.PADDING)
        self.grid_item.setVisible(False)

        self.set_chkbrd_bg()
        self.set_grid(self.grid_size, self.grid_opacity, self.grid_color)

    def get_canvas_size(self):
        u"""現在のキャンバスサイズをタプルで返す."""
        w = self.canvas_pixmap.width()
        h = self.canvas_pixmap.height()
        return (w, h)

    def load_canvas_image(self, fpath):
        u"""キャンバスに表示する画像ファイルを読み込む."""
        self.canvas_pixmap = QPixmap(fpath)
        self.update_canvas()

    def make_new_canvas(self, w, h):
        u"""キャンバスを新規作成."""
        self.canvas_pixmap = QPixmap(w, h)
        self.canvas_pixmap.fill(QColor(0, 0, 0, 0))
        self.update_canvas()

    def update_canvas(self):
        u"""キャンバスを更新."""
        w, h = self.get_canvas_size()
        self.set_chkbrd_bg()
        self.canvas_item.setPixmap(self.canvas_pixmap)
        self.canvas_item.setOffset(DrawScene.PADDING, DrawScene.PADDING)
        self.update()

    def set_chkbrd_bg(self):
        u"""背景のチェックボード柄画像を更新."""
        w, h = self.get_canvas_size()
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

    def set_grid(self, size, grid_opacity, col=Qt.red):
        u"""グリッド表示レイヤーを指定された升目で作成."""
        self.grid_opacity = grid_opacity
        gw, gh = size.width(), size.height()

        # 升目1つ分を作成
        bpm = self.get_grid_pm_b(gw, gh, col)
        brush = QBrush(bpm)

        # 作った升目でキャンバスサイズのQPixmapを矩形塗り潰し
        w, h = self.get_canvas_size()
        pm = QPixmap(w, h)
        pm.fill(Qt.transparent)
        qp = QPainter()
        qp.begin(pm)
        qp.fillRect(0, 0, w, h, brush)
        qp.end()
        del qp
        del brush
        del bpm
        self.grid_pixmap = pm
        self.grid_item.setPixmap(self.grid_pixmap)

        if self.grid_item.isVisible():
            self.grid_item.setOpacity(self.grid_opacity)

    def get_grid_pm_a(self, gw, gh, col):
        u"""グリッドの升目一つ分を作成して返す."""
        pen = QPen(col, 1, Qt.SolidLine)
        bpm = QPixmap(gw, gh)
        bpm.fill(Qt.transparent)
        qp = QPainter()
        qp.begin(bpm)
        qp.setPen(pen)
        qp.drawPoint(0, 0)
        qp.drawPoint(1, 0)
        qp.drawPoint(2, 0)
        qp.drawPoint(0, 1)
        qp.drawPoint(0, 2)
        qp.drawPoint(gw - 1, gw - 1)
        qp.drawPoint(gw - 2, gw - 1)
        qp.drawPoint(gw - 3, gw - 1)
        qp.drawPoint(gw - 1, gw - 2)
        qp.drawPoint(gw - 1, gw - 3)
        qp.end()
        del qp
        del pen
        return bpm

    def get_grid_pm_b(self, gw, gh, col):
        u"""グリッドの升目一つ分を作成して返す."""
        r, g, b, a = col.red(), col.green(), col.blue(), col.alpha()
        col2 = QColor(r / 2, g / 2, b / 2, a)
        bpm = QPixmap(gw * 2, gh * 2)
        bpm.fill(Qt.transparent)
        qp = QPainter()
        qp.begin(bpm)
        qp.setPen(QPen(col, 1, Qt.SolidLine))
        qp.drawRect(0, 0, gw - 1, gh - 1)
        qp.drawRect(gw, gh, gw - 1, gh - 1)
        qp.setPen(QPen(col2, 1, Qt.SolidLine))
        qp.drawRect(gw, 0, gw - 1, gh - 1)
        qp.drawRect(0, gh, gw - 1, gh - 1)
        qp.end()
        del qp
        return bpm

    def set_new_brush_image(self):
        u"""ブラシ画像を設定."""
        self.brush_item.setPixmap(self.get_brush_image())

    def move_brush_cursor(self, pos, draw_kind):
        u"""ブラシカーソルを移動."""
        self.set_visible_brush(True)
        self.set_new_brush_image()
        pm = self.get_brush_image()
        x = int(pos.x() - (pm.width() / 2))
        y = int(pos.y() - (pm.height() / 2))
        self.brush_item.setOffset(x, y)
        if draw_kind != DrawScene.BR_PREVIEW:
            self.drawing(x, y, draw_kind)

    def drawing(self, x, y, draw_kind):
        u"""ブラシで描画、もしくは消しゴム."""
        x = int(x - self.canvas_item.offset().x())
        y = int(y - self.canvas_item.offset().y())
        bim = self.get_brush_image()
        qp = QPainter()
        qp.begin(self.canvas_pixmap)

        if draw_kind == DrawScene.BR_ERASE:
            qp.setCompositionMode(QPainter.CompositionMode_DestinationOut)
        else:
            qp.setCompositionMode(QPainter.CompositionMode_SourceOver)

        qp.drawPixmap(x, y, bim)
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
        w, h = self.get_canvas_size()
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
        if len(self.undo_buf) > DrawScene.UNDO_MAX:
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

    def get_brush_image(self):
        u"""現在のブラシ画像を返す."""
        return self.parent().get_brush_image()

    def show_grid(self, grid_opacity):
        u"""グリッドを表示. grid_opacityは0.0(透明)-1.0(不透明)の値を取る."""
        self.grid_item.setVisible(True)
        self.grid_item.setOpacity(grid_opacity)

    def hide_grid(self):
        u"""グリッドを非表示."""
        self.grid_item.setVisible(False)


class DrawAreaView(QGraphicsView):

    u"""メインとなるビュー."""

    # ズーム倍率
    ZOOM_LIST = [
        1.0 / 32, 1.0 / 24, 1.0 / 20, 1.0 / 16, 1.0 / 12, 1.0 / 8,
        1.0 / 6, 1.0 / 4, 1.0 / 3, 1.0 / 2,
        1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 16.0, 20.0, 24.0, 32.0]

    def __init__(self, *argv, **keywords):
        u"""初期化."""
        super(DrawAreaView, self).__init__(*argv, **keywords)

        # マウスカーソル画像を読み込み
        self.init_mouse_cursor()
        self.change_mouse_cursor("pen")

        self.zoom_factor = 1.0
        self.zoom_disp = "100%"
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

    def get_canvas_size(self):
        u"""現在のキャンバスサイズをタプルで返す."""
        scene = self.scene()
        w, h = scene.get_canvas_size()
        return (w, h)

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
        w, h = self.get_canvas_size()

        # キャンバスサイズに余白をつける
        w += DrawScene.PADDING * 2
        h += DrawScene.PADDING * 2

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
        if d > 0:
            for v in DrawAreaView.ZOOM_LIST:
                if self.zoom_factor < v:
                    self.zoom_factor = v
                    break
            else:
                self.zoom_factor = DrawAreaView.ZOOM_LIST[-1]
        elif d < 0:
            for v in reversed(DrawAreaView.ZOOM_LIST):
                if self.zoom_factor > v:
                    self.zoom_factor = v
                    break
            else:
                self.zoom_factor = DrawAreaView.ZOOM_LIST[0]

        self.disp_zoom_factor(self.zoom_factor)
        return self.zoom_factor

    def disp_zoom_factor(self, v):
        u"""ズーム倍率をステータスバー右に表示."""
        self.zoom_disp = "%d%s" % (int(v * 100), '%')
        self.parent().set_zoom_lbl_text(self.zoom_disp)

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

    def get_brush_image(self):
        u"""現在のブラシ画像を返す."""
        return self.parent().get_brush_image()

    def show_grid(self, grid_opacity=0.25):
        u"""グリッドを表示."""
        self.scene().show_grid(grid_opacity)

    def hide_grid(self):
        u"""グリッドを非表示."""
        self.scene().hide_grid()

    def set_grid(self, size, grid_opacity, col=Qt.red):
        u"""グリッドの升目サイズを設定."""
        self.scene().set_grid(size, grid_opacity, col)
