@echo off
REM ============================================
REM   PRINT SERVER USB CREATOR
REM ============================================
REM
REM This launches Rufus with the Ubuntu ISO.
REM Just select your USB drive and click Start.
REM

echo.
echo ============================================
echo   PRINT SERVER USB CREATOR
echo ============================================
echo.
echo This will open Rufus to flash Ubuntu to your USB drive.
echo.
echo BEFORE YOU CONTINUE:
echo   1. Insert your USB drive (8GB or larger)
echo   2. Close any File Explorer windows showing the USB
echo.
echo WARNING: This will ERASE everything on the USB drive!
echo.
pause

cd /d "%~dp0"

REM Check for 24.04.2 first (bug fix version), fall back to 24.04.1
set "ISO_FILE="
if exist "ubuntu-server-24.04.2.iso" (
    set "ISO_FILE=ubuntu-server-24.04.2.iso"
) else if exist "ubuntu-server-24.04.iso" (
    set "ISO_FILE=ubuntu-server-24.04.iso"
)

if "%ISO_FILE%"=="" (
    echo.
    echo ERROR: No Ubuntu ISO found!
    echo Looking for: ubuntu-server-24.04.2.iso or ubuntu-server-24.04.iso
    echo Check the usb-installer folder and try again.
    echo.
    pause
    exit /b 1
)

echo Using ISO: %ISO_FILE%

if not exist "rufus.exe" (
    echo.
    echo ERROR: rufus.exe not found!
    echo.
    pause
    exit /b 1
)

echo.
echo Launching Rufus...
echo.
echo IN RUFUS:
echo   1. Select your USB drive at the top
echo   2. The ISO should already be selected
echo   3. Leave other settings as default
echo   4. Click START
echo   5. Accept any prompts
echo.
echo After flashing completes, keep the USB plugged in
echo and run COPY-TO-USB.bat to add the deployment files.
echo.

start "" rufus.exe -i "%~dp0%ISO_FILE%"
