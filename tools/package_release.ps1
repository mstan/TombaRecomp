param(
    [string]$Version = "v0.1.1-alpha",
    [string]$BuildDir = "build-release"
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$BuildPath = Join-Path $Root $BuildDir
$StageRoot = Join-Path $Root "release-stage"
$Stage = Join-Path $StageRoot "TombaRecomp-windows-x64"
$ZipPath = Join-Path $Root ("TombaRecomp-{0}-windows-x64.zip" -f $Version)
$MingwBin = "C:\msys64\mingw64\bin"

$env:PATH = "$MingwBin;$env:PATH"

cmake -S $Root -B $BuildPath -G Ninja -DCMAKE_BUILD_TYPE=Release -DPSX_DEBUG_TOOLS=OFF
cmake --build $BuildPath -j $env:NUMBER_OF_PROCESSORS

if (Test-Path $StageRoot) {
    Remove-Item -Recurse -Force $StageRoot
}
New-Item -ItemType Directory -Force $Stage | Out-Null
New-Item -ItemType Directory -Force (Join-Path $Stage "saves") | Out-Null

Copy-Item (Join-Path $BuildPath "psx-runtime.exe") (Join-Path $Stage "TombaRecomp.exe")
Copy-Item (Join-Path $Root "game.toml") $Stage
Copy-Item (Join-Path $Root "README.md") $Stage
Copy-Item (Join-Path $Root "LICENSE") $Stage

foreach ($Dll in @("SDL2.dll", "libgcc_s_seh-1.dll", "libstdc++-6.dll")) {
    $Source = Join-Path $MingwBin $Dll
    if (!(Test-Path $Source)) {
        throw "Required runtime DLL not found: $Source"
    }
    Copy-Item $Source $Stage
}

@"
TombaRecomp $Version

This package does not include Tomba, the PlayStation BIOS, generated game
source, save data, or any copyrighted Sony/Whoopee Camp assets.

First launch:
1. Run TombaRecomp.exe.
2. Select your legally obtained SCPH1001.BIN BIOS when prompted.
3. Select your legally obtained Tomba! (USA, SCUS-94236) disc image when
   prompted.

Disc image formats:
- .cue + .bin
- .bin
- .iso

The selected BIOS path is saved in bios.cfg and the selected disc path is saved
in disc.cfg next to the executable. Delete those files if you want to pick
different files later.

If the disc header or game ID does not match SCUS-94236, TombaRecomp will show
a warning and try to run the image anyway. Boot may fail if the image is the
wrong game, the wrong region, or corrupt.

Memory cards are stored in the saves directory.
"@ | Set-Content -Encoding ASCII (Join-Path $Stage "START_HERE.txt")

if (Test-Path $ZipPath) {
    Remove-Item -Force $ZipPath
}
Compress-Archive -Path (Join-Path $Stage "*") -DestinationPath $ZipPath -Force

Write-Host "Wrote $ZipPath"
