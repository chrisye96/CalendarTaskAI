' CalendarTaskAI 启动脚本
' 双击此文件即可后台启动程序，不会弹出任何窗口

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' 设置工作目录为脚本所在目录
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = scriptDir

' 使用系统 PATH 中的 pythonw 后台运行
WshShell.Run "pythonw main.py", 0, False

Set fso = Nothing
Set WshShell = Nothing
