#!python
# -*- mode: python; Encoding: utf-8; coding: utf-8 -*-
# Last updated: <2016/12/01 05:51:29 +0900>
# pylint: disable=C0103,W0401,W0602,W0603,W0613,W0614,E1101
u"""グリッドサイズ入力ダイアログ."""

import sys
from PySide.QtCore import *     # NOQA
from PySide.QtGui import *      # NOQA


class GridSizeDialog(QDialog):

    u"""グリッドサイズ入力ダイアログ."""

    def __init__(self, parent=None, w=8, h=8, a=0.25, col=None):
        """init."""
        super(GridSizeDialog, self).__init__(parent)
        self.setWindowTitle("Input Grid Size")

        if col is None:
            self.color = QColor(255, 0, 0, 255)
        else:
            self.color = col

        self.init_spinbox(w, h)
        self.init_opacity_inputbox(a)
        self.init_color_disp_btn(self.color)
        self.init_ok_cancel()

        gl = QGridLayout()

        gl.addWidget(QLabel("Grid Size", self), 0, 0)
        gl.addWidget(self.input_w, 0, 1)
        gl.addWidget(QLabel("x", self), 0, 2)
        gl.addWidget(self.input_h, 0, 3)

        gl.addWidget(QLabel("Opacity (0.0 - 1.0)", self), 1, 0)
        gl.addWidget(self.opa_in, 1, 1)

        gl.addWidget(QLabel("Color", self), 2, 0)
        gl.addWidget(self.color_disp_btn, 2, 1)

        gl.addWidget(self.btns, 3, 4, 1, 4)

        self.setLayout(gl)

    def init_spinbox(self, w, h):
        u"""スピンボックスを用意."""
        self.input_w = QSpinBox(self)
        self.input_h = QSpinBox(self)
        self.input_w.setRange(2, 8192)  # 値の範囲
        self.input_h.setRange(2, 8192)
        self.input_w.setValue(w)
        self.input_h.setValue(h)

    def init_opacity_inputbox(self, opa):
        u"""透明度入力ボックスを用意."""
        self.opa_in = QDoubleSpinBox(self)
        self.opa_in.setRange(0.0, 1.0)
        self.opa_in.setSingleStep(0.05)
        self.opa_in.setValue(opa)

    def init_color_disp_btn(self, col):
        u""""色選択ボタンを用意."""
        self.color_disp_btn = QPushButton("", self)
        self.color_disp_btn.clicked.connect(self.show_color_dialog)
        self.update_color_disp_btn(col)

    def init_ok_cancel(self):
        u"""ダイアログのOK/キャンセルボタンを用意."""
        self.btns = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        self.btns.accepted.connect(self.accept)
        self.btns.rejected.connect(self.reject)

    def update_color_disp_btn(self, col):
        u"""色表示用ボタンの背景色を変更."""
        pm = QPixmap(48, 36)
        pm.fill(col)
        self.color_disp_btn.setIcon(QIcon(pm))
        del pm

    def show_color_dialog(self):
        u"""色選択ダイアログを表示."""
        old_col = self.color
        col = QColorDialog.getColor(old_col, self)
        if col.isValid():
            self.color = col
            self.update_color_disp_btn(col)

    def get_data(self):
        u"""サイズ、透明度、色を取得してタプルで返す."""
        w = int(self.input_w.value())
        h = int(self.input_h.value())
        a = self.opa_in.value()
        col = self.color
        return (w, h, a, col)

    @staticmethod
    def get_grid_size(parent=None, w=8, h=8, a=0.25, col=None):
        u"""ダイアログを開いてグリッドサイズとOK / キャンセルを返す."""
        dialog = GridSizeDialog(parent, w, h, a, col)
        result = dialog.exec_()  # ダイアログを開く
        w, h, a, col = dialog.get_data()
        return (w, h, a, col, result == QDialog.Accepted)


if __name__ == '__main__':
    # テスト表示
    app = QApplication(sys.argv)
    w = GridSizeDialog()
    w.show()
    sys.exit(app.exec_())
