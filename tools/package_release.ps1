param(
    [string]$Version = "v0.2.0-alpha",
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

# Regenerate the game's C BEFORE building. The recompiler emits the settings
# persistence init-store hook (from game_options.toml) and the widescreen sites
# at regen time; the runtime build below just compiles generated/*.c. A stale
# generated/ would ship without the settings-persistence feature.
$RecompDir = Resolve-Path (Join-Path $Root "..\psxrecomp\recompiler\build")
cmake --build $RecompDir --target psxrecomp-game -j $env:NUMBER_OF_PROCESSORS
& (Join-Path $RecompDir "psxrecomp-game.exe") --config (Join-Path $Root "game.toml")
if ($LASTEXITCODE -ne 0) { throw "game regen failed" }

cmake -S $Root -B $BuildPath -G Ninja -DCMAKE_BUILD_TYPE=Release -DPSX_DEBUG_TOOLS=OFF -DPSX_LAUNCHER=ON
cmake --build $BuildPath -j $env:NUMBER_OF_PROCESSORS

if (Test-Path $StageRoot) {
    Remove-Item -Recurse -Force $StageRoot
}
New-Item -ItemType Directory -Force $Stage | Out-Null
New-Item -ItemType Directory -Force (Join-Path $Stage "saves") | Out-Null

Copy-Item (Join-Path $BuildPath "psx-runtime.exe") (Join-Path $Stage "TombaRecomp.exe")
Copy-Item (Join-Path $Root "README.md") $Stage
Copy-Item (Join-Path $Root "LICENSE") $Stage
if (Test-Path (Join-Path $Root "RELEASE_NOTES.md")) {
    Copy-Item (Join-Path $Root "RELEASE_NOTES.md") $Stage
}

# Launcher assets (RML + fonts + images). The PSX_LAUNCHER build stages these
# next to the exe via a cmake POST_BUILD copy_directory of
# psxrecomp/runtime/launcher/assets, so they live flat under $BuildPath
# (launcher.rml, fonts/, img/). The launcher loads them relative to the exe
# dir; a release without them shows a blank/broken launcher. Assert + copy.
$LauncherRml = Join-Path $BuildPath "launcher.rml"
if (-not (Test-Path $LauncherRml)) {
    throw "Launcher assets missing at $BuildPath (no launcher.rml) -- was the build configured with -DPSX_LAUNCHER=ON?"
}
Copy-Item $LauncherRml $Stage
foreach ($dir in @("fonts","img")) {
    $src = Join-Path $BuildPath $dir
    if (-not (Test-Path $src)) { throw "Launcher asset dir missing: $src" }
    Copy-Item -Recurse -Force $src (Join-Path $Stage $dir)
}
$fontCount = (Get-ChildItem (Join-Path $Stage "fonts") -Filter *.ttf -ErrorAction SilentlyContinue).Count
$imgCount  = (Get-ChildItem (Join-Path $Stage "img") -Filter *.png -ErrorAction SilentlyContinue).Count
Write-Host "Bundled launcher assets: launcher.rml + $fontCount font(s) + $imgCount image(s)"

# Player-facing game.toml: same effective runtime settings as the dev config,
# minus dev-only sections ([recompiler]/[audit] inputs, the overlay
# autocompile command that needs a local python+gcc toolchain). Players can
# edit the [runtime] section post-install; the comments document the knobs.
@"
[game]
name = "Tomba!"
id = "SCUS-94236"
exe = "tomba/SCUS_942.36"
disc = "tomba/tomba.cue"
load_address = "0x80010000"
entry_pc = "0x8006B58C"
text_size = "0x00088000"
stack_base = "0x801FFFF0"

# Required block; used only by the developer recompiler tool, not at runtime.
[recompiler]
seeds = "seeds/ghidra_funcs.txt"
bios_thunks = "seeds/tomba_bios_thunks.txt"
out_dir = "generated"

# ---- Player-adjustable options ------------------------------------------
# Edit, save, and restart TombaRecomp.exe to apply.
[runtime]
window_title = "Tomba! Recompiled"
memcard_dir = "saves"

# Disc read speed: "1x" (authentic), "2x", "4x", or "instant" (fastest).
disc_speed = "instant"

# Skip the PlayStation BIOS boot logos (true) or watch them (false).
fast_boot  = false

# Speed through in-game loading screens at full host speed (recommended).
turbo_loads = true

# Overlay cache: keeps converted native code for game areas in the cache
# folder, and records newly visited areas into overlay_captures.json so
# your own cache grows as you play. Keep that file private - it contains
# game code from your disc (see README).
overlay_cache = true

# ---- Visual quality -----------------------------------------------------
[video]
# supersampling: render the game at this multiple of native resolution and
# downsample, for higher detail and anti-aliased edges. 1 = native PSX look,
# 2 = recommended, 3-4 = sharper (needs a faster CPU to hold full speed).
supersampling = 2
# antialiasing: smooth (linear) scaling to the window. false = sharp pixels.
antialiasing  = true
# texture_filtering: "nearest" = native PSX look; "bilinear" = smooths
# textures and 2D backgrounds.
texture_filtering = "nearest"
# renderer: "opengl" = hardware GPU renderer (default; keeps heavy areas at
# full speed). "software" = CPU renderer (automatic fallback if the GPU
# renderer can't start). You can also change this in the launcher.
renderer = "opengl"
# auto_skip_fmv: skip full-motion videos (e.g. the opening movie). When on, a
# video is skipped the instant it starts, jumping straight to the next screen.
# Off by default; also toggleable in the launcher (Settings -> "Skip FMVs").
auto_skip_fmv = false
# aspect_ratio: "4:3" (native, default) or "16:9" (EXPERIMENTAL widescreen). Also
# toggleable in the launcher (Settings -> Widescreen), which overrides this.
aspect_ratio = "4:3"

# ---- Controller ---------------------------------------------------------
# default_analog: present a DualShock/analog pad by default so the left stick
# gives variable run speed (the D-pad / keyboard still move you). Per-player
# toggle in the launcher. deadzone: analog stick dead-band (0..32767; ~12000 =
# 37%), also adjustable in the launcher (Settings -> Controller).
[controller]
default_analog = true
deadzone = 12000

# ---- Widescreen (experimental 16:9) -------------------------------------
# These hooks keep the 16:9 picture correct (wider field of view, HUD/sprites at
# the right proportions, backdrops filled). Inert at 4:3. Addresses are specific
# to Tomba! (USA, SCUS-94236) and must match the build the cache was made for.
[widescreen]
sprite_tag_funcs   = ["0x8005E08C"]
sprite_anchor_addr = "0x1F800070"
hud_sprt_squash    = true

[widescreen.cull]
bias_sites    = ["0x80022E78", "0x80022F94", "0x80022FE8", "0x80023068"]
range_sites   = ["0x80022E80", "0x80022F9C", "0x80022FF0", "0x80023070"]
a1_sites      = ["0x80022C34", "0x80022D68", "0x800230FC"]
auto_screen_x = true

[widescreen.backdrop]
x_sites        = ["0x801217B4", "0x8012196C"]
unsquash_funcs = ["0x8004DB3C"]
"@ | Set-Content -Encoding ASCII (Join-Path $Stage "game.toml")

# Tomba's native OPTION-screen settings declaration (the RAM addresses the
# settings-persistence feature reads/writes). Required for in-game settings
# (text speed, sound, vibration, screen adjust) to persist between launches.
Copy-Item (Join-Path $Root "game_options.toml") $Stage

# Prebuilt overlay cache: native code for the game areas contributed so far.
# The cache is namespaced per backend/arch/codegen-version:
#   gcc/<arch-abi>/cg<N>/<entry8>_<crc8>.dll (+ .ranges)
# and the loader scans it by that exact path, so the subtree must be preserved
# (a flat copy bundles nothing / won't load). Ship .dll + .ranges only (the
# _patched.c intermediates are build artifacts); skip the reserved sljit/
# namespace (it has no on-disk blobs — sljit re-JITs in process).
$CacheSrc = Join-Path $Root "build-stable/cache/SCUS-94236"
if (Test-Path $CacheSrc) {
    $CacheDst = Join-Path $Stage "cache/SCUS-94236"
    $cacheFiles = Get-ChildItem $CacheSrc -Recurse -File -Include *.dll,*.ranges |
        Where-Object { $_.FullName -notmatch '[\\/]sljit[\\/]' }
    foreach ($f in $cacheFiles) {
        $rel  = $f.FullName.Substring($CacheSrc.Length).TrimStart('\','/')
        $dest = Join-Path $CacheDst $rel
        New-Item -ItemType Directory -Force (Split-Path $dest) | Out-Null
        Copy-Item $f.FullName $dest
    }
    $dllCount = (Get-ChildItem $CacheDst -Recurse -Filter *.dll).Count
    Write-Host "Bundled overlay cache: $dllCount native overlay DLL(s)"
} else {
    Write-Warning "No overlay cache found at $CacheSrc - releasing without bundled cache"
}

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

This package does not include the Tomba disc, the PlayStation BIOS, save
data, or any game assets - you supply those from your own collection, and
TombaRecomp asks for them one at a time (each dialog says which one it
wants). The executable and the cache folder contain statically recompiled
(machine-translated) builds of the game's code, the same distribution model
used by other static recompilation projects such as N64: Recompiled.

First launch:
1. Run TombaRecomp.exe. A launcher window opens.
2. In the launcher, set your PlayStation BIOS: select your legally obtained
   SCPH1001.BIN (a 512 KB file dumped from your own console).
3. Set the game disc: select your legally obtained Tomba! (USA, SCUS-94236)
   disc image.
4. Adjust any options you like (renderer, supersampling, screen look,
   controller), then press Launch. Your choices are remembered next time.

Disc image formats:
- .cue + .bin (preferred - pick the .cue)
- .bin
- .iso

The selected BIOS path is saved in bios.cfg and the selected disc path is saved
in disc.cfg next to the executable. Delete those files if you want to pick
different files later.

If the disc header or game ID does not match SCUS-94236, TombaRecomp will show
a warning and try to run the image anyway. Boot may fail if the image is the
wrong game, the wrong region, or corrupt.

Options such as loading-screen turbo and disc speed can be changed in
game.toml (the [runtime] section) with any text editor.

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
Compress-Archive -Path (Join-Path $Stage "*") -DestinationPath $ZipPath -Force

Write-Host "Wrote $ZipPath"
