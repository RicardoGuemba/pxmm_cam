@echo off
REM Pxmm CAM - Inicializacao 1-clique (Windows)
setlocal
cd /d "%~dp0\.."

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

python "%CD%\run.py"
endlocal
