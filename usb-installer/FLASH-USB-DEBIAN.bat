@echo off
REM ============================================
REM   PRINT SERVER USB CREATOR - DEBIAN
REM ============================================
REM
REM This launches Rufus with the Debian DVD ISO.
REM Offline install - no network needed!
REM Configure WiFi after install is complete.
REM

echo.
echo ============================================
echo   PRINT SERVER USB CREATOR - DEBIAN
echo ============================================
echo.
echo This will open Rufus to flash Debian to your USB drive.
echo.
echo BEFORE YOU CONTINUE:
echo   1. Insert your USB drive (8GB or larger)
echo   2. Close any File Explorer windows showing the USB
echo.
echo WARNING: This will ERASE everything on the USB drive!
echo.
pause

cd /d "%~dp0"

REM Check for Debian ISO
set "ISO_FILE="
for %%f in (debian-*.iso) do (
    set "ISO_FILE=%%f"
)

if "%ISO_FILE%"=="" (
    echo.
    echo ERROR: No Debian ISO found!
    echo.
    echo Download Debian 13 netinst from:
    echo   https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/
    echo.
    echo Save it to this folder as: debian-13.x.x-amd64-netinst.iso
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
echo   3. Partition scheme: GPT (for UEFI) or MBR (for legacy BIOS)
echo   4. Click START
echo   5. Choose "Write in ISO Image mode" if prompted
echo.
echo After flashing completes, keep the USB plugged in
echo and run COPY-TO-USB-DEBIAN.bat to add the preseed file.
echo.

start "" rufus.exe -i "%~dp0%ISO_FILE%"
