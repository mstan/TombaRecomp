$ErrorActionPreference = 'Stop'

$Root      = Split-Path -Parent $PSScriptRoot
$Framework = Join-Path $Root 'psxrecomp'
$Tool      = Join-Path $Framework 'recompiler/build/psxrecomp-game.exe'
$Config    = Join-Path $Root 'game.toml'

if (!(Test-Path $Tool)) {
    throw @"
recompiler tool not built: $Tool

Build it first (one time):
  cmake -S "$Framework/recompiler" -B "$Framework/recompiler/build" -G Ninja -DCMAKE_BUILD_TYPE=Release
  cmake --build "$Framework/recompiler/build"
See psxrecomp/docs/BUILDING.md ("Build and run a game").
"@
}
if (!(Test-Path $Config)) {
    throw "game.toml not found: $Config"
}

# Config-driven invocation. The TOML describes exe, seeds, out_dir —
# see psxrecomp/docs/config_schema.md.
Push-Location $Root
try {
    & $Tool --config $Config
    if ($LASTEXITCODE -ne 0) {
        throw "psxrecomp-game exited with code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
