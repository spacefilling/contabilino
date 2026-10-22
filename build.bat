@echo off
echo === Contabilino - Build ===
echo.

REM Installa dipendenze
pip install openpyxl reportlab pyinstaller

echo.
echo Compilazione in corso...
echo.

pyinstaller --onefile --windowed --name Contabilino --hidden-import openpyxl main.py

echo.
echo === Build completata ===
echo L'eseguibile si trova in: dist\Contabilino.exe
echo Copia Contabilino.exe sulla chiavetta USB insieme al file .db
echo.
pause
