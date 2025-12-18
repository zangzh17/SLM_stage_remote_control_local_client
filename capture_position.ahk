#NoEnv
SendMode Input
SetWorkingDir %A_ScriptDir%

; 捕获屏幕全局坐标并保存到配置文件
CoordMode, Mouse, Screen
ToolTip, Click position to record...

KeyWait, LButton, D
MouseGetPos, PosX, PosY
ToolTip

; 保存到配置文件
configFile := A_ScriptDir . "\click_position.ini"
FileDelete, %configFile%
FileAppend, %PosX%`n%PosY%, %configFile%

; 可选：显示简短提示
MsgBox, 262144, Recorded, Window #1 recorded!

ExitApp
