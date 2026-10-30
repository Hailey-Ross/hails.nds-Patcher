@echo off
rem Drag .nds files or a folder onto this file.
if "%~1"=="" (
    echo Drag .nds files or a folder onto this file.
) else (
    python "%~dp0hails_patcher.py" %*
)
pause
