#NoEnv
SendMode Input
SetWorkingDir %A_ScriptDir%

; 读取配置文件
configFile := A_ScriptDir . "\click_position.ini"

if !FileExist(configFile)
{
    ; 静默退出，错误码1
    ExitApp, 1
}

FileReadLine, PosX, %configFile%, 1
FileReadLine, PosY, %configFile%, 2

; 点击位置
CoordMode, Mouse, Screen
Click, %PosX%, %PosY%

ExitApp
