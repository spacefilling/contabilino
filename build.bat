@echo off
echo === Contabilino - Build ===
echo.

REM Installa dipendenze
pip install -r requirements.txt

echo.
echo Compilazione in corso...
echo.

python strumenti\versione_exe.py
pyinstaller --onefile --windowed --name Contabilino --icon risorse\contabilino.ico --hidden-import openpyxl --collect-data sv_ttk --version-file versione_exe.txt main.py

echo.
echo === Build completata ===
echo L'eseguibile si trova in: dist\Contabilino.exe
echo Copia Contabilino.exe sulla chiavetta USB insieme al file .db
echo.
pause
