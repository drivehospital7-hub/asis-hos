Option Explicit

Dim shell, fso
Dim scriptDir, psScript, psExe, cmd

Set shell = CreateObject("WScript.Shell")
Set fso   = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

psScript = fso.BuildPath(scriptDir, "backup_db.ps1")
psExe    = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"

cmd = """" & psExe & _
      """ -NoProfile -ExecutionPolicy Bypass -File """ & _
      psScript & """"

shell.Run cmd, 0, True

Set shell = Nothing
Set fso = Nothing