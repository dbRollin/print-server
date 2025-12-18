@echo off
REM ============================================
REM   DEPLOY PRINT SERVER (from this Windows PC)
REM ============================================
REM
REM Run this after Ubuntu is installed on the server.
REM This will SSH in and set everything up.
REM

echo.
echo ============================================
echo   PRINT SERVER DEPLOYMENT
echo ============================================
echo.
echo This script will:
echo   1. Connect to the server via SSH
echo   2. Install Docker, Portainer, Cockpit, CUPS
echo   3. Copy all the print-server files over
echo.
echo Make sure the server has finished installing Ubuntu
echo and is connected to the same network as this PC.
echo.

set "SERVER=printserver.local"
set "USER=print"

echo Trying to reach %SERVER%...
ping -n 1 %SERVER% >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo Could not reach %SERVER%
    echo.
    set /p SERVER="Enter server IP address: "
)

echo.
echo Will connect to: %USER%@%SERVER%
echo.
echo You will be prompted for the password you set during Ubuntu install.
echo.
pause

REM Change to the print-server project directory
cd /d "%~dp0.."

echo.
echo ============================================
echo   STEP 1: Running bootstrap on server
echo ============================================
echo.
echo This installs Docker, Portainer, Cockpit, and CUPS.
echo It may take 5-10 minutes. Watch for prompts.
echo.

ssh %USER%@%SERVER% "curl -fsSL https://raw.githubusercontent.com/daveb/print-server/main/scripts/bootstrap.sh | bash || bash -s" < "%~dp0..\deployment-kit\setup.sh"

echo.
echo ============================================
echo   STEP 2: Copying print-server files
echo ============================================
echo.

scp -r "%~dp0.." %USER%@%SERVER%:~/print-server

echo.
echo ============================================
echo   DEPLOYMENT COMPLETE!
echo ============================================
echo.
echo Management UIs are ready at:
echo   Cockpit:   https://%SERVER%:9090
echo   Portainer: http://%SERVER%:9000
echo.
echo FINAL STEP - SSH in and start the container:
echo.
echo   ssh %USER%@%SERVER%
echo   cd ~/print-server
echo   docker compose -f docker/docker-compose.prod.yaml up -d
echo.
echo Or just run this:
echo   ssh %USER%@%SERVER% "cd ~/print-server && docker compose -f docker/docker-compose.prod.yaml up -d"
echo.
pause
