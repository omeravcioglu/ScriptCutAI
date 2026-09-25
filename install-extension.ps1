# ScriptCutAI - Premiere Pro Extension Installer
# Run this script as Administrator

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ScriptCutAI Extension Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Enable unsigned extensions (required for development)
Write-Host "[1/3] Enabling unsigned extensions..." -ForegroundColor Yellow

$regPath = "HKCU:\Software\Adobe\CSXS.11"
if (-not (Test-Path $regPath)) {
    New-Item -Path $regPath -Force | Out-Null
}
Set-ItemProperty -Path $regPath -Name "PlayerDebugMode" -Value 1 -Type String

# Also set for older versions
$versions = @("CSXS.10", "CSXS.9", "CSXS.8")
foreach ($ver in $versions) {
    $path = "HKCU:\Software\Adobe\$ver"
    if (-not (Test-Path $path)) {
        New-Item -Path $path -Force | Out-Null
    }
    Set-ItemProperty -Path $path -Name "PlayerDebugMode" -Value 1 -Type String
}

Write-Host "   Done!" -ForegroundColor Green

# Step 2: Copy extension to Adobe extensions folder
Write-Host "[2/3] Installing extension..." -ForegroundColor Yellow

$sourcePath = "$PSScriptRoot\premiere-extension"
$destPath = "$env:APPDATA\Adobe\CEP\extensions\com.scriptcutai.panel"

# Create destination folder if it doesn't exist
if (Test-Path $destPath) {
    Remove-Item -Path $destPath -Recurse -Force
}
New-Item -Path $destPath -ItemType Directory -Force | Out-Null

# Copy extension files
Copy-Item -Path "$sourcePath\*" -Destination $destPath -Recurse -Force

Write-Host "   Installed to: $destPath" -ForegroundColor Green

# Step 3: Verify installation
Write-Host "[3/3] Verifying installation..." -ForegroundColor Yellow

if (Test-Path "$destPath\CSXS\manifest.xml") {
    Write-Host "   Verification passed!" -ForegroundColor Green
} else {
    Write-Host "   Warning: manifest.xml not found" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Close Premiere Pro if it's open"
Write-Host "2. Start the Python backend server:"
Write-Host "   cd $PSScriptRoot\backend"
Write-Host "   .\venv\Scripts\Activate.ps1"
Write-Host "   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
Write-Host ""
Write-Host "3. Open Premiere Pro"
Write-Host "4. Go to: Window > Extensions > ScriptCutAI"
Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

