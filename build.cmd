@echo off
rem Builds release\Gearbox Upgrades\plugins\GearboxUpgrades.dll with the Visual Studio Build Tools (x64, static CRT).
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul 2>nul || exit /b 1
cd /d "%~dp0"
set "OUT=%~dp0release\Gearbox Upgrades\plugins"
if not exist "%OUT%" mkdir "%OUT%"
if not exist build mkdir build
cl /nologo /std:c11 /O2 /MT /W4 /D_CRT_SECURE_NO_WARNINGS /Iinclude /LD src\gearbox_upgrades.c /Fobuild\ /Fe"%OUT%\GearboxUpgrades.dll" /link /NOLOGO || exit /b 1
del "%OUT%\GearboxUpgrades.exp" "%OUT%\GearboxUpgrades.lib" 2>nul
cl /nologo /std:c11 /O2 /MT /W3 /D_CRT_SECURE_NO_WARNINGS /Iinclude tests\run_on_copy.c /Fobuild\ /Febuild\run_on_copy.exe /link /NOLOGO || exit /b 1
echo Built
