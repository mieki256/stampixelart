#!python
# -*- mode: python; Encoding: utf-8; coding: utf-8 -*-
# Last updated: <2016/12/01 01:51:25 +0900>
# pylint: disable=C0103,W0401,W0602,W0603,W0613,W0614,E1101
u"""キャンバスサイズ入力ダイアログ."""

from PySide.QtCore import *     # NOQA
from PySide.QtGui import *      # NOQA


class CanvasSizeDialog(QDialog):

    u"""キャンバスサイズ入力ダイアログ."""

    DEF_W = 256
    DEF_H = 256

    def __init__(self, *argv, **keywords):
        """init."""
        super(CanvasSizeDialog, self).__init__(*argv, **keywords)
        self.setWindowTitle("Input new canvas size")
        self.init_spinbox()
        self.init_ok_cancel()

        # 各ウィジェットをレイアウト
        gl = QGridLayout()
        gl.addWidget(QLabel("Input new canvas size", self), 0, 0, 1, 4)
        gl.addWidget(self.input_w, 1, 0)
        gl.addWidget(QLabel("x", self), 1, 1)
        gl.addWidget(self.input_h, 1, 2)
        gl.addWidget(self.btns, 2, 3)
        self.setLayout(gl)

    def init_spinbox(self):
        u"""スピンボックスを用意."""
        self.input_w = QSpinBox(self)
        self.input_h = QSpinBox(self)
        self.input_w.setRange(1, 8192)  # 値の範囲
        self.input_h.setRange(1, 8192)
        self.input_w.setFixedWidth(80)  # 表示する横幅を指定
        self.input_h.setFixedWidth(80)
        self.input_w.setValue(CanvasSizeDialog.DEF_W)  # 初期値を設定
        self.input_h.setValue(CanvasSizeDialog.DEF_H)

    def init_ok_cancel(self):
        u"""ダイアログのOK/キャンセルボタンを用意."""
        self.btns = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        self.btns.accepted.connect(self.accept)
        self.btns.rejected.connect(self.reject)

    def canvas_size(self):
        u"""キャンバスサイズを取得。(w, h)で返す."""
        w = int(self.input_w.value())
        h = int(self.input_h.value())
        return (w, h)

    @staticmethod
    def get_canvas_size(parent=None):
        u"""ダイアログを開いてキャンバスサイズとOKキャンセルを返す."""
        dialog = CanvasSizeDialog(parent)
        result = dialog.exec_()  # ダイアログを開く
        w, h = dialog.canvas_size()  # キャンバスサイズを取得
        return (w, h, result == QDialog.Accepted)
