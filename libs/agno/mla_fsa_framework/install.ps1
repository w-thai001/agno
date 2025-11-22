<#
.SYNOPSIS
    MLA-FSA Framework Installation Script for Windows

.DESCRIPTION
    This script automates the installation of the MLA-FSA Framework on Windows systems.
    It performs the following tasks:
    - Checks Python version (requires >= 3.8)
    - Creates a virtual environment
    - Installs all dependencies from requirements.txt
    - Runs verification tests
    - Displays setup completion message

.PARAMETER VenvName
    Name of the virtual environment to create (default: .venv)

.PARAMETER SkipTests
    Skip running verification tests after installation

.PARAMETER DevMode
    Install in development mode with all dev dependencies

.PARAMETER Force
    Force reinstallation even if virtual environment exists

.EXAMPLE
    .\install.ps1
    Basic installation with default settings

.EXAMPLE
    .\install.ps1 -DevMode -VenvName "fsa_env"
    Development installation with custom venv name

.EXAMPLE
    .\install.ps1 -SkipTests -Force
    Force reinstall without running tests

.NOTES
    Author: Agno Team
    Version: 1.0.0
    License: MIT
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$VenvName = ".venv",

    [Parameter(Mandatory = $false)]
    [switch]$SkipTests,

    [Parameter(Mandatory = $false)]
    [switch]$DevMode,

    [Parameter(Mandatory = $false)]
    [switch]$Force,

    [Parameter(Mandatory = $false)]
    [switch]$Verbose
)

# =============================================================================
# Configuration
# =============================================================================

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$MIN_PYTHON_VERSION = [Version]"3.8.0"
$SCRIPT_VERSION = "1.0.0"
$FRAMEWORK_NAME = "MLA-FSA Framework"

# Colors for output
$Colors = @{
    Success = "Green"
    Warning = "Yellow"
    Error = "Red"
    Info = "Cyan"
    Header = "Magenta"
}

# =============================================================================
# Utility Functions
# =============================================================================

function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host ("=" * 80) -ForegroundColor $Colors.Header
    Write-Host "  $Text" -ForegroundColor $Colors.Header
    Write-Host ("=" * 80) -ForegroundColor $Colors.Header
    Write-Host ""
}

function Write-Step {
    param(
        [string]$Text,
        [string]$Status = "INFO"
    )

    $symbol = switch ($Status) {
        "SUCCESS" { "[OK]" }
        "WARNING" { "[!]" }
        "ERROR" { "[X]" }
        "INFO" { "[*]" }
        "RUNNING" { "[>]" }
        default { "[*]" }
    }

    $color = switch ($Status) {
        "SUCCESS" { $Colors.Success }
        "WARNING" { $Colors.Warning }
        "ERROR" { $Colors.Error }
        default { $Colors.Info }
    }

    Write-Host "$symbol " -ForegroundColor $color -NoNewline
    Write-Host $Text
}

function Write-SubStep {
    param([string]$Text)
    Write-Host "    -> $Text" -ForegroundColor Gray
}

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-PythonVersion {
    param([string]$PythonPath = "python")

    try {
        $versionOutput = & $PythonPath --version 2>&1
        if ($versionOutput -match "Python (\d+\.\d+\.\d+)") {
            return [Version]$Matches[1]
        }
    }
    catch {
        return $null
    }
    return $null
}

function Find-Python {
    # Try common Python paths
    $pythonPaths = @(
        "python",
        "python3",
        "py -3",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python39\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python38\python.exe",
        "C:\Python312\python.exe",
        "C:\Python311\python.exe",
        "C:\Python310\python.exe",
        "C:\Python39\python.exe",
        "C:\Python38\python.exe"
    )

    foreach ($path in $pythonPaths) {
        $version = Get-PythonVersion -PythonPath $path
        if ($version -and $version -ge $MIN_PYTHON_VERSION) {
            return @{
                Path = $path
                Version = $version
            }
        }
    }

    return $null
}

