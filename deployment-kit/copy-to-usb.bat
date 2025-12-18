@echo off
REM Copy deployment kit to USB drive
REM Run this AFTER flashing Ubuntu to the USB

echo.
echo ========================================
echo   COPY DEPLOYMENT FILES TO USB
echo ========================================
echo.

REM List available drives
echo Available drives:
wmic logicaldisk get caption,volumename,drivetype 2>nul | findstr "2 3"
echo.

set /p DRIVE="Enter USB drive letter (e.g., E): "

if not exist %DRIVE%:\ (
    echo ERROR: Drive %DRIVE%: not found
    pause
    exit /b 1
)

echo.
echo Copying deployment-kit to %DRIVE%:\deployment-kit ...

xcopy /E /I /Y "%~dp0" "%DRIVE%:\deployment-kit\"

echo.
echo ========================================
echo   DONE!
echo ========================================
echo.
echo Files copied to: %DRIVE%:\deployment-kit\
echo.
echo The USB is ready. Take it to the server machine and:
echo   1. Boot from USB
echo   2. Install Ubuntu (see DEPLOY.txt)
echo   3. SSH in and run the setup script
echo.
pause
