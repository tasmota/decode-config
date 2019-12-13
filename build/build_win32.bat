@echo off
SET EXEC=decode-config.exe
pyinstaller.exe dc-build-win32.spec
IF ERRORLEVEL 0 (
	ECHO Copying dist\%EXEC% ..\%EXEC%
	COPY dist\%EXEC% ..\%EXEC%
)
