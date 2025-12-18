#NoEnv
SendMode Input

; 使用方法: click_at.ahk X Y
; 例如: click_at.ahk 500 300

if (A_Args.Length() < 2)
{
    ExitApp, 1
}

PosX := A_Args[1]
PosY := A_Args[2]

CoordMode, Mouse, Screen
Click, %PosX%, %PosY%

ExitApp
