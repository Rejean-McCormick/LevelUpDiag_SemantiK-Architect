Option Explicit

Dim shell, fso, here, ui, rc
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
here = fso.GetParentFolderName(WScript.ScriptFullName)
ui = fso.BuildPath(here, "LevelUpDiag_UI.pyw")

If Not fso.FileExists(ui) Then
    MsgBox "LevelUpDiag_UI.pyw was not found:" & vbCrLf & ui, vbCritical, "LevelUpDiag"
    WScript.Quit 1
End If

' Preferred: pythonw.exe never owns a console window.
On Error Resume Next
Err.Clear
rc = shell.Run("pythonw.exe """ & ui & """", 0, False)
If Err.Number = 0 Then
    WScript.Quit 0
End If

' Fallback: python.exe is started with hidden window style 0.
Err.Clear
rc = shell.Run("python.exe """ & ui & """", 0, False)
If Err.Number = 0 Then
    WScript.Quit 0
End If
On Error GoTo 0

MsgBox "Python could not be launched. Ensure python.exe or pythonw.exe is available in PATH.", vbCritical, "LevelUpDiag"
WScript.Quit 1
