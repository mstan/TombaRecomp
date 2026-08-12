param(
    [string]$Version = "v0.11.2-alpha",
    [string]$BuildDir = "build-release",
    # Ship without a bundled overlay cache. Off by default: a cache-less
    # package makes every player's first session run overlays interpreted, so
    # it has to be asked for rather than warned about.
    [switch]$AllowNoCache
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$BuildPath = Join-Path $Root $BuildDir
$StageRoot = Join-Path $Root "release-stage"
$Stage = Join-Path $StageRoot "TombaRecomp-windows-x64"
$ZipPath = Join-Path $Root ("TombaRecomp-{0}-windows-x64.zip" -f $Version)
$MingwBin = "C:\msys64\mingw64\bin"

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

$RecompDir = Resolve-Path (Join-Path $Root "psxrecomp\recompiler\build")
Invoke-Native { cmake --build $RecompDir --target psxrecomp-game -j $env:NUMBER_OF_PROCESSORS } "recompiler build"
& (Join-Path $RecompDir "psxrecomp-game.exe") --config (Join-Path $Root "game.toml")
if ($LASTEXITCODE -ne 0) { throw "game regen failed" }

Invoke-Native { cmake -S $Root -B $BuildPath -G Ninja -DCMAKE_BUILD_TYPE=Release -DPSX_DEBUG_TOOLS=OFF } "cmake configure"
Invoke-Native { cmake --build $BuildPath -j $env:NUMBER_OF_PROCESSORS } "cmake build"

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

# Built-in mod catalog: CMake stages game-owned packages next to the runtime.
# Ship that exact output so the release and local-build catalogs cannot drift.
# Native plugin implementations remain compiled into the executable; these
# packages are metadata that expose their default-off features in recomp-ui.
$ModsSrc = Join-Path $BuildPath "mods"
$WarpManifest = Join-Path $ModsSrc "packages/tomba.debug.warp/1.0.0/manifest.toml"
$WidescreenManifest = Join-Path $ModsSrc "packages/tomba.enhancement.widescreen/1.0.0/manifest.toml"
$SkipFmvManifest = Join-Path $ModsSrc "packages/tomba.enhancement.skip-fmv/1.0.0/manifest.toml"
$InterpolationManifest = Join-Path $ModsSrc "packages/tomba.enhancement.frame-interpolation/1.0.0/manifest.toml"
$HybridManifest = Join-Path $ModsSrc "packages/tomba.enhancement.hybrid-controller/1.0.0/manifest.toml"
$FastLoadingManifest = Join-Path $ModsSrc "packages/psx.enhancement.fast-loading/1.0.0/manifest.toml"
foreach ($RequiredManifest in @(
    $WarpManifest,
    $WidescreenManifest,
    $SkipFmvManifest,
    $InterpolationManifest,
    $HybridManifest,
    $FastLoadingManifest
)) {
    if (-not (Test-Path $RequiredManifest)) {
        throw "Built-in mod catalog missing from runtime output: $RequiredManifest"
    }
}
Copy-Item -Recurse -Force $ModsSrc (Join-Path $Stage "mods")
Write-Host "Bundled built-in mod catalog from $ModsSrc"

# Player-facing game.toml is shared with the AppImage package so release
# defaults cannot drift between Windows and Linux.
Copy-Item (Join-Path $Root "packaging\release\game.toml") `
    (Join-Path $Stage "game.toml")

# Tomba's native OPTION-screen settings declaration (the RAM addresses the
# settings-persistence feature reads/writes). Required for in-game settings
# (text speed, sound, vibration, screen adjust) to persist between launches.
Copy-Item (Join-Path $Root "game_options.toml") $Stage

# Prebuilt overlay cache: native code for the game areas contributed so far.
# The cache is namespaced per backend/arch/codegen-version:
#   gcc/<arch-abi>/cg<N>_<hash>/<entry8>_<crc8>.dll (+ .ranges)
# and the loader scans it by that exact path, so the subtree must be preserved
# (a flat copy bundles nothing / won't load). Ship .dll + .ranges only (the
# _patched.c intermediates are build artifacts); skip the reserved sljit/
# namespace (it has no on-disk blobs), and ONLY the dir matching THIS build's
# codegen tag -- a stale-hash dir is dead weight the runtime never loads (it was
# the cause of the v0.3.0 black-screen: shipping a cg dir the emitter moved past).
$RecompTools = Resolve-Path (Join-Path $Root "psxrecomp\tools")
$RecompInc   = Resolve-Path (Join-Path $Root "psxrecomp\runtime\include")
$tagScript = Join-Path $env:TEMP ("psx_cgtag_{0}.py" -f $PID)
@"
import importlib.util
s = importlib.util.spec_from_file_location('co', r'$RecompTools\compile_overlays.py')
m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
inc = r'$RecompInc'
print('cg%d_%08x_gc%08x' % (
    m.codegen_ver(inc),
    m.codegen_hash(inc),
    m.overlay_config_hash(
        r'$(Join-Path $RecompDir "psxrecomp-game.exe")',
        r'$(Join-Path $Stage "game.toml")')))
"@ | Set-Content -Encoding ASCII $tagScript
$CgTag = (& python $tagScript).Trim()
Remove-Item -Force $tagScript
Write-Host "Release codegen tag: $CgTag (only this cache namespace is shipped)"
$CacheSrc = Join-Path $Root "build-stable/cache/SCUS-94236"
if (Test-Path $CacheSrc) {
    $CacheDst = Join-Path $Stage "cache/SCUS-94236"
    $cacheFiles = Get-ChildItem $CacheSrc -Recurse -File -Include *.dll,*.ranges |
        Where-Object { $_.FullName -notmatch '[\\/]sljit[\\/]' -and $_.FullName -match "[\\/]$CgTag[\\/]" }
    foreach ($f in $cacheFiles) {
        $rel  = $f.FullName.Substring($CacheSrc.Length).TrimStart('\','/')
        $dest = Join-Path $CacheDst $rel
        New-Item -ItemType Directory -Force (Split-Path $dest) | Out-Null
        Copy-Item $f.FullName $dest
    }
    $dllCount = (Get-ChildItem $CacheDst -Recurse -Filter *.dll -ErrorAction SilentlyContinue).Count
    Write-Host "Bundled overlay cache: $dllCount native overlay DLL(s)"
    if ($dllCount -eq 0) {
        throw ("Overlay cache at $CacheSrc has no shards for this build's tag $CgTag. " +
               "Rebuild it against this runtime AND the packaged game.toml " +
               "(the tag folds in an overlay-config hash of both), or pass " +
               "-AllowNoCache to ship without one.")
    }
} elseif ($AllowNoCache) {
    Write-Warning "No overlay cache at $CacheSrc - shipping without one because -AllowNoCache was given"
} else {
    # A cache-less package makes every player's first session run overlays
    # interpreted. v0.11.2 nearly shipped that way silently because the tag
    # computed here had drifted from the one the runtime and compile_overlays
    # actually use, so the match never hit and this branch just warned.
    throw @"
No overlay cache found at $CacheSrc, so this package would ship without one and
every player's first session would run overlays interpreted.

Build one for this release's tag ($CgTag) -- note the tag folds in a hash of
the PACKAGED game.toml, so a cache built against the dev config lands under a
different tag and will not be picked up:

  `$env:PSX_OVERLAY_CACHE_DIR = "$Root\build-stable\cache"
  `$env:PSX_OVERLAY_CAPTURES  = "<coverage vault>\overlay_captures.json"
  python psxrecomp\tools\compile_overlays.py --game-toml <packaged game.toml> ``
      --recompiler psxrecomp\recompiler\build\psxrecomp-game.exe ``
      --runtime-include psxrecomp\runtime\include --gcc C:\msys64\mingw64\bin\gcc.exe --cps

Then re-run this packager, or pass -AllowNoCache to ship without one anyway.
"@
}

# ---- Self-contained overlay toolchain (tcc tier) -------------------------
# A player box has no gcc AND no Python, so overlay_backend=auto resolves to tcc:
# the runtime fills overlay gaps the shipped gcc cache misses by spawning this
# bundled, fully self-contained toolchain. The runtime constructs the command
# from <exe>/overlay_toolchain/ (see main.cpp): embedded Python + TinyCC + the
# recompiler + compile_overlays.py + the runtime headers. Every exe here must be
# self-contained (embedded python + prebuilt tcc are; the recompiler needs its
# mingw runtime DLLs bundled beside it).
$Toolchain = Join-Path $Stage "overlay_toolchain"
New-Item -ItemType Directory -Force $Toolchain | Out-Null
$DlCache = Join-Path $Root "tools/_toolchain_cache"
New-Item -ItemType Directory -Force $DlCache | Out-Null

# Embedded Python (fixed version; downloaded once + cached)
$PyVer = "3.13.1"
$PyZip = Join-Path $DlCache "python-$PyVer-embed-amd64.zip"
if (-not (Test-Path $PyZip)) {
    Invoke-WebRequest -Uri "https://www.python.org/ftp/python/$PyVer/python-$PyVer-embed-amd64.zip" -OutFile $PyZip
}
Expand-Archive -Path $PyZip -DestinationPath (Join-Path $Toolchain "python") -Force

# TinyCC prebuilt win64 (fixed version; downloaded once + cached). The zip has a
# top-level tcc/ dir (tcc.exe + libtcc.dll + include/ + lib/) -- ship it whole.
$TccZip = Join-Path $DlCache "tcc-0.9.27-win64-bin.zip"
if (-not (Test-Path $TccZip)) {
    Invoke-WebRequest -Uri "https://download.savannah.gnu.org/releases/tinycc/tcc-0.9.27-win64-bin.zip" -OutFile $TccZip
}
$TccTmp = Join-Path $DlCache "tcc_extract"
if (Test-Path $TccTmp) { Remove-Item -Recurse -Force $TccTmp }
Expand-Archive -Path $TccZip -DestinationPath $TccTmp -Force
Copy-Item -Recurse -Force (Join-Path $TccTmp "tcc") (Join-Path $Toolchain "tcc")

# Recompiler (built above) + its mingw runtime DLLs (NOT statically linked) +
# compile_overlays.py + the runtime headers.
Copy-Item (Join-Path $RecompDir "psxrecomp-game.exe") $Toolchain
foreach ($d in @("libgcc_s_seh-1.dll","libstdc++-6.dll","libwinpthread-1.dll")) {
    Copy-Item (Join-Path $MingwBin $d) $Toolchain
}
Copy-Item (Join-Path $RecompTools "compile_overlays.py") $Toolchain
$ToolInc = Join-Path $Toolchain "include"
New-Item -ItemType Directory -Force $ToolInc | Out-Null
Copy-Item (Join-Path $RecompInc "*.h") $ToolInc
$tcMB = "{0:N0}" -f ((Get-ChildItem $Toolchain -Recurse -File | Measure-Object Length -Sum).Sum / 1MB)
Write-Host "Bundled overlay toolchain (embedded python + tcc + recompiler): ~$tcMB MB"

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
