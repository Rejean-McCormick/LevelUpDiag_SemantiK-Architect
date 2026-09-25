$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = (Get-Command python.exe -ErrorAction Stop).Source
$PythonW = Join-Path (Split-Path -Parent $Python) "pythonw.exe"
$Ui = Join-Path $Here "LevelUpDiag_UI.pyw"

if (Test-Path $PythonW) {
    Start-Process -FilePath $PythonW -ArgumentList @($Ui) -WorkingDirectory $Here
} else {
    Start-Process -FilePath $Python -ArgumentList @($Ui) -WorkingDirectory $Here
}