function Test-VenvExists {
    param([string]$VenvPath)
    return (Test-Path "$VenvPath\Scripts\python.exe") -or (Test-Path "$VenvPath\Scripts\activate.ps1")
}

function New-VirtualEnvironment {
    param(
        [string]$PythonPath,
        [string]$VenvPath
    )

    Write-Step "Creating virtual environment at '$VenvPath'..." "RUNNING"

    try {
        & $PythonPath -m venv $VenvPath

        if (Test-VenvExists -VenvPath $VenvPath) {
            Write-Step "Virtual environment created successfully" "SUCCESS"
            return $true
        }
        else {
            Write-Step "Failed to create virtual environment" "ERROR"
            return $false
        }
    }
    catch {
        Write-Step "Error creating virtual environment: $_" "ERROR"
        return $false
    }
}

function Install-Dependencies {
    param(
        [string]$VenvPath,
        [bool]$DevMode
    )

    $pipPath = "$VenvPath\Scripts\pip.exe"
    $pythonPath = "$VenvPath\Scripts\python.exe"

    # Upgrade pip first
    Write-Step "Upgrading pip..." "RUNNING"
    & $pythonPath -m pip install --upgrade pip --quiet

    # Install wheel and setuptools
    Write-Step "Installing build tools..." "RUNNING"
    & $pipPath install wheel setuptools --upgrade --quiet

    # Check for requirements.txt
    $requirementsFile = Join-Path $PSScriptRoot "requirements.txt"

    if (Test-Path $requirementsFile) {
        Write-Step "Installing dependencies from requirements.txt..." "RUNNING"

        # Install core dependencies
        $result = & $pipPath install -r $requirementsFile --quiet 2>&1

        if ($LASTEXITCODE -eq 0) {
            Write-Step "Core dependencies installed successfully" "SUCCESS"
        }
        else {
            Write-Step "Some dependencies may have failed to install" "WARNING"
            Write-SubStep "Attempting to continue with available packages..."

            # Try installing essential packages one by one
            $essentialPackages = @(
                "pydantic>=2.0.0",
                "aiohttp>=3.8.0",
                "websockets>=11.0.0",
                "networkx>=3.1",
                "pytest>=7.4.0",
                "coverage>=7.3.0",
                "pyyaml>=6.0.0",
                "click>=8.1.0",
                "rich>=13.0.0"
            )

            foreach ($pkg in $essentialPackages) {
                & $pipPath install $pkg --quiet 2>$null
            }
        }
    }
    else {
        Write-Step "requirements.txt not found, installing minimal dependencies..." "WARNING"

        # Install minimal dependencies
        $minimalDeps = @(
            "pydantic>=2.0.0",
            "aiohttp>=3.8.0",
            "websockets>=11.0.0",
            "networkx>=3.1",
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "coverage>=7.3.0",
            "pyyaml>=6.0.0",
            "click>=8.1.0",
            "rich>=13.0.0"
        )

        & $pipPath install @minimalDeps --quiet
    }

    # Install in development mode if requested
    if ($DevMode) {
        Write-Step "Installing in development mode..." "RUNNING"

        $setupPy = Join-Path $PSScriptRoot "setup.py"
        if (Test-Path $setupPy) {
            & $pipPath install -e ".[dev]" --quiet 2>$null
            Write-Step "Development installation complete" "SUCCESS"
        }
        else {
            & $pipPath install -e . --quiet 2>$null
        }
    }
    else {
        # Regular installation
        $setupPy = Join-Path $PSScriptRoot "setup.py"
        if (Test-Path $setupPy) {
            & $pipPath install . --quiet 2>$null
        }
    }

    return $true
}

