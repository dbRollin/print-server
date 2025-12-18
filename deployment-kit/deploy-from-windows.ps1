# Deploy Print Server from Windows
# Run this after Ubuntu is installed and you can SSH in

param(
    [string]$ServerIP = "printserver.local",
    [string]$Username = "print"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  PRINT SERVER DEPLOYMENT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get project root (parent of deployment-kit)
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "Project folder: $ProjectRoot"
Write-Host "Target server:  $Username@$ServerIP"
Write-Host ""

# Test SSH connectivity
Write-Host "[1/4] Testing SSH connection..." -ForegroundColor Yellow
try {
    ssh -o ConnectTimeout=5 -o BatchMode=yes "$Username@$ServerIP" "echo connected" 2>$null
    if ($LASTEXITCODE -ne 0) { throw "SSH failed" }
    Write-Host "  Connected!" -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "  Cannot connect to $ServerIP" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Make sure:" -ForegroundColor Yellow
    Write-Host "    - The server finished installing Ubuntu"
    Write-Host "    - It's on the same network as this computer"
    Write-Host "    - You can ping it: ping $ServerIP"
    Write-Host ""
    Write-Host "  If using IP address, run:"
    Write-Host "    .\deploy-from-windows.ps1 -ServerIP 192.168.x.x"
    Write-Host ""
    exit 1
}

# Run bootstrap
Write-Host ""
Write-Host "[2/4] Running bootstrap on server..." -ForegroundColor Yellow
Write-Host "  (This installs Docker, Portainer, Cockpit, CUPS)"
Write-Host "  This may take 5-10 minutes..."
Write-Host ""

$SetupScript = Get-Content "$PSScriptRoot\setup.sh" -Raw
ssh "$Username@$ServerIP" "bash -s" <<< $SetupScript

Write-Host ""
Write-Host "  Bootstrap complete!" -ForegroundColor Green

# Copy project files
Write-Host ""
Write-Host "[3/4] Copying print-server files to server..." -ForegroundColor Yellow
scp -r "$ProjectRoot" "${Username}@${ServerIP}:~/"
Write-Host "  Files copied!" -ForegroundColor Green

# Final instructions
Write-Host ""
Write-Host "[4/4] Almost done!" -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DEPLOYMENT COMPLETE!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Management UIs are ready:" -ForegroundColor Green
Write-Host "    Cockpit:   https://${ServerIP}:9090"
Write-Host "    Portainer: http://${ServerIP}:9000"
Write-Host ""
Write-Host "  NEXT: Start the print server container" -ForegroundColor Yellow
Write-Host ""
Write-Host "  SSH into the server:"
Write-Host "    ssh $Username@$ServerIP"
Write-Host ""
Write-Host "  Then run:"
Write-Host "    cd ~/print-server"
Write-Host "    docker compose -f docker/docker-compose.prod.yaml up -d"
Write-Host ""
Write-Host "  Test it:"
Write-Host "    curl http://localhost:5001/v1/health"
Write-Host ""
