@echo off
setlocal
cd /d "%~dp0"

set PYTHON_VERSION=3.12.10
set PYTHON_INSTALLER_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-amd64.exe
set PYTHON_INSTALLER=%TEMP%\python-%PYTHON_VERSION%-amd64.exe
set PYTHON_HOME=%LOCALAPPDATA%\Programs\Python\Python312

echo === Instalando el Clasificador de Fotos ===
echo.

set PYCMD=

where py >nul 2>nul
if not errorlevel 1 set PYCMD=py -3

if not defined PYCMD (
    where python >nul 2>nul
    if not errorlevel 1 set PYCMD=python
)

if not defined PYCMD (
    if exist "%PYTHON_HOME%\python.exe" set PYCMD="%PYTHON_HOME%\python.exe"
)

if not defined PYCMD (
    echo No se encontro Python instalado en esta PC.
    echo Descargando Python %PYTHON_VERSION% ^(se instala solo para tu usuario,
    echo NO hace falta ser administrador^)...
    echo.

    where curl >nul 2>nul
    if not errorlevel 1 (
        curl -L -o "%PYTHON_INSTALLER%" "%PYTHON_INSTALLER_URL%"
    ) else (
        powershell -NoProfile -Command "Invoke-WebRequest -Uri '%PYTHON_INSTALLER_URL%' -OutFile '%PYTHON_INSTALLER%'"
    )

    if not exist "%PYTHON_INSTALLER%" (
        echo.
        echo No se pudo descargar el instalador de Python.
        echo Revisa tu conexion a internet e intenta de nuevo.
        echo Tambien podes instalarlo manualmente desde https://www.python.org/downloads/
        pause
        exit /b 1
    )

    echo Instalando Python %PYTHON_VERSION% ^(esto puede tardar un par de minutos^)...
    start /wait "" "%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0

    del "%PYTHON_INSTALLER%" >nul 2>nul

    if not exist "%PYTHON_HOME%\python.exe" (
        echo.
        echo La instalacion de Python no se completo correctamente.
        echo Instalalo manualmente desde https://www.python.org/downloads/
        echo marcando la casilla "Add python.exe to PATH", y volve a correr este archivo.
        pause
        exit /b 1
    )

    set PYCMD="%PYTHON_HOME%\python.exe"
    echo Python instalado correctamente.
)

echo.
echo Version de Python detectada:
%PYCMD% --version
echo.

echo Creando entorno virtual (venv_windows)...
%PYCMD% -m venv venv_windows
if errorlevel 1 (
    echo.
    echo No se pudo crear el entorno virtual.
    pause
    exit /b 1
)

call venv_windows\Scripts\activate.bat

echo Actualizando pip...
python -m pip install --upgrade pip

echo.
echo Instalando dependencias, esto puede tardar varios minutos...
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo Hubo un error instalando las dependencias.
    echo Revisa que tengas conexion a internet e intenta de nuevo.
    pause
    exit /b 1
)

echo.
echo === Instalacion completa ===
echo A partir de ahora, para el modo Tinder hace doble clic en "ejecutar_web.bat"
echo Para el modo automatico con IA, usa "ejecutar.bat"
echo Para el pulido final ^(paso 3^), usa "pulir.bat"
echo.
pause
