#!python
# -*- mode: python; Encoding: utf-8; coding: utf-8 -*-
# Last updated: <2016/11/29 04:00:49 +0900>
# pylint: disable=C0103,W0401,W0602,W0603,W0613,W0614,E1101
u"""PIL Image と QImage を変換するクラス."""

import cStringIO
from PySide.QtCore import *     # NOQA
from PySide.QtGui import *      # NOQA
from PIL import Image


class ImageQtPoor(QImage):

    u"""ImageQt substitute. Supports only RGBA image."""

    def __init__(self, pim):
        """convert PIL Image to PySide QImage."""
        self.org_mode = pim.mode
        if pim.mode != "RGBA":
            pim = pim.convert("RGBA")
        w, h = pim.size
        fmt = QImage.Format_ARGB32
        self.__data = pim.tobytes("raw", "BGRA")
        super(ImageQtPoor, self).__init__(self.__data, w, h, fmt)

    @staticmethod
    def fromqimage(qim):
        """convert PySide QImage to PIL Image."""
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
