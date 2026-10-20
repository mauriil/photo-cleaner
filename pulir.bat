@echo off
setlocal
cd /d "%~dp0"

if not exist venv_windows\Scripts\activate.bat (
    echo No se encontro la instalacion todavia.
    echo Primero hace doble clic en "instalar.bat" una sola vez.
    echo.
    pause
    exit /b 1
)

call venv_windows\Scripts\activate.bat
python pulir_fotos.py %*

echo.
pause
