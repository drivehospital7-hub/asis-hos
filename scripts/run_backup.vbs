Set objShell = CreateObject("Wscript.Shell")

objShell.Run _
    "powershell.exe -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File ""D:\CODE\backup-asis-hos.ps1""", _
    0, _
    False