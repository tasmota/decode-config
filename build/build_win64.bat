@echo off
SET EXEC=decode-config_x64.exe
pyinstaller.exe dc-build-win64.spec
IF ERRORLEVEL 0 (
	ECHO Copying dist\%EXEC% ..\%EXEC%
	COPY dist\%EXEC% ..\%EXEC%
)
