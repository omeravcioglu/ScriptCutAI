# ScriptCutAI - Automatic Setup Script
# This script will install everything needed, including Python if missing

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "      ScriptCutAI - Auto Setup" -ForegroundColor Cyan  
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This tool requires Python to run." -ForegroundColor Yellow
Write-Host "The script will check and install everything needed." -ForegroundColor Yellow
Write-Host ""

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# ============================================
# STEP 1: Check/Install Python
# ============================================
Write-Host "[1/5] Checking for Python..." -ForegroundColor Cyan

$pythonInstalled = $false
$pythonPath = ""

# Check if python is in PATH
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python 3") {
        $pythonInstalled = $true
        $pythonPath = (Get-Command python).Source
        Write-Host "  Found: $pythonVersion" -ForegroundColor Green
    }
} catch {
    $pythonInstalled = $false
}

# Check common installation paths
if (-not $pythonInstalled) {
    $commonPaths = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "C:\Python312\python.exe",
        "C:\Python311\python.exe"
    )
    
    foreach ($path in $commonPaths) {
        if (Test-Path $path) {
            $pythonPath = $path
            $pythonInstalled = $true
            Write-Host "  Found Python at: $path" -ForegroundColor Green
            break
        }
    }
}

# If Python not found, download and install it
if (-not $pythonInstalled) {
    Write-Host "  Python not found. Downloading Python 3.12..." -ForegroundColor Yellow
    
    $pythonUrl = "https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe"
    $installerPath = "$env:TEMP\python-installer.exe"
    
    try {
        # Download Python installer
        Write-Host "  Downloading from python.org (this may take a minute)..." -ForegroundColor Yellow
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $pythonUrl -OutFile $installerPath -UseBasicParsing
        
        Write-Host "  Installing Python (this may take a few minutes)..." -ForegroundColor Yellow
        Write-Host "  Please wait and DO NOT close this window..." -ForegroundColor Red
        
        # Install Python silently with PATH option
        $installArgs = "/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_test=0"
        Start-Process -FilePath $installerPath -ArgumentList $installArgs -Wait -NoNewWindow
        
        # Refresh environment variables
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        
        # Find the newly installed Python
        $newPythonPath = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
        if (Test-Path $newPythonPath) {
            $pythonPath = $newPythonPath
            $pythonInstalled = $true
            Write-Host "  Python 3.12 installed successfully!" -ForegroundColor Green
        } else {
            # Try to find it
            $pythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
            if ($pythonPath) {
                $pythonInstalled = $true
                Write-Host "  Python installed successfully!" -ForegroundColor Green
            }
        }
        
        # Clean up installer
        Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
        
    } catch {
        Write-Host "  ERROR: Failed to download/install Python" -ForegroundColor Red
        Write-Host "  Please install Python manually from: https://www.python.org/downloads/" -ForegroundColor Yellow
        Write-Host "  Make sure to check 'Add Python to PATH' during installation" -ForegroundColor Yellow
        Write-Host ""
        Read-Host "Press Enter to exit"
        exit 1
    }
}