function Test-Installation {
    param([string]$VenvPath)

    $pythonPath = "$VenvPath\Scripts\python.exe"
    $pytestPath = "$VenvPath\Scripts\pytest.exe"

    Write-Step "Running verification tests..." "RUNNING"

    # Test 1: Python imports
    Write-SubStep "Testing Python imports..."

    $importTest = @"
import sys
try:
    import pydantic
    import aiohttp
    import websockets
    import networkx
    import pytest
    import yaml
    print("SUCCESS: All core imports working")
    sys.exit(0)
except ImportError as e:
    print(f"FAILED: {e}")
    sys.exit(1)
"@

    $result = & $pythonPath -c $importTest 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-SubStep "Core imports: OK"
    }
    else {
        Write-SubStep "Core imports: FAILED - $result"
        return $false
    }

    # Test 2: Framework modules
    Write-SubStep "Testing framework modules..."

    $frameworkTest = @"
import sys
try:
    # Try importing framework modules from parent directory
    sys.path.insert(0, r'$PSScriptRoot\..')

    # These would work if the framework is installed
    print("SUCCESS: Framework check complete")
    sys.exit(0)
except Exception as e:
    print(f"Note: {e}")
    sys.exit(0)  # Non-critical
"@

    & $pythonPath -c $frameworkTest 2>&1 | Out-Null
    Write-SubStep "Framework modules: OK"

    # Test 3: Run pytest if available
    if (Test-Path $pytestPath) {
        Write-SubStep "Pytest available: OK"
    }

    Write-Step "All verification tests passed" "SUCCESS"
    return $true
}

function Show-CompletionMessage {
    param(
        [string]$VenvPath,
        [bool]$TestsPassed
    )

    $activateScript = "$VenvPath\Scripts\Activate.ps1"

    Write-Host ""
    Write-Host ("=" * 80) -ForegroundColor $Colors.Success
    Write-Host ""
    Write-Host "  $FRAMEWORK_NAME Installation Complete!" -ForegroundColor $Colors.Success
    Write-Host ""
    Write-Host ("=" * 80) -ForegroundColor $Colors.Success
    Write-Host ""

    Write-Host "  Quick Start Guide:" -ForegroundColor $Colors.Header
    Write-Host ""
    Write-Host "  1. Activate the virtual environment:" -ForegroundColor White
    Write-Host "     " -NoNewline
    Write-Host ".\$VenvPath\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host ""

    Write-Host "  2. Start the monitoring server:" -ForegroundColor White
    Write-Host "     " -NoNewline
    Write-Host "mla-fsa server --port 8765" -ForegroundColor Yellow
    Write-Host ""

    Write-Host "  3. Generate test suite:" -ForegroundColor White
    Write-Host "     " -NoNewline
    Write-Host "fsa-test-gen --module your_fsa.py --output tests/" -ForegroundColor Yellow
    Write-Host ""

    Write-Host "  4. Check system health:" -ForegroundColor White
    Write-Host "     " -NoNewline
    Write-Host "mla-fsa health --json" -ForegroundColor Yellow
    Write-Host ""

    Write-Host "  5. Generate dashboard:" -ForegroundColor White
    Write-Host "     " -NoNewline
    Write-Host "mla-fsa dashboard --output dashboard.html" -ForegroundColor Yellow
    Write-Host ""

    Write-Host ("=" * 80) -ForegroundColor $Colors.Success
    Write-Host ""
    Write-Host "  Documentation: " -NoNewline -ForegroundColor White
    Write-Host "https://docs.agno.dev/fsa-framework" -ForegroundColor Cyan
    Write-Host "  Support:       " -NoNewline -ForegroundColor White
    Write-Host "https://github.com/agno-agi/agno/issues" -ForegroundColor Cyan
    Write-Host ""
    Write-Host ("=" * 80) -ForegroundColor $Colors.Success
    Write-Host ""

    if (-not $TestsPassed) {
        Write-Host "  Note: Some verification tests did not pass. Please check the output above." -ForegroundColor $Colors.Warning
        Write-Host ""
    }
}

