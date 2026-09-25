@echo off
setlocal EnableExtensions
set "HERE=%~dp0"

rem Find the Python selected by PATH, then prefer its pythonw.exe sibling.
for %%I in (python.exe) do set "PY=%%~$PATH:I"
if not defined PY (
    echo LevelUpDiag UI: python.exe was not found in PATH.
    echo Install/enable Python, then run this launcher again.
    pause
    exit /b 1
)

for %%I in ("%PY%") do set "PYW=%%~dpIpythonw.exe"
if exist "%PYW%" (
    start "LevelUpDiag" "%PYW%" "%HERE%LevelUpDiag_UI.pyw"
    exit /b 0
)

rem Fallback: launch with python.exe. This may leave a console window open.
start "LevelUpDiag" "%PY%" "%HERE%LevelUpDiag_UI.pyw"
exit /b 0