if (-not $pythonInstalled) {
    Write-Host "  ERROR: Python installation failed" -ForegroundColor Red
    Write-Host "  Please install Python 3.12 manually from python.org" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Determine python command to use
if ($pythonPath -and (Test-Path $pythonPath)) {
    $pythonCmd = $pythonPath
} else {
    $pythonCmd = "python"
}

# ============================================
# STEP 2: Check/Install FFmpeg  
# ============================================
Write-Host "[2/5] Checking for FFmpeg..." -ForegroundColor Cyan

$ffmpegInstalled = $false
try {
    $ffmpegVersion = ffmpeg -version 2>&1
    if ($ffmpegVersion -match "ffmpeg version") {
        $ffmpegInstalled = $true
        Write-Host "  FFmpeg is installed" -ForegroundColor Green
    }
} catch {
    $ffmpegInstalled = $false
}

if (-not $ffmpegInstalled) {
    Write-Host "  FFmpeg not found. Installing via winget..." -ForegroundColor Yellow
    
    try {
        winget install Gyan.FFmpeg --accept-package-agreements --accept-source-agreements --silent
        
        # Add to current session PATH
        $ffmpegPath = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-*\bin"
        $actualPath = Get-ChildItem $ffmpegPath -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($actualPath) {
            $env:Path = "$($actualPath.FullName);$env:Path"
        }
        
        Write-Host "  FFmpeg installed!" -ForegroundColor Green
    } catch {
        Write-Host "  Warning: Could not install FFmpeg automatically" -ForegroundColor Yellow
        Write-Host "  You may need to install it manually: winget install Gyan.FFmpeg" -ForegroundColor Yellow
    }
}

# ============================================
# STEP 3: Setup Python Virtual Environment
# ============================================
Write-Host "[3/5] Setting up Python environment..." -ForegroundColor Cyan

$backendPath = Join-Path $scriptRoot "backend"
$venvPath = Join-Path $backendPath "venv"
$requirementsPath = Join-Path $backendPath "requirements.txt"

# Create venv if it doesn't exist
if (-not (Test-Path "$venvPath\Scripts\python.exe")) {
    Write-Host "  Creating virtual environment..." -ForegroundColor Yellow
    Push-Location $backendPath
    & $pythonCmd -m venv venv
    Pop-Location
}

$venvPython = Join-Path $venvPath "Scripts\python.exe"
$venvPip = Join-Path $venvPath "Scripts\pip.exe"

# Install dependencies
Write-Host "  Installing dependencies (this may take several minutes)..." -ForegroundColor Yellow
Write-Host "  Please wait..." -ForegroundColor Yellow

Push-Location $backendPath
& $venvPip install --upgrade pip --quiet 2>$null
& $venvPip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    Write-Host "  Dependency installation FAILED - see the errors above." -ForegroundColor Red
    exit 1
}
Pop-Location

Write-Host "  Dependencies installed!" -ForegroundColor Green

# ============================================
# STEP 4: Install Premiere Extension
# ============================================
Write-Host "[4/5] Installing Premiere Pro extension..." -ForegroundColor Cyan

# Enable unsigned extensions for various CEP versions
$cepVersions = @("CSXS.11", "CSXS.10", "CSXS.9", "CSXS.8", "CSXS.7")
foreach ($ver in $cepVersions) {
    $regPath = "HKCU:\Software\Adobe\$ver"
    if (-not (Test-Path $regPath)) {
        New-Item -Path $regPath -Force | Out-Null
    }
    Set-ItemProperty -Path $regPath -Name "PlayerDebugMode" -Value "1" -Type String -Force
}

# Copy extension files
$extSource = Join-Path $scriptRoot "premiere-extension"
$extDest = "$env:APPDATA\Adobe\CEP\extensions\com.scriptcutai.panel"

if (Test-Path $extDest) {
    Remove-Item -Path $extDest -Recurse -Force
}
New-Item -Path $extDest -ItemType Directory -Force | Out-Null
Copy-Item -Path "$extSource\*" -Destination $extDest -Recurse -Force

Write-Host "  Extension installed!" -ForegroundColor Green

# ============================================
# STEP 5: Download AI Model
# ============================================
Write-Host "[5/5] Downloading AI model (first time only)..." -ForegroundColor Cyan
Write-Host "  This downloads ~150MB and may take a few minutes..." -ForegroundColor Yellow

Push-Location $backendPath
& $venvPython -c "import whisper; print('  Loading model...'); whisper.load_model('base'); print('  Model ready!')"
Pop-Location

# ============================================
# DONE!
# ============================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "      Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "HOW TO USE:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Double-click 'start-server.bat'" -ForegroundColor White
Write-Host "   (Keep this window open while editing)" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Open Adobe Premiere Pro" -ForegroundColor White
Write-Host ""
Write-Host "3. Go to: Window > Extensions > ScriptCutAI" -ForegroundColor White
Write-Host ""
Write-Host "4. Select video, paste script, click Analyze!" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to close"
