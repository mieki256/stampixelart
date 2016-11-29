@echo off
set TGT_DIR=dist

@echo make exe file.

python setup.py py2exe
pause

if exist "%TGT_DIR%\" goto FOUND_DIST
echo Error. Not found %TGT_DIR% folder.
goto END

:FOUND_DIST
echo Found %TGT_DIR% folder.
@echo on
copy README.md %TGT_DIR%
xcopy brushes dist\brushes\
xcopy palettes dist\palettes\
xcopy res dist\res\
xcopy screenshot dist\screenshot\
@echo off
@echo.
@echo success.
@echo use dist\ and dist\*.exe
:END

