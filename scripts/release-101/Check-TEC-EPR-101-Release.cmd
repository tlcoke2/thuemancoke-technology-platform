@echo off
setlocal
cd /d "%~dp0"
node "%~dp0rc5-101-commercial-release.cjs" --mode plan
exit /b %ERRORLEVEL%