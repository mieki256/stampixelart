#!python
# -*- mode: python; Encoding: utf-8; coding: utf-8 -*-
# Last updated: <2016/11/29 03:42:45 +0900>
# pylint: disable=C0103,W0401,W0602,W0603,W0613,W0614,E1101
u"""ブラシ画像を管理するクラス群."""

import os
from PIL import Image


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
