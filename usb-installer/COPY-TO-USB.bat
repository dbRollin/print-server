@echo off
REM ============================================
REM   PREPARE USB FOR AUTOMATED INSTALL
REM ============================================
REM
REM Run this AFTER flashing Ubuntu with Rufus.
REM Enables fully automated installation - just boot and walk away!
REM

echo.
echo ============================================
echo   PREPARE USB FOR AUTOMATED INSTALL
echo ============================================
echo.

REM Try to find the USB drive automatically
set "USB_DRIVE="
for %%d in (D E F G H I J K) do (
    if exist "%%d:\ubuntu" (
        set "USB_DRIVE=%%d:"
        goto :found
    )
)
for %%d in (D E F G H I J K) do (
    if exist "%%d:\boot\grub\grub.cfg" (
        set "USB_DRIVE=%%d:"
        goto :found
    )
)

REM If not found automatically, list drives and ask
echo Could not auto-detect the USB drive.
echo.
echo Available removable drives:
wmic logicaldisk where drivetype=2 get caption,volumename 2>nul
echo.
set /p USB_DRIVE="Enter USB drive letter (e.g., E:): "
goto :copy

:found
echo Found Ubuntu USB at %USB_DRIVE%
echo.

:copy
if not exist "%USB_DRIVE%\" (
    echo ERROR: Drive %USB_DRIVE% not found!
    pause
    exit /b 1
)

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"

echo [1/4] Copying autoinstall configuration...
copy "%SCRIPT_DIR%..\install\autoinstall.yaml" "%USB_DRIVE%\" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy autoinstall.yaml
    pause
    exit /b 1
)

echo [2/4] Enabling autoinstall in bootloader...
REM Create nocloud directory with user-data (the autoinstall config)
if not exist "%USB_DRIVE%\nocloud" mkdir "%USB_DRIVE%\nocloud"
copy "%SCRIPT_DIR%..\install\autoinstall.yaml" "%USB_DRIVE%\nocloud\user-data" >nul
copy "%SCRIPT_DIR%..\install\meta-data" "%USB_DRIVE%\nocloud\meta-data" >nul 2>&1
REM Create empty meta-data if it doesn't exist
if not exist "%USB_DRIVE%\nocloud\meta-data" echo instance-id: printserver > "%USB_DRIVE%\nocloud\meta-data"

REM Modify grub.cfg to add autoinstall parameter
if exist "%USB_DRIVE%\boot\grub\grub.cfg" (
    powershell -Command "$content = Get-Content '%USB_DRIVE%\boot\grub\grub.cfg' -Raw; $content = $content -replace '(linux\s+/casper/vmlinuz[^\n]*)', '$1 autoinstall ds=nocloud\\;s=/cdrom/nocloud/'; $content | Set-Content '%USB_DRIVE%\boot\grub\grub.cfg' -NoNewline"
    echo     - Modified grub.cfg for autoinstall
)

echo [3/4] Copying deployment kit...
if not exist "%USB_DRIVE%\deployment-kit" mkdir "%USB_DRIVE%\deployment-kit"
copy "%SCRIPT_DIR%..\deployment-kit\DEPLOY.txt" "%USB_DRIVE%\deployment-kit\" >nul 2>&1
copy "%SCRIPT_DIR%..\deployment-kit\setup.sh" "%USB_DRIVE%\deployment-kit\" >nul 2>&1
copy "%SCRIPT_DIR%..\deployment-kit\deploy-from-windows.ps1" "%USB_DRIVE%\deployment-kit\" >nul 2>&1

echo [4/4] Copying helper scripts...
copy "%SCRIPT_DIR%..\scripts\first-setup.sh" "%USB_DRIVE%\deployment-kit\" >nul 2>&1
copy "%SCRIPT_DIR%..\scripts\configure-wifi.sh" "%USB_DRIVE%\deployment-kit\" >nul 2>&1
copy "%SCRIPT_DIR%..\scripts\clear-wifi.sh" "%USB_DRIVE%\deployment-kit\" >nul 2>&1
copy "%SCRIPT_DIR%..\scripts\show-network.sh" "%USB_DRIVE%\deployment-kit\" >nul 2>&1
copy "%SCRIPT_DIR%..\scripts\health-check.sh" "%USB_DRIVE%\deployment-kit\" >nul 2>&1

echo.
echo ============================================
echo   USB READY FOR AUTOMATED INSTALL!
echo ============================================
echo.
echo Files copied to: %USB_DRIVE%
echo.
echo WHAT HAPPENS NEXT:
echo   1. Boot the Beelink from this USB
echo   2. Select "Install Ubuntu Server" (or just wait)
echo   3. WALK AWAY - installation is fully automated!
echo   4. The machine will reboot when done
echo.
echo AFTER INSTALL:
echo   Login:    admin / printserver
echo   Then run: ./bootstrap.sh
echo.
echo   Or from Windows, run DEPLOY-FROM-HERE.bat
echo.
pause
