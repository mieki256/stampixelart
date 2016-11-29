# -*- coding: utf-8 -*-
"""py2exe config."""

import sys
import os

if sys.platform == "win32":
    # Windows
    import py2exe
    from distutils.core import setup

    IMAGELIB_DIR = r"D:\Python\Python27\Lib\site-packages\PySide\plugins\imageformats"
    imgfiles = [os.path.join(IMAGELIB_DIR, i) for i in [
        "qgif4.dll",
        "qgifd4.dll",
        "qico4.dll",
        "qicod4.dll",
        "qjpeg4.dll",
        "qjpegd4.dll",
        "qmng4.dll",
        "qmngd4.dll",
        "qsvg4.dll",
        "qsvgd4.dll",
        "qtga4.dll",
        "qtgad4.dll",
        "qtiff4.dll",
        "qtiffd4.dll",
    ]]

    data_files = [("imageformats", imgfiles)]

    py2exe_options = {
        "compressed": 1,
        "optimize": 2,
        "bundle_files": 3
    }

    setup(
        data_files=data_files,
        options={"py2exe": py2exe_options},
        # console = [
        windows=[
            {"script": "stampixelart.py"}
        ],
        zipfile="lib/libs.zip"
    )

if sys.platform == 'darwin':
    # OS X
    pass

if sys.platform == 'linux2':
    # Linux
    pass
