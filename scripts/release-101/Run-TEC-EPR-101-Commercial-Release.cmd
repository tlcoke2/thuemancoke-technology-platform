@echo off
setlocal
cd /d "%~dp0"
node "%~dp0rc5-101-commercial-release.cjs" --mode release --confirm-owner-release %*
set "rc=%ERRORLEVEL%"
echo.
if not "%rc%"=="0" echo RELEASE HELD. Review the printed reason. Do not enable public downloads.
exit /b %rc%