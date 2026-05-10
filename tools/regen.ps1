$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$Framework = Join-Path $Root 'psxrecomp-v4'
$Tool = Join-Path $Framework 'recompiler/build/psxrecomp-game.exe'
$Exe = Join-Path $Root 'tomba/SCUS_942.36'
$Seeds = Join-Path $Root 'seeds/ghidra_funcs.txt'
$OutDir = Join-Path $Root 'generated'

if (!(Test-Path $Tool)) {
    throw "psxrecomp-game not built: $Tool"
}
if (!(Test-Path $Exe)) {
    throw "Tomba EXE not found: $Exe"
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

& $Tool $Exe --seeds $Seeds --strict --out-dir $OutDir
