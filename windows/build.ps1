<#
.SYNOPSIS
Builds the Colony Print node installer for Windows (setup.exe).

.DESCRIPTION
Builds the wheels of the node (colony-print, npcolony and their dependencies)
with the provided (64 bit) Python interpreter, compiling npcolony with the
Visual C++ compiler of the machine, installs them in an embedded Python
distribution of the same version and compiles the Inno Setup installer with
it, together with the WinSW service wrapper.

The wheels are also copied to the dist\packages directory, ready to be uploaded
to the Colony Print server, from where the nodes update themselves.

.EXAMPLE
.\windows\build.ps1 -Python C:\Python314\python.exe
#>
param(
    [string]$Python = "python",
    [string]$Npcolony = "npcolony",
    [string]$WinSWVersion = "2.12.0",
    [string]$WinSWSha256 = "b5066b7bbdfba1293e5d15cda3caaea88fbeab35bd5b38c41c913d492aadfc4f",
    [string]$Iscc = ""
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$Root = Split-Path -Parent $PSScriptRoot
$BuildDir = Join-Path $Root "build\windows"
$WheelsDir = Join-Path $BuildDir "wheels"
$PythonDir = Join-Path $BuildDir "python"
$SitePackages = Join-Path $PythonDir "Lib\site-packages"
$DistDir = Join-Path $Root "dist"
$PackagesDir = Join-Path $DistDir "packages"

# the packages installed in the node, besides colony-print (built from the
# repository) and npcolony, notice that netius is required as it's the HTTP
# client used by appier, that would otherwise try to install it on runtime
$Packages = @("mailme-api", "netius", "pip")

function Invoke-Native {
    param([string]$File, [string[]]$Arguments)
    & $File @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command '$File $Arguments' failed with exit code $LASTEXITCODE"
    }
}

function Get-NativeOutput {
    param([string]$File, [string[]]$Arguments)
    $Output = & $File @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command '$File $Arguments' failed with exit code $LASTEXITCODE"
    }
    return ($Output | Out-String).Trim()
}

# retrieves the version of the node (from the package) and the version of
# the Python interpreter, the embedded Python must be of the same version
# so that the native wheels (eg: npcolony) built with it are compatible
$Setup = Get-Content -Raw -Path (Join-Path $Root "setup.py")
$Version = [regex]::Match($Setup, 'version="([^"]+)"').Groups[1].Value
$PythonVersion = Get-NativeOutput $Python @("-c", "import platform; print(platform.python_version())")
$PythonBits = Get-NativeOutput $Python @("-c", "import struct; print(struct.calcsize('P') * 8)")
$PythonTag = Get-NativeOutput $Python @("-c", "import sys; print('python%d%d' % sys.version_info[:2])")
if ($PythonBits -ne "64") {
    throw "A 64 bit Python interpreter is required (found $PythonBits bit)"
}
Write-Host "Building Colony Print node $Version with Python $PythonVersion"

if (Test-Path $BuildDir) {
    Remove-Item -Recurse -Force $BuildDir
}
if (Test-Path $PackagesDir) {
    Remove-Item -Recurse -Force $PackagesDir
}
New-Item -ItemType Directory -Force -Path $BuildDir, $WheelsDir, $PythonDir, $PackagesDir | Out-Null

# builds the wheels of the node packages and of their dependencies, the
# ones without wheels (eg: npcolony) are built from their sources
Write-Host "Building wheels"
Invoke-Native $Python (@("-m", "pip", "wheel", "--wheel-dir", $WheelsDir, $Root, $Npcolony) + $Packages)

# downloads the embedded Python distribution and enables the site packages
# in it (disabled by default), where the node packages are installed, notice
# that the first path entry (Lib) has no modules, as appier removes the first
# entry of the path (expected to be the one of the script) while importing
# some modules, which would otherwise be the standard library
Write-Host "Downloading embedded Python $PythonVersion"
$EmbedZip = Join-Path $BuildDir "python-embed.zip"
$EmbedUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"
Invoke-WebRequest -Uri $EmbedUrl -OutFile $EmbedZip
Expand-Archive -Path $EmbedZip -DestinationPath $PythonDir
Remove-Item $EmbedZip
Set-Content -Path (Join-Path $PythonDir "$PythonTag._pth") -Encoding Ascii -Value @(
    "Lib",
    "$PythonTag.zip",
    ".",
    "Lib\site-packages",
    "import site"
)

# installs the node packages in the site packages of the embedded Python,
# using the (same version) interpreter of the build, as the embedded one
# has no pip, that is installed as one of the packages
Write-Host "Installing packages in embedded Python"
Invoke-Native $Python (@(
    "-m", "pip", "install", "--no-index", "--find-links", $WheelsDir,
    "--target", $SitePackages, "--no-warn-script-location", "colony-print", "npcolony"
) + $Packages)
$BinDir = Join-Path $SitePackages "bin"
if (Test-Path $BinDir) {
    Remove-Item -Recurse -Force $BinDir
}

# verifies that the embedded Python is able to load the node and its native
# dependencies, listing the printers found by npcolony
$EmbedPython = Join-Path $PythonDir "python.exe"
Invoke-Native $EmbedPython @(
    "-c",
    "import npcolony, mailme, netius, pip, colony_print.node; " +
    "print('npcolony %s (%s)' % (getattr(npcolony, 'VERSION', '?'), npcolony.get_format())); " +
    "print([device['name'] for device in npcolony.get_devices()])"
)

# downloads the WinSW service wrapper, verifying its digest, that is renamed
# after the service, as WinSW loads the configuration file with its name
Write-Host "Downloading WinSW $WinSWVersion"
$WinSW = Join-Path $BuildDir "colony-print-node.exe"
$WinSWUrl = "https://github.com/winsw/winsw/releases/download/v$WinSWVersion/WinSW.NET461.exe"
Invoke-WebRequest -Uri $WinSWUrl -OutFile $WinSW
$WinSWHash = (Get-FileHash -Path $WinSW -Algorithm SHA256).Hash.ToLower()
if ($WinSWHash -ne $WinSWSha256.ToLower()) {
    throw "Invalid WinSW digest $WinSWHash (expected $WinSWSha256)"
}

# copies the wheels to the dist directory, to be uploaded to the server
# so that the nodes are able to update themselves from it
Copy-Item -Path (Join-Path $WheelsDir "*.whl") -Destination $PackagesDir

if (-not $Iscc) {
    $Command = Get-Command "iscc.exe" -ErrorAction SilentlyContinue
    if ($Command) {
        $Iscc = $Command.Source
    }
    else {
        $Iscc = Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"
    }
}
Write-Host "Compiling installer with $Iscc"
Invoke-Native $Iscc @(
    "/Q",
    "/DAppVersion=$Version",
    "/DBuildDir=$BuildDir",
    "/DOutputDir=$DistDir",
    (Join-Path $PSScriptRoot "setup.iss")
)

Write-Host "Built $(Join-Path $DistDir "colony-print-node-setup-$Version.exe")"
Write-Host "Built packages in $PackagesDir"
