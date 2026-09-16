[CmdletBinding()]
param(
    [string]$PythonExecutable = "",
    [switch]$SkipVerification
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RootDir = $PSScriptRoot
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"
$VenvDir = Join-Path $RootDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$RequirementsFile = Join-Path $RootDir "backend\requirements.txt"
$PipCacheDir = Join-Path $RootDir ".pip-cache"
$NpmCacheDir = Join-Path $RootDir ".npm-cache"
$ExpectedPythonVersion = (Get-Content (Join-Path $RootDir ".python-version") -Raw).Trim()
$ExpectedNodeVersion = (Get-Content (Join-Path $RootDir ".node-version") -Raw).Trim()
$ExpectedNpmVersion = "11.13.0"

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Invoke-Checked {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
    }
}

function Get-CommandVersion {
    param(
        [string]$FilePath,
        [string[]]$Arguments = @("--version")
    )

    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $output = & $FilePath @Arguments 2>&1
        $exitCode = $LASTEXITCODE
    }
    catch {
        return $null
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    if ($exitCode -ne 0 -or -not $output) {
        return $null
    }
    return (($output | Select-Object -Last 1).ToString().Trim() -replace '^v', '')
}

function Resolve-NodeTools {
    $nodeCommands = @(Get-Command node -All -ErrorAction SilentlyContinue)
    foreach ($nodeCommand in $nodeCommands) {
        $nodePath = $nodeCommand.Source
        $nodeVersion = Get-CommandVersion -FilePath $nodePath
        if ($nodeVersion -ne $ExpectedNodeVersion) {
            continue
        }

        $npmPath = Join-Path (Split-Path $nodePath -Parent) "npm.cmd"
        if (-not (Test-Path $npmPath)) {
            continue
        }
        $npmVersion = Get-CommandVersion -FilePath $npmPath
        if ($npmVersion -eq $ExpectedNpmVersion) {
            return @{ Node = $nodePath; Npm = $npmPath }
        }
    }

    throw "Node.js $ExpectedNodeVersion and npm $ExpectedNpmVersion are required."
}

function Resolve-BasePython {
    if ($PythonExecutable) {
        if (-not (Test-Path $PythonExecutable)) {
            throw "The specified Python executable does not exist: $PythonExecutable"
        }
        return @{ Path = (Resolve-Path $PythonExecutable).Path; PrefixArguments = @() }
    }

    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) {
        $version = Get-CommandVersion -FilePath $launcher.Source -Arguments @("-3.13", "--version")
        if ($version -eq "Python $ExpectedPythonVersion") {
            return @{ Path = $launcher.Source; PrefixArguments = @("-3.13") }
        }
    }

    foreach ($commandName in @("python3.13", "python")) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($command) {
            $version = Get-CommandVersion -FilePath $command.Source
            if ($version -eq "Python $ExpectedPythonVersion") {
                return @{ Path = $command.Source; PrefixArguments = @() }
            }
        }
    }

    throw "Python $ExpectedPythonVersion is required. Install it or use -PythonExecutable to specify python.exe."
}

Write-Host "Knowledge Vault environment setup" -ForegroundColor Green
Write-Host "Project directory: $RootDir"

$nodeTools = Resolve-NodeTools
$nodeDir = Split-Path $nodeTools.Node -Parent
$env:PATH = "$nodeDir;$env:PATH"
Write-Host "Node.js: $ExpectedNodeVersion"
Write-Host "npm: $ExpectedNpmVersion"

if (-not (Test-Path $VenvPython)) {
    Write-Step "python -m venv .venv"
    $basePython = Resolve-BasePython
    $venvArguments = @($basePython.PrefixArguments) + @("-m", "venv", $VenvDir)
    Invoke-Checked -FilePath $basePython.Path -Arguments $venvArguments
}

$actualPythonVersion = Get-CommandVersion -FilePath $VenvPython -Arguments @(
    "-c",
    "import platform; print(platform.python_version())"
)
if ($actualPythonVersion -ne $ExpectedPythonVersion) {
    throw ".venv uses Python $actualPythonVersion, but $ExpectedPythonVersion is required. Remove the local .venv and run setup again."
}
Write-Host "Python: $actualPythonVersion"

Write-Step "Install locked backend dependencies"
Invoke-Checked -FilePath $VenvPython -Arguments @(
    "-m", "pip", "install", "--cache-dir", $PipCacheDir, "--upgrade", "pip==26.2.1"
)
Invoke-Checked -FilePath $VenvPython -Arguments @(
    "-m", "pip", "install", "--cache-dir", $PipCacheDir, "--requirement", $RequirementsFile
)

Write-Step "npm ci"
Push-Location $FrontendDir
try {
    Invoke-Checked -FilePath $nodeTools.Npm -Arguments @("ci", "--cache", $NpmCacheDir)
}
finally {
    Pop-Location
}

$envFile = Join-Path $RootDir ".env"
if (-not (Test-Path $envFile)) {
    Write-Step "Create local .env from .env.example"
    Copy-Item (Join-Path $RootDir ".env.example") $envFile
}

Write-Step "Run flask db upgrade head"
Push-Location $BackendDir
try {
    Invoke-Checked -FilePath $VenvPython -Arguments @(
        "-m", "flask", "--app", "run.py", "db", "upgrade", "head"
    )
}
finally {
    Pop-Location
}

if (-not $SkipVerification) {
    Write-Step "Verify backend dependencies"
    Invoke-Checked -FilePath $VenvPython -Arguments @("-m", "pip", "check")
    Push-Location $BackendDir
    try {
        Invoke-Checked -FilePath $VenvPython -Arguments @(
            "-c",
            "from app import create_app; app = create_app(); print(app.name)"
        )
    }
    finally {
        Pop-Location
    }

    Write-Step "npm run build"
    Push-Location $FrontendDir
    try {
        Invoke-Checked -FilePath $nodeTools.Npm -Arguments @("run", "build")
    }
    finally {
        Pop-Location
    }
}

Write-Host "`nEnvironment setup completed. Run .\desktop.bat to start the project." -ForegroundColor Green