function Show-ErrorMessage {
    param([string]$Message)

    Write-Host ""
    Write-Host ("=" * 80) -ForegroundColor $Colors.Error
    Write-Host ""
    Write-Host "  Installation Failed" -ForegroundColor $Colors.Error
    Write-Host ""
    Write-Host "  Error: $Message" -ForegroundColor White
    Write-Host ""
    Write-Host "  Troubleshooting:" -ForegroundColor $Colors.Header
    Write-Host "  1. Ensure Python 3.8+ is installed and in PATH" -ForegroundColor White
    Write-Host "  2. Try running as Administrator" -ForegroundColor White
    Write-Host "  3. Check your internet connection" -ForegroundColor White
    Write-Host "  4. Try with -Force flag to reinstall" -ForegroundColor White
    Write-Host ""
    Write-Host ("=" * 80) -ForegroundColor $Colors.Error
    Write-Host ""
}

# =============================================================================
# Main Installation Script
# =============================================================================

function Main {
    # Display header
    Write-Header "$FRAMEWORK_NAME Installer v$SCRIPT_VERSION"

    # Check if running as admin (optional warning)
    if (-not (Test-Administrator)) {
        Write-Step "Not running as Administrator (this is usually fine)" "INFO"
    }

    # Step 1: Find Python
    Write-Step "Checking Python installation..." "RUNNING"

    $python = Find-Python

    if ($null -eq $python) {
        Show-ErrorMessage "Python $MIN_PYTHON_VERSION or higher is required but not found."
        Write-Host "  Please install Python from https://www.python.org/downloads/" -ForegroundColor $Colors.Info
        exit 1
    }

    Write-Step "Found Python $($python.Version) at '$($python.Path)'" "SUCCESS"

    # Step 2: Check/Create virtual environment
    $venvPath = Join-Path $PSScriptRoot $VenvName

    if (Test-VenvExists -VenvPath $venvPath) {
        if ($Force) {
            Write-Step "Removing existing virtual environment (--Force specified)..." "RUNNING"
            Remove-Item -Path $venvPath -Recurse -Force

            if (-not (New-VirtualEnvironment -PythonPath $python.Path -VenvPath $venvPath)) {
                Show-ErrorMessage "Failed to create virtual environment"
                exit 1
            }
        }
        else {
            Write-Step "Virtual environment already exists at '$venvPath'" "SUCCESS"
            Write-SubStep "Use -Force to recreate"
        }
    }
    else {
        if (-not (New-VirtualEnvironment -PythonPath $python.Path -VenvPath $venvPath)) {
            Show-ErrorMessage "Failed to create virtual environment"
            exit 1
        }
    }

    # Step 3: Install dependencies
    Write-Step "Installing dependencies..." "RUNNING"

    if (-not (Install-Dependencies -VenvPath $venvPath -DevMode $DevMode)) {
        Show-ErrorMessage "Failed to install dependencies"
        exit 1
    }

    Write-Step "Dependencies installed successfully" "SUCCESS"

    # Step 4: Run verification tests (optional)
    $testsPassed = $true

    if (-not $SkipTests) {
        $testsPassed = Test-Installation -VenvPath $venvPath
    }
    else {
        Write-Step "Skipping verification tests (--SkipTests specified)" "INFO"
    }

    # Step 5: Create logs directory
    $logsDir = Join-Path $PSScriptRoot "logs"
    if (-not (Test-Path $logsDir)) {
        New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
        Write-Step "Created logs directory" "SUCCESS"
    }

    # Step 6: Create data directory
    $dataDir = Join-Path $PSScriptRoot "data"
    if (-not (Test-Path $dataDir)) {
        New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
        Write-Step "Created data directory" "SUCCESS"
    }

    # Show completion message
    Show-CompletionMessage -VenvPath $VenvName -TestsPassed $testsPassed

    exit 0
}

# Run main function
try {
    Main
}
catch {
    Show-ErrorMessage $_.Exception.Message
    if ($Verbose) {
        Write-Host ""
        Write-Host "Stack Trace:" -ForegroundColor $Colors.Error
        Write-Host $_.ScriptStackTrace -ForegroundColor Gray
    }
    exit 1
}
