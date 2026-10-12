<#
.SYNOPSIS
Builds the Colony Print node installer for Windows (setup.exe).

.DESCRIPTION
Builds the wheel of the node (colony-print) with the provided (64 bit) Python
interpreter and downloads the wheels of npcolony and of the dependencies from
PyPI (so that nothing is compiled), installs them in an embedded Python
distribution of the same version and compiles the Inno Setup installer with
it, together with the WinSW service wrapper.

The installer of the Windows XP nodes (32 bit) is built with the XP switch
and a 32 bit Python 2.7 interpreter (the last one that runs on Windows XP),
the Python of the node is extracted from its installer (as it has no embedded
distribution), the service wrapper is NSSM (as WinSW requires a .NET Framework
that Windows XP lacks) and the installer is compiled with Inno Setup 5 (the
last one that supports Windows XP), bundling the redistributable of the Visual
C++ 2008 runtime required by that Python.

.EXAMPLE
.\windows\build.ps1 -Python C:\Python314\python.exe

.EXAMPLE
.\windows\build.ps1 -XP -Python C:\Python27\python.exe
#>
param(
    [string]$Python = "python",
    [string]$Npcolony = "npcolony>=1.4.0",
    [string]$WinSWVersion = "2.12.0",
    [string]$WinSWSha256 = "b5066b7bbdfba1293e5d15cda3caaea88fbeab35bd5b38c41c913d492aadfc4f",
    [string]$NssmSha256 = "472232ca821b5c2ef562ab07f53638bc2cc82eae84cea13fbe674d6022b6481c",
    [string]$VCRedistSha256 = "8742bcbf24ef328a72d2a27b693cc7071e38d3bb4b9b44dec42aa3d2c8d61d92",
    [string]$Iscc = "",
    [switch]$XP
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$Root = Split-Path -Parent $PSScriptRoot
$BuildDir = Join-Path $Root "build\windows"
$WheelsDir = Join-Path $BuildDir "wheels"
$PythonDir = Join-Path $BuildDir "python"
$SitePackages = Join-Path $PythonDir "Lib\site-packages"
$DistDir = Join-Path $Root "dist"

# the digests (SHA256) of the embedded Python distributions supported by the
# build, as published by python.org, so that a tampered (or corrupted) Python,
# that runs as the system account in the nodes, is never installed by it
$EmbedDigests = @{
    "3.14.8" = "a93abe456ab01bd96d7a085b3cdb6566b3063f4241360d114142fbdb07f0a310"
}

# the digests (SHA256) of the (32 bit) Python installers supported by the
# build of the Windows XP nodes, from which the Python of the node is
# extracted, python.org only publishes their MD5 digests, the one of the
# 2.7.18 installer being db6ad9195b3086c6b4cefb9493d738d2
$InstallerDigests = @{
    "2.7.18" = "d901802e90026e9bad76b8a81f8dd7e43c7d7e8269d9281c9e9df7a9c40480a9"
}

# the parts of the Python extracted from its installer that are not used
# by the node (eg: the documentation and the test suite), that are removed
$Unused = @("Doc", "include", "libs", "tcl", "Tools", "Lib\idlelib", "Lib\lib-tk", "Lib\test")

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

# downloads the file at the provided URL, trying again (after a pause) when
# it fails, as the servers of the downloads are unavailable every now and
# then (eg: answering with a 503), which would otherwise fail the whole build
function Invoke-Download {
    param([string]$Uri, [string]$OutFile, [int]$Attempts = 5, [int]$Delay = 15)
    for ($Attempt = 1; $true; $Attempt++) {
        try {
            Invoke-WebRequest -Uri $Uri -OutFile $OutFile
            return
        }
        catch {
            if ($Attempt -ge $Attempts) {
                throw
            }
            Write-Host "Download of $Uri failed, trying again in $Delay seconds"
            Start-Sleep -Seconds $Delay
        }
    }
}

# retrieves the version of the node (from the package) and the version of
# the Python interpreter, the embedded Python must be of the same version
# so that the native wheels (eg: npcolony) built with it are compatible,
# the Windows XP nodes requiring a 32 bit Python and having their own
# installer (name), so that both installers may be built and released
$Setup = Get-Content -Raw -Path (Join-Path $Root "setup.py")
$Version = [regex]::Match($Setup, 'version="([^"]+)"').Groups[1].Value
$PythonVersion = Get-NativeOutput $Python @("-c", "import platform; print(platform.python_version())")
$PythonBits = Get-NativeOutput $Python @("-c", "import struct; print(struct.calcsize('P') * 8)")
$PythonTag = Get-NativeOutput $Python @("-c", "import sys; print('python%d%d' % sys.version_info[:2])")
$Bits = "64"
$Digests = $EmbedDigests
$Installer = "colony-print-node-setup-$Version.exe"
if ($XP) {
    $Bits = "32"
    $Digests = $InstallerDigests
    $Installer = "colony-print-node-setup-xp-$Version.exe"
}
if ($PythonBits -ne $Bits) {
    throw "A $Bits bit Python interpreter is required (found $PythonBits bit)"
}
if (-not $Digests.ContainsKey($PythonVersion)) {
    throw "No digest of the embedded Python $PythonVersion, add it to the build"
}
Write-Host "Building Colony Print node $Version with Python $PythonVersion"

if (Test-Path $BuildDir) {
    Remove-Item -Recurse -Force $BuildDir
}
New-Item -ItemType Directory -Force -Path $BuildDir, $WheelsDir, $PythonDir | Out-Null

# builds the wheel of the node (from the repository) and downloads the wheels
# of the other packages and of the dependencies from PyPI, only accepting the
# wheels, as npcolony (since 1.4.0) has wheels for Windows, the ones for
# Windows XP (32 bit, Python 2.7) existing since 1.7.0
Write-Host "Building wheels"
Invoke-Native $Python @("-m", "pip", "wheel", "--no-deps", "--wheel-dir", $WheelsDir, $Root)
$Wheel = Get-ChildItem -Path (Join-Path $WheelsDir "colony_print-*.whl") | Select-Object -First 1
Invoke-Native $Python (@(
    "-m", "pip", "wheel", "--only-binary", ":all:", "--wheel-dir", $WheelsDir,
    $Wheel.FullName, $Npcolony
) + $Packages)

if ($XP) {
    # downloads the (32 bit) Python installer and extracts it (administrative
    # install) as the Python of the node, as the versions of Python that run
    # on Windows XP have no embedded distribution, removing the copy of the
    # installer that is left in it and the parts that are not used by the
    # node, notice that its site packages are enabled by default and that
    # the first path entry is the one of the script (removed by appier)
    Write-Host "Downloading Python $PythonVersion installer"
    $EmbedMsi = Join-Path $BuildDir "python.msi"
    $EmbedUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion.msi"
    Invoke-Download -Uri $EmbedUrl -OutFile $EmbedMsi
    $EmbedHash = (Get-FileHash -Path $EmbedMsi -Algorithm SHA256).Hash.ToLower()
    if ($EmbedHash -ne $InstallerDigests[$PythonVersion]) {
        throw "Invalid Python installer digest $EmbedHash (expected $($InstallerDigests[$PythonVersion]))"
    }
    $Process = Start-Process -Wait -PassThru -FilePath "msiexec.exe" -ArgumentList @(
        "/a", "`"$EmbedMsi`"", "/qn", "TARGETDIR=`"$PythonDir`""
    )
    if ($Process.ExitCode -ne 0) {
        throw "Extraction of the Python installer failed with exit code $($Process.ExitCode)"
    }
    Remove-Item $EmbedMsi
    Remove-Item (Join-Path $PythonDir "*.msi")
    foreach ($Name in $Unused) {
        $UnusedDir = Join-Path $PythonDir $Name
        if (Test-Path $UnusedDir) {
            Remove-Item -Recurse -Force $UnusedDir
        }
    }
}
else {
    # downloads the embedded Python distribution and enables the site packages
    # in it (disabled by default), where the node packages are installed, notice
    # that the first path entry (Lib) has no modules, as appier removes the first
    # entry of the path (expected to be the one of the script) while importing
    # some modules, which would otherwise be the standard library
    Write-Host "Downloading embedded Python $PythonVersion"
    $EmbedZip = Join-Path $BuildDir "python-embed.zip"
    $EmbedUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"
    Invoke-Download -Uri $EmbedUrl -OutFile $EmbedZip
    $EmbedHash = (Get-FileHash -Path $EmbedZip -Algorithm SHA256).Hash.ToLower()
    if ($EmbedHash -ne $EmbedDigests[$PythonVersion]) {
        throw "Invalid embedded Python digest $EmbedHash (expected $($EmbedDigests[$PythonVersion]))"
    }
    Expand-Archive -Path $EmbedZip -DestinationPath $PythonDir
    Remove-Item $EmbedZip
    Set-Content -Path (Join-Path $PythonDir "$PythonTag._pth") -Encoding Ascii -Value @(
        "Lib",
        "$PythonTag.zip",
        ".",
        "Lib\site-packages",
        "import site"
    )
}

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

# copies the boot script, that is run by the service from outside of the
# packages it updates, so that a failed update never prevents it from running
Copy-Item -Path (Join-Path $Root "src\colony_print\boot.py") -Destination (Join-Path $BuildDir "boot.py")

if ($XP) {
    # copies the NSSM service wrapper (the 32 bit build of its 2.24 version),
    # verifying its digest, as WinSW requires a .NET Framework that Windows XP
    # lacks, the wrapper being kept in the repository (it's public domain) as
    # its site (nssm.cc) is unavailable too often for it to be downloaded
    $Nssm = Join-Path $BuildDir "nssm.exe"
    Copy-Item -Path (Join-Path $PSScriptRoot "nssm.exe") -Destination $Nssm
    $NssmHash = (Get-FileHash -Path $Nssm -Algorithm SHA256).Hash.ToLower()
    if ($NssmHash -ne $NssmSha256.ToLower()) {
        throw "Invalid NSSM digest $NssmHash (expected $NssmSha256)"
    }

    # downloads the redistributable of the Visual C++ 2008 runtime (32 bit),
    # verifying its digest, that is run by the installer of the node, as the
    # Python of the node requires this runtime, which is not part of the Python
    # extracted from its installer (nor of Windows XP), so that the node would
    # not start in the machines without it
    Write-Host "Downloading Visual C++ 2008 redistributable"
    $VCRedist = Join-Path $BuildDir "vcredist_x86.exe"
    $VCRedistUrl = "https://download.microsoft.com/download/5/D/8/5D8C65CB-C849-4025-8E95-C3966CAFD8AE/vcredist_x86.exe"
    Invoke-Download -Uri $VCRedistUrl -OutFile $VCRedist
    $VCRedistHash = (Get-FileHash -Path $VCRedist -Algorithm SHA256).Hash.ToLower()
    if ($VCRedistHash -ne $VCRedistSha256.ToLower()) {
        throw "Invalid Visual C++ redistributable digest $VCRedistHash (expected $VCRedistSha256)"
    }
}
else {
    # downloads the WinSW service wrapper, verifying its digest, that is renamed
    # after the service, as WinSW loads the configuration file with its name
    Write-Host "Downloading WinSW $WinSWVersion"
    $WinSW = Join-Path $BuildDir "colony-print-node.exe"
    $WinSWUrl = "https://github.com/winsw/winsw/releases/download/v$WinSWVersion/WinSW.NET461.exe"
    Invoke-Download -Uri $WinSWUrl -OutFile $WinSW
    $WinSWHash = (Get-FileHash -Path $WinSW -Algorithm SHA256).Hash.ToLower()
    if ($WinSWHash -ne $WinSWSha256.ToLower()) {
        throw "Invalid WinSW digest $WinSWHash (expected $WinSWSha256)"
    }
}

# compiles the installer, the one of the Windows XP nodes with Inno Setup 5
# (the last one that supports Windows XP) and with the XP definition
$InnoSetup = "Inno Setup 6"
$Definitions = @("/DAppVersion=$Version", "/DBuildDir=$BuildDir", "/DOutputDir=$DistDir")
if ($XP) {
    $InnoSetup = "Inno Setup 5"
    $Definitions += "/DXP"
}
if (-not $Iscc) {
    $Command = Get-Command "iscc.exe" -ErrorAction SilentlyContinue
    if ($Command) {
        $Iscc = $Command.Source
    }
    else {
        $Iscc = Join-Path ${env:ProgramFiles(x86)} "$InnoSetup\ISCC.exe"
    }
}
Write-Host "Compiling installer with $Iscc"
Invoke-Native $Iscc (@("/Q") + $Definitions + @(Join-Path $PSScriptRoot "setup.iss"))

Write-Host "Built $(Join-Path $DistDir $Installer)"
