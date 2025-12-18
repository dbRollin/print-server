@echo off
REM ============================================
REM   PREPARE DEBIAN USB FOR AUTOMATED INSTALL
REM ============================================
REM
REM Run this AFTER flashing Debian with Rufus.
REM Enables fully automated installation - just boot and walk away!
REM

echo.
echo ============================================
echo   PREPARE DEBIAN USB FOR AUTOMATED INSTALL
echo ============================================
echo.

REM Try to find the USB drive automatically (look for Debian markers)
set "USB_DRIVE="
for %%d in (D E F G H I J K) do (
    if exist "%%d:\install.amd" (
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
for %%d in (D E F G H I J K) do (
    if exist "%%d:\isolinux" (
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
echo Found Debian USB at %USB_DRIVE%
echo.

:copy
if not exist "%USB_DRIVE%\" (
    echo ERROR: Drive %USB_DRIVE% not found!
    pause
    exit /b 1
)

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"

echo [1/4] Copying preseed configuration...
copy "%SCRIPT_DIR%..\install\preseed.cfg" "%USB_DRIVE%\" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy preseed.cfg
    pause
    exit /b 1
)

echo [2/4] Modifying boot configuration for automated install...

REM Preseed boot parameters - try multiple paths (cdrom for ISO mode, hd-media for USB)
set "PRESEED_PARAMS=auto=true priority=critical file=/cdrom/preseed.cfg"

REM Try UEFI boot (grub.cfg)
if exist "%USB_DRIVE%\boot\grub\grub.cfg" (
    echo     - Found GRUB config, enabling preseed...
    powershell -Command "$content = Get-Content '%USB_DRIVE%\boot\grub\grub.cfg' -Raw; $content = $content -replace '(menuentry[^{]+Install[^{]+{[^}]*linux\s+)([^\n]+)', '$1$2 auto=true priority=critical file=/cdrom/preseed.cfg'; $content | Set-Content '%USB_DRIVE%\boot\grub\grub.cfg' -NoNewline"
    echo     - Note: If auto-install fails, manually add boot params at GRUB menu
)

REM Try BIOS boot (isolinux - txt.cfg has the actual menu entries)
if exist "%USB_DRIVE%\isolinux\txt.cfg" (
    echo     - Found isolinux txt.cfg, enabling preseed...
    powershell -Command "$content = Get-Content '%USB_DRIVE%\isolinux\txt.cfg' -Raw; $content = $content -replace '(label install\s+menu label \^Install\s+kernel [^\s]+\s+append )([^\n]+)', '$1$2 auto=true priority=critical file=/cdrom/preseed.cfg'; $content | Set-Content '%USB_DRIVE%\isolinux\txt.cfg' -NoNewline"
)

echo [3/4] Copying deployment kit...
if not exist "%USB_DRIVE%\deployment-kit" mkdir "%USB_DRIVE%\deployment-kit"
copy "%SCRIPT_DIR%..\deployment-kit\DEPLOY.txt" "%USB_DRIVE%\deployment-kit\" >nul 2>&1
copy "%SCRIPT_DIR%..\deployment-kit\setup.sh" "%USB_DRIVE%\deployment-kit\" >nul 2>&1
copy "%SCRIPT_DIR%..\deployment-kit\deploy-from-windows.ps1" "%USB_DRIVE%\deployment-kit\" >nul 2>&1

echo [4/4] Copying helper scripts...
copy "%SCRIPT_DIR%..\scripts\first-setup.sh" "%USB_DRIVE%\deployment-kit\" >nul 2>&1
copy "%SCRIPT_DIR%..\scripts\bootstrap.sh" "%USB_DRIVE%\deployment-kit\" >nul 2>&1
copy "%SCRIPT_DIR%..\scripts\configure-wifi.sh" "%USB_DRIVE%\deployment-kit\" >nul 2>&1
copy "%SCRIPT_DIR%..\scripts\show-network.sh" "%USB_DRIVE%\deployment-kit\" >nul 2>&1
copy "%SCRIPT_DIR%..\scripts\health-check.sh" "%USB_DRIVE%\deployment-kit\" >nul 2>&1

echo.
echo ============================================
echo   USB READY - READ THE INSTRUCTIONS BELOW
echo ============================================
echo.
echo Files copied to: %USB_DRIVE%
echo.
echo -------------------------------------------
echo   OPTION 1: TRY AUTOMATIC (might work)
echo -------------------------------------------
echo   1. Boot server from USB
echo   2. At boot menu, just press Enter or wait
echo   3. If it starts asking questions, use Option 2
echo.
echo -------------------------------------------
echo   OPTION 2: MANUAL BOOT PARAMS (reliable)
echo -------------------------------------------
echo   1. Boot server from USB
echo   2. At the Debian boot menu, press TAB (BIOS) or E (UEFI)
echo   3. Find the line starting with 'linux' and ADD to the end:
echo.
echo      auto=true priority=critical file=/cdrom/preseed.cfg
echo.
echo   4. Press Enter (BIOS) or Ctrl+X (UEFI) to boot
echo   5. Installation should run unattended
echo.
echo -------------------------------------------
echo   AFTER INSTALL
echo -------------------------------------------
echo   Login:    admin / printserver
echo   Then run: sudo bash bootstrap.sh
echo.
echo TIP: Take a photo of this screen for the boot params!
echo.
pause
