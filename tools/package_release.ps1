param(
    [string]$Version = "v0.11.2-alpha",
    [string]$BuildDir = "build-release",
    [string]$CacheBuildDir = "build-stable",
    [switch]$SkipRegen
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$BuildPath = Join-Path $Root $BuildDir
$StageRoot = Join-Path $Root "release-stage"
$Stage = Join-Path $StageRoot "TombaRecomp-windows-x64"
$ZipPath = Join-Path $Root ("TombaRecomp-{0}-windows-x64.zip" -f $Version)
$MingwBin = "C:\msys64\mingw64\bin"
$FrameworkRoot = Join-Path $Root "psxrecomp"
$RecompTools = Resolve-Path (Join-Path $FrameworkRoot "tools")
$RecompInc = Resolve-Path (Join-Path $FrameworkRoot "runtime\include")
$RuntimeTarget = "psx-runtime"

. (Join-Path $RecompTools "release_overlay_stage.ps1")

$env:PATH = "$MingwBin;$env:PATH"

# Regenerate the game's C BEFORE building. The recompiler emits the settings
# persistence init-store hook (from game_options.toml) and the widescreen sites
# at regen time; the runtime build below just compiles generated/*.c. A stale
# generated/ would ship without the settings-persistence feature.
# cmake writes benign warnings (e.g. freetype's cmake_minimum_required
# deprecation) to STDERR. Under $ErrorActionPreference='Stop', PowerShell 5.1
# promotes a native command's stderr write to a TERMINATING error, aborting the
# release for a non-error. Run the native cmake invocations with the preference
# relaxed and gate on the real signal -- $LASTEXITCODE -- instead.
function Invoke-Native {
    param([scriptblock]$Cmd, [string]$What)
    $old = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & $Cmd 2>&1 | Out-Host
    $code = $LASTEXITCODE
    $ErrorActionPreference = $old
    if ($code -ne 0) { throw "$What failed (exit $code)" }
}

function Ensure-BiosBackends {
    param([Parameter(Mandatory)][string]$FrameworkRoot)
    $stems = @()
    if (Test-Path -LiteralPath (Join-Path $FrameworkRoot "bios\OpenBIOS.toml")) {
        $stems += ,@("OpenBIOS", "bios/OpenBIOS.toml")
    }
    if (Test-Path -LiteralPath (Join-Path $FrameworkRoot "bios\SCPH1001.BIN")) {
        $stems += ,@("SCPH1001", "bios/SCPH1001.toml")
    }
    if (-not $stems) { throw "No BIOS profile available under $FrameworkRoot\bios" }

    $missing = @($stems | Where-Object {
        -not (Test-Path -LiteralPath (Join-Path $FrameworkRoot ("generated\{0}_dispatch.c" -f $_[0])))
    })
    if (-not $missing) { return }

    $bash = $null
    foreach ($cand in @("C:\msys64\usr\bin\bash.exe", "C:\msys64\mingw64\bin\bash.exe")) {
        if (Test-Path -LiteralPath $cand) { $bash = $cand; break }
    }
    if (-not $bash) {
        throw ("Missing recompiled BIOS backend(s): {0}. Install MSYS2 or run " +
               "psxrecomp/tools/regen_bios.sh manually." -f (($missing | ForEach-Object { $_[0] }) -join ', '))
    }

    $cygpath = Join-Path (Split-Path -Parent $bash) "cygpath.exe"
    $posixRoot = (& $cygpath -u $FrameworkRoot).Trim()
    $posixMingw = (& $cygpath -u $MingwBin).Trim()
    foreach ($stem in $missing) {
        Write-Host "Generating recompiled BIOS backend: $($stem[0])"
        $biosShellCmd = "export PATH='$posixMingw':`$PATH; cd '$posixRoot' && " +
                        "PSXRECOMP_BIOS_BUILD=recompiler/build tools/regen_bios.sh --config $($stem[1])"
        Invoke-Native { & $bash -c $biosShellCmd } "regen_bios ($($stem[0]))"
    }
}

$RecompSourceDir = Join-Path $FrameworkRoot "recompiler"
$RecompDir = Join-Path $RecompSourceDir "build"
if (-not (Test-Path -LiteralPath (Join-Path $RecompDir "build.ninja"))) {
    Invoke-Native {
        cmake -S $RecompSourceDir -B $RecompDir -G Ninja -DCMAKE_BUILD_TYPE=Release
    } "recompiler configure"
}
Invoke-Native { cmake --build $RecompDir --target psxrecomp-game psxrecomp-bios -j $env:NUMBER_OF_PROCESSORS } "recompiler build"
Ensure-BiosBackends -FrameworkRoot $FrameworkRoot
if ($SkipRegen) {
    Write-Host "SkipRegen: shipping checked-in generated/ code without requiring a local disc image"
} else {
    & (Join-Path $RecompDir "psxrecomp-game.exe") --config (Join-Path $Root "game.toml")
    if ($LASTEXITCODE -ne 0) { throw "game regen failed" }
}

Invoke-Native { cmake -S $Root -B $BuildPath -G Ninja -DCMAKE_BUILD_TYPE=Release -DPSX_DEBUG_TOOLS=OFF } "cmake configure"
Invoke-Native { cmake --build $BuildPath --target $RuntimeTarget -j $env:NUMBER_OF_PROCESSORS } "cmake build"

if (Test-Path $StageRoot) {
    Remove-Item -Recurse -Force $StageRoot
}
New-Item -ItemType Directory -Force $Stage | Out-Null
New-Item -ItemType Directory -Force (Join-Path $Stage "saves") | Out-Null

# The current framework derives OUTPUT_NAME from WINDOW_TITLE. For
# "Tomba! Recompiled" that is Tomba__Recompiled.exe; older framework pins
# emitted psx-runtime.exe. Prefer the current name but keep the fallback so
# historical release branches remain packageable.
$DevExe = Join-Path $BuildPath "Tomba__Recompiled.exe"
if (-not (Test-Path $DevExe)) { $DevExe = Join-Path $BuildPath "psx-runtime.exe" }
if (-not (Test-Path $DevExe)) { throw "Built runtime executable not found in $BuildPath" }
Copy-Item $DevExe (Join-Path $Stage "TombaRecomp.exe")
Copy-Item (Join-Path $Root "README.md") $Stage
Copy-Item (Join-Path $Root "LICENSE") $Stage
$BundledBiosSrc = Join-Path $BuildPath "bios"
if (!(Test-Path (Join-Path $BundledBiosSrc "openbios.bin")) -or
    (Get-Item (Join-Path $BundledBiosSrc "openbios.bin")).Length -ne 524288 -or
    !(Test-Path (Join-Path $BundledBiosSrc "OpenBIOS.LICENSE"))) {
    throw "Runtime build did not stage OpenBIOS and its MIT notice"
}
$BundledBiosDst = Join-Path $Stage "bios"
New-Item -ItemType Directory -Force $BundledBiosDst | Out-Null
Copy-Item (Join-Path $BundledBiosSrc "openbios.bin") $BundledBiosDst
Copy-Item (Join-Path $BundledBiosSrc "OpenBIOS.LICENSE") $BundledBiosDst
$ThirdPartyLicenses = Join-Path $Stage "licenses"
New-Item -ItemType Directory -Force $ThirdPartyLicenses | Out-Null
Copy-Item (Join-Path $Root "psxrecomp\runtime\licenses\libchdr-NOTICES.txt") `
    $ThirdPartyLicenses
if (Test-Path (Join-Path $Root "RELEASE_NOTES.md")) {
    Copy-Item (Join-Path $Root "RELEASE_NOTES.md") $Stage
}

# Launcher assets: this build ships the shared recomp-ui Dear ImGui launcher
# (RECOMP_LAUNCHER; see main.cpp + recomp-ui/recomp_ui.cmake), which loads from
# <exe>/assets/ (fonts + img TGAs, including this repo's boxart baked in by
# recomp_target_launcher_ui's POST_BUILD).
$AssetsSrc = Join-Path $BuildPath "assets"
if (-not (Test-Path (Join-Path $AssetsSrc "img"))) {
    throw "recomp-ui launcher assets missing at $AssetsSrc -- was the recomp-ui launcher built (recomp-ui junction present)?"
}
Copy-Item -Recurse -Force $AssetsSrc (Join-Path $Stage "assets")
$fontCount = (Get-ChildItem (Join-Path $Stage "assets/fonts") -Filter *.ttf -ErrorAction SilentlyContinue).Count
$imgCount  = (Get-ChildItem (Join-Path $Stage "assets/img")   -Filter *.tga -ErrorAction SilentlyContinue).Count
Write-Host "Bundled recomp-ui launcher assets: $fontCount font(s) + $imgCount image(s)"

Add-ModCatalog -BuildPath $BuildPath -Stage $Stage `
               -RuntimeTarget $RuntimeTarget | Out-Null

# Player-facing game.toml is shared with the AppImage package so release
# defaults cannot drift between Windows and Linux.
Copy-Item (Join-Path $Root "packaging\release\game.toml") `
    (Join-Path $Stage "game.toml")

# Tomba's native OPTION-screen settings declaration (the RAM addresses the
# settings-persistence feature reads/writes). Required for in-game settings
# (text speed, sound, vibration, screen adjust) to persist between launches.
Copy-Item (Join-Path $Root "game_options.toml") $Stage

# Prebuilt overlay cache + self-contained overlay toolchain are staged by the
# shared framework implementation. Keep this a call; Tomba 1 must not own tag
# formatting, shard filtering, or toolchain layout.
$CgTag = Get-OverlayCgTag -RecompTools $RecompTools -RecompInc $RecompInc `
                          -GameExe (Join-Path $RecompDir "psxrecomp-game.exe") `
                          -GameToml (Join-Path $Stage "game.toml") `
                          -BuildPath $BuildPath -RuntimeTarget $RuntimeTarget
Write-Host "Release codegen tag: $CgTag (only this cache namespace is shipped)"
Add-OverlayCache -GameId "SCUS-94236" `
                 -CacheSrcRoot (Join-Path $Root "$CacheBuildDir/cache") `
                 -Stage $Stage -CgTag $CgTag | Out-Null
Add-OverlayToolchain -Stage $Stage -RecompDir $RecompDir -RecompTools $RecompTools `
                     -RecompInc $RecompInc -MingwBin $MingwBin `
                     -DlCache (Join-Path $Root "tools\_toolchain_cache") | Out-Null

# The Release build is statically linked (PSX_STATIC_RUNTIME defaults ON for
# MinGW Release in psxrecomp/runtime/runtime.cmake), so TombaRecomp.exe imports
# ONLY Windows system DLLs -- no SDL2.dll / libgcc_s_seh-1.dll / libstdc++-6.dll
# to bundle. Shipping those side-by-side was the cause of the 0xc000007b launch
# crash (issue #1) on machines with a mismatched copy earlier on the DLL search
# path. Assert self-containment rather than trust it.
$objdump = Join-Path $MingwBin "objdump.exe"
$imports = & $objdump -p (Join-Path $Stage "TombaRecomp.exe") |
    Select-String "DLL Name: (.+)" | ForEach-Object { $_.Matches[0].Groups[1].Value.Trim() }
$systemDlls = @("kernel32.dll","user32.dll","gdi32.dll","shell32.dll","msvcrt.dll",
                "advapi32.dll","ws2_32.dll","comdlg32.dll","dbghelp.dll","ole32.dll",
                "oleaut32.dll","winmm.dll","imm32.dll","version.dll","setupapi.dll",
                "dinput8.dll","rpcrt4.dll","hid.dll","cfgmgr32.dll","opengl32.dll")
$nonSystem = $imports | Where-Object { $systemDlls -notcontains $_.ToLower() }
if ($nonSystem) {
    throw "Release exe is NOT self-contained -- imports non-system DLL(s): $($nonSystem -join ', ')"
}
Write-Host "Verified self-contained: imports only system DLLs ($($imports.Count) total)"

@"
; PSXRecomp input mapping. PSX buttons are active when any listed source is pressed.
; Sources use SDL/Xbox names: a,b,x,y,back,start,leftshoulder,rightshoulder,
; lefttrigger,righttrigger,dpup,dpdown,dpleft,dpright,leftx-/leftx+/lefty-/lefty+.

[controller]
enabled = true
device = 0
deadzone = 12000

[mapping]
up = dpup,lefty-
down = dpdown,lefty+
left = dpleft,leftx-
right = dpright,leftx+
cross = a
circle = b
square = x
triangle = y
l1 = leftshoulder
r1 = rightshoulder
l2 = lefttrigger
r2 = righttrigger
start = start
select = back
"@ | Set-Content -Encoding ASCII (Join-Path $Stage "input.ini")

@"
TombaRecomp $Version

This package includes the MIT-licensed OpenBIOS from PCSX-Redux and its notice
in bios/OpenBIOS.LICENSE. It does not include the Tomba disc, a retail
PlayStation BIOS, save data, or game assets.

First launch:
1. Run TombaRecomp.exe. A launcher window opens.
2. OpenBIOS is selected automatically. You may optionally select your legally
   obtained SCPH1001.BIN in the BIOS row.
3. Set the game disc: select your legally obtained Tomba! (USA, SCUS-94236)
   disc image.
4. Adjust any options you like (renderer, supersampling, screen look,
   controller), then press Launch. Your choices are remembered next time.

Disc image formats:
- .cue + .bin (preferred - pick the .cue)
- .bin
- .img
- .iso
- .car (Steam; t_data_u.car works without renaming)
- .chd

An optional retail BIOS choice and the selected disc path are saved next to the
executable. Clear the BIOS row to return to OpenBIOS.

If the disc header or game ID does not match SCUS-94236, TombaRecomp will show
a warning and try to run the image anyway. Boot may fail if the image is the
wrong game, the wrong region, or corrupt.

Fast Loading is disabled by default. Enable its mod in the launcher and choose
one dropdown value. Host pacing is recommended; experimental CD timing can
break timing-sensitive loads, audio, or speedrun strategies.

The cache folder contains pre-converted native code for game areas covered
so far; those run at full speed from your first visit. As you play, newly
visited areas are recorded into overlay_captures.json and your local cache
grows automatically. Do NOT post overlay_captures.json publicly - it
contains snapshots of the game's own code read from your disc. See
README.md ("Help make your game faster") for details.

Keyboard and Xbox-style controller defaults are documented in README.md.
Controller mappings are configurable in input.ini.

Memory cards are stored in the saves directory.
"@ | Set-Content -Encoding ASCII (Join-Path $Stage "START_HERE.txt")

if (Test-Path $ZipPath) {
    Remove-Item -Force $ZipPath
}
$ZipHelper = Join-Path $Root "psxrecomp\tools\create_release_zip.py"
if (-not (Test-Path $ZipHelper)) {
    throw "Portable ZIP helper missing from pinned psxrecomp: $ZipHelper"
}
Invoke-Native {
    python $ZipHelper --source $Stage --output $ZipPath
} "portable release ZIP"

Write-Host "Wrote $ZipPath"
