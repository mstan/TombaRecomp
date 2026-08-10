cmake_minimum_required(VERSION 3.20)
project(TombaRecomp C CXX)

set(CMAKE_C_STANDARD 99)
set(CMAKE_CXX_STANDARD 17)

set(PSXRECOMP_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/psxrecomp" CACHE PATH
    "Path to psxrecomp")

include("${PSXRECOMP_ROOT}/runtime/runtime.cmake")

# Newer recompiler builds can write parallel-compilable full_NN.c shards, while
# the framework commit pinned by this repository still writes full.c. Prefer a
# freshly regenerated monolith when present; otherwise consume every shard.
set(TOMBA_GENERATED_MONOLITH
    "${CMAKE_CURRENT_SOURCE_DIR}/generated/SCUS_942.36_full.c")
file(GLOB TOMBA_GENERATED_SHARDS CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/generated/SCUS_942.36_full_*.c")
if(EXISTS "${TOMBA_GENERATED_MONOLITH}")
    set(TOMBA_GENERATED_PRIMARY "${TOMBA_GENERATED_MONOLITH}")
    set(TOMBA_GENERATED_EXTRAS)
elseif(TOMBA_GENERATED_SHARDS)
    list(POP_FRONT TOMBA_GENERATED_SHARDS TOMBA_GENERATED_PRIMARY)
    set(TOMBA_GENERATED_EXTRAS ${TOMBA_GENERATED_SHARDS})
else()
    # Keep configure usable before the first regeneration. The generated-file
    # property in psxrecomp_add_runtime_target allows the path to appear later.
    set(TOMBA_GENERATED_PRIMARY "${TOMBA_GENERATED_MONOLITH}")
    set(TOMBA_GENERATED_EXTRAS)
endif()
set(TOMBA_GENERATED_DISPATCH
    "${CMAKE_CURRENT_SOURCE_DIR}/generated/SCUS_942.36_dispatch.c")

file(GLOB TOMBA_MOD_PLUGIN_SOURCES CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/src/mods/*.c")

psxrecomp_add_runtime_target(psx-runtime
    # The framework's GAME_GENERATED_FULL_C argument is singular. Keep the
    # primary output in that slot and compile any remaining shards through its
    # supported extra-sources list.
    GAME_GENERATED_FULL_C "${TOMBA_GENERATED_PRIMARY}"
    GAME_GENERATED_DISPATCH_C "${TOMBA_GENERATED_DISPATCH}"
    EXTRAS_SOURCES ${TOMBA_GENERATED_EXTRAS} ${TOMBA_MOD_PLUGIN_SOURCES}
    DEBUG_PORT 4470
    WINDOW_TITLE "Tomba! Recompiled"
    DEFAULT_BIOS_PATH "${PSXRECOMP_ROOT}/bios/SCPH1001.BIN"
    DEFAULT_GAME_CONFIG_PATH "game.toml"
    LAUNCHER_BOXART "${CMAKE_SOURCE_DIR}/recomp/launcher/boxart.tga"
)

# The runtime resolves its baked "game.toml" default relative to the
# executable. Keep direct development launches equivalent to packaged builds:
# without these files the executable falls back to "Unknown Game" and cannot
# load Tomba's title metadata or native game options.
foreach(TOMBA_RUNTIME_CONFIG game.toml game_options.toml)
    add_custom_command(TARGET psx-runtime POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${CMAKE_CURRENT_SOURCE_DIR}/${TOMBA_RUNTIME_CONFIG}"
            "$<TARGET_FILE_DIR:psx-runtime>/${TOMBA_RUNTIME_CONFIG}"
        COMMENT "Staging ${TOMBA_RUNTIME_CONFIG} for direct Tomba launches")
endforeach()

# Preload the game-owned catalog. Features remain disabled until selected in
# the launcher, and plugin ids resolve only to implementations compiled above.
set(TOMBA_PRELOADED_MODS "${CMAKE_CURRENT_SOURCE_DIR}/mods/preloaded")
if(EXISTS "${TOMBA_PRELOADED_MODS}/packages")
    add_custom_command(TARGET psx-runtime POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_directory
            "${TOMBA_PRELOADED_MODS}"
            "$<TARGET_FILE_DIR:psx-runtime>/mods"
        COMMENT "Preloading the Tomba mod catalog")
endif()

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
        EXTRAS_SOURCES ${TOMBA_MOD_PLUGIN_SOURCES}
        COSIM
    )
endif()
