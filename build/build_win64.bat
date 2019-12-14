@echo off
set SCRIPTDIR=%~dp0
set SCRIPTDIR=%SCRIPTDIR:~0,-1%
pushd %SCRIPTDIR%

set EXEC=decode-config_x64.exe
pyinstaller.exe dc-build-win64.spec
if errorlevel 0 (
	echo Copying dist\%EXEC% ..\%EXEC%...
	copy dist\%EXEC% ..\%EXEC%
    echo Well done
) else (
	echo Error occurred
)
popd
