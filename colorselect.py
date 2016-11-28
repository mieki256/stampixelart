#!python
# -*- mode: python; Encoding: utf-8; coding: utf-8 -*-
# Last updated: <2016/11/29 03:57:39 +0900>
# pylint: disable=C0103,W0401,W0602,W0603,W0613,W0614,E1101
u"""色選択スライダー関連クラス群."""

from PySide.QtCore import *     # NOQA
from PySide.QtGui import *      # NOQA


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
