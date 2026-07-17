cmake_minimum_required(VERSION 3.20)
project(TombaRecomp C CXX)

set(CMAKE_C_STANDARD 99)
set(CMAKE_CXX_STANDARD 17)

set(PSXRECOMP_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/psxrecomp" CACHE PATH
    "Path to psxrecomp")

include("${PSXRECOMP_ROOT}/runtime/runtime.cmake")

set(TOMBA_GENERATED_FULL
    "${CMAKE_CURRENT_SOURCE_DIR}/generated/SCUS_942.36_full.c")
set(TOMBA_GENERATED_DISPATCH
    "${CMAKE_CURRENT_SOURCE_DIR}/generated/SCUS_942.36_dispatch.c")

psxrecomp_add_runtime_target(psx-runtime
    GAME_GENERATED_FULL_C "${TOMBA_GENERATED_FULL}"
    GAME_GENERATED_DISPATCH_C "${TOMBA_GENERATED_DISPATCH}"
    DEBUG_PORT 4470
    WINDOW_TITLE "Tomba! Recompiled"
    DEFAULT_BIOS_PATH "${PSXRECOMP_ROOT}/bios/SCPH1001.BIN"
    DEFAULT_GAME_CONFIG_PATH "game.toml"
)

# Shared recomp-ui Dear ImGui launcher. Wires in the PSX-themed launcher UI
# (see main.cpp RECOMP_LAUNCHER gate) instead of the framework's default RmlUi
# launcher. recomp-ui is a real git submodule (github.com/mstan/recomp-ui,
# pinned via the recomp-ui gitlink); locally it is a directory junction to the
# working checkout so builds stay offline and reproducible like everything else.
include("${CMAKE_SOURCE_DIR}/recomp-ui/recomp_ui.cmake")
recomp_target_launcher_ui(psx-runtime
    BOXART "${CMAKE_SOURCE_DIR}/recomp/launcher/boxart.tga"
    PAD    "${CMAKE_SOURCE_DIR}/recomp/launcher/pad.tga"
    BRAND  "${CMAKE_SOURCE_DIR}/recomp/launcher/brand.tga"
)

# First-divergence co-sim oracle build (COSIM_ORACLE.md): clean, deterministic,
# PSX_NO_DEBUG_TOOLS + PSX_COSIM. Two of these (one normal, one PSX_FORCE_INTERP=1)
# are cycle-lockstepped by tools/cosim.py to prove Tomba's compiled backend matches
# the interpreter under the new timing model (regression check). Only built on
# explicit request (-DPSX_BUILD_COSIM=ON) to keep normal game builds lean.
if(PSX_BUILD_COSIM)
    psxrecomp_add_runtime_target(psx-cosim
        GAME_GENERATED_FULL_C "${TOMBA_GENERATED_FULL}"
        GAME_GENERATED_DISPATCH_C "${TOMBA_GENERATED_DISPATCH}"
        WINDOW_TITLE "Tomba-cosim"
        DEFAULT_BIOS_PATH "${PSXRECOMP_ROOT}/bios/SCPH1001.BIN"
        DEFAULT_GAME_CONFIG_PATH "game.toml"
        COSIM
    )
endif()
