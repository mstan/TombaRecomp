cmake_minimum_required(VERSION 3.20)
project(TombaRecomp LANGUAGES C CXX)
include(CTest)

set(TOMBA_GEOMETRY_IMPL "LLE" CACHE STRING "Terrain packet implementation: HLE or LLE")
set_property(CACHE TOMBA_GEOMETRY_IMPL PROPERTY STRINGS HLE LLE)
option(TOMBA_GEOMETRY_VALIDATE "Test-only isolated HLE/LLE packet comparison" OFF)
if(NOT TOMBA_GEOMETRY_IMPL MATCHES "^(HLE|LLE)$")
    message(FATAL_ERROR "TOMBA_GEOMETRY_IMPL must be HLE or LLE")
endif()
if(TOMBA_GEOMETRY_VALIDATE AND NOT TOMBA_GEOMETRY_IMPL STREQUAL "HLE")
    message(FATAL_ERROR "TOMBA_GEOMETRY_VALIDATE requires HLE")
endif()

set(PSXRECOMP_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/psxrecomp" CACHE PATH
    "Path to psxrecomp")

# --- Opt-in product surfaces (OFF by default in the framework) -------------
# Scaffold prompts / flags fill these. Without recomp-ui, PSX_RECOMP_UI is OFF.
# Release players use a prebuilt executable and supply their disc for data.
# The legacy compiler wizard remains an explicit developer build option.
# recomp-ui submodule present (PSX_RECOMP_UI defaults ON).
# Full netplay UI — enable after adding recomp-ui + testing:
# if(EXISTS "${PSXRECOMP_ROOT}/lib/recomp-net/CMakeLists.txt")
#     set(PSX_NETPLAY ON CACHE BOOL "…" FORCE)
# endif()
option(PSX_SETUP_WIZARD "Enable the legacy developer code-generation wizard" OFF)
include("${PSXRECOMP_ROOT}/runtime/runtime.cmake")

set(TOMBA_CODEGEN_SETUP_SOURCES)
if(PSX_SETUP_WIZARD)
    list(APPEND TOMBA_CODEGEN_SETUP_SOURCES
        "${CMAKE_CURRENT_SOURCE_DIR}/codegen_setup.c"
        "${PSXRECOMP_ROOT}/host/psxrecomp_codegen_host.c")
endif()

file(GLOB TOMBA_MOD_PLUGIN_SOURCES CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/src/mods/*.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/mods/*.cpp")
set(TOMBA_PRELOADED_MODS "${CMAKE_CURRENT_SOURCE_DIR}/mods/preloaded")
# Seamless Loading replaces the framework's CD Speed and host-paced Fast
# Loading on Tomba, so only the remaining framework builtins are staged.
set(PSX_BUILTIN_MOD_ALLOWLIST
    psx.enhancement.pgxp
    psx.presentation.bezel)

psxrecomp_add_game_runtime(psx-runtime
    # ENABLE_NETPLAY_IF_PRESENT
    # NETPLAY_LOBBY_URL "ws://netplay.retcomm.net:8765"
    WINDOW_TITLE "Tomba! Recompiled"
    DEFAULT_GAME_CONFIG_PATH "game.toml"
    MAX_PLAYERS 1
    LAUNCHER_BOXART "${CMAKE_CURRENT_SOURCE_DIR}/launcher_assets/img/boxart.tga"
    GEN_MARKER "generated/SCUS_942.36_dispatch.c"
    GEN_FULL_GLOB "generated/SCUS_942.36_full_*.c"
    CODEGEN_SETUP_SOURCES ${TOMBA_CODEGEN_SETUP_SOURCES}
    PRELOADED_MODS_DIR "${TOMBA_PRELOADED_MODS}"
    # Tomba provides this generic renderer plugin through its own package so
    # the launcher has one HD pack feature and title-specific instructions.
    EXCLUDE_BUILTIN_MODS psx.enhancement.hd-textures
)

target_sources(psx-runtime PRIVATE ${TOMBA_MOD_PLUGIN_SOURCES})
if(TARGET psx-runtime-pgxp)
    target_sources(psx-runtime-pgxp PRIVATE ${TOMBA_MOD_PLUGIN_SOURCES})
endif()

# Rename only the maintained original definitions. The dispatch table binds
# the native batch symbols in HLE builds; LLE compiles the unmodified source.
# Locate by symbol rather than relying on the current codegen shard number.
if(TOMBA_GEOMETRY_IMPL STREQUAL "HLE")
    file(GLOB _tomba_geometry_shards "${CMAKE_CURRENT_SOURCE_DIR}/generated/SCUS_942.36_full_*.c")
    foreach(_tomba_geometry_shard IN LISTS _tomba_geometry_shards)
        file(READ "${_tomba_geometry_shard}" _tomba_geometry_text)
        foreach(_tomba_geometry_entry 80024EEC 800251C0 800253C8)
            if(_tomba_geometry_text MATCHES "void func_${_tomba_geometry_entry}\\(")
                set_property(SOURCE "${_tomba_geometry_shard}" APPEND PROPERTY COMPILE_DEFINITIONS
                    "func_${_tomba_geometry_entry}=tomba_lle_${_tomba_geometry_entry}")
                set(_tomba_found_${_tomba_geometry_entry} TRUE)
            endif()
        endforeach()
    endforeach()
    foreach(_tomba_geometry_entry 80024EEC 800251C0 800253C8)
        if(NOT _tomba_found_${_tomba_geometry_entry})
            message(FATAL_ERROR "Missing original geometry routine ${_tomba_geometry_entry}; run codegen")
        endif()
    endforeach()
endif()
foreach(_tomba_geometry_target psx-runtime psx-runtime-pgxp)
    if(TARGET ${_tomba_geometry_target})
        target_sources(${_tomba_geometry_target} PRIVATE src/hle/tomba_geometry_build.c)
        target_compile_definitions(${_tomba_geometry_target} PRIVATE TOMBA_GEOMETRY_IMPL="${TOMBA_GEOMETRY_IMPL}")
        if(TOMBA_GEOMETRY_IMPL STREQUAL "HLE")
            target_sources(${_tomba_geometry_target} PRIVATE src/hle/tomba_geometry_hle.c)
            if(TOMBA_GEOMETRY_VALIDATE)
                set_property(SOURCE src/hle/tomba_geometry_hle.c APPEND PROPERTY COMPILE_DEFINITIONS TOMBA_GEOMETRY_VALIDATE=1)
            endif()
        endif()
    endif()
endforeach()
message(STATUS "Tomba geometry: ${TOMBA_GEOMETRY_IMPL}, validation=${TOMBA_GEOMETRY_VALIDATE}")
if(TOMBA_GEOMETRY_IMPL STREQUAL "HLE")
    # TGH1: atomic packet batches cannot resume an old mid-instruction state.
    set_property(SOURCE "${PSXRECOMP_ROOT}/runtime/src/boot_state.c" APPEND PROPERTY
        COMPILE_DEFINITIONS PSX_SAVESTATE_IMPL_TAG=0x54474801u)
endif()

# Stage configs beside the binary for direct launches. Gate on EXISTS so a
# setup-host zip that forgot an optional file still links successfully.
foreach(TOMBA_RUNTIME_CONFIG game.toml game_options.toml)
    if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/${TOMBA_RUNTIME_CONFIG}")
        add_custom_command(TARGET psx-runtime POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                "${CMAKE_CURRENT_SOURCE_DIR}/${TOMBA_RUNTIME_CONFIG}"
                "$<TARGET_FILE_DIR:psx-runtime>/${TOMBA_RUNTIME_CONFIG}"
            COMMENT "Staging ${TOMBA_RUNTIME_CONFIG} for direct Tomba launches"
            VERBATIM)
    endif()
endforeach()

if(BUILD_TESTING)
    add_executable(tomba-fmv-skip-tests tests/test_fmv_skip.c
        src/mods/tomba_skip_fmv_plugin.c)
    target_include_directories(tomba-fmv-skip-tests PRIVATE
        "${PSXRECOMP_ROOT}/runtime/include")
    add_test(NAME tomba_fmv_skip COMMAND tomba-fmv-skip-tests)

    # The audit fixture includes the real planner but no running game. Drop
    # the unreferenced installation/dispatch services from this small target.
    if(CMAKE_C_COMPILER_ID MATCHES "GNU|Clang" AND NOT MSVC)
        add_library(tomba-seamless-request-fixture SHARED tests/seamless_request_fixture.c)
        add_executable(tomba-seamless-request-tests tests/test_seamless_requests.c)
        foreach(target tomba-seamless-request-fixture tomba-seamless-request-tests)
            target_include_directories(${target} PRIVATE "${PSXRECOMP_ROOT}/runtime/include")
            target_compile_options(${target} PRIVATE -O2 -ffunction-sections -fdata-sections)
            if(APPLE)
                target_link_options(${target} PRIVATE -Wl,-dead_strip)
            else()
                target_link_options(${target} PRIVATE -Wl,--gc-sections)
            endif()
        endforeach()
        add_test(NAME tomba_seamless_requests COMMAND tomba-seamless-request-tests)
    endif()
    add_library(tomba-seamless-reverb-fixture SHARED tests/seamless_reverb_native_fixture.c)
    # Seamless Loading preparation against an owner-supplied disc image:
    # -DTOMBA_TEST_DISC=<path to the SCUS-94236 data-track .bin>.
    add_executable(tomba-seamless-prepare-tests
        tests/test_seamless_prepare.cpp src/mods/tomba_seamless_prepare.cpp
        "${PSXRECOMP_ROOT}/runtime/src/mod_resident.cpp"
        "${PSXRECOMP_ROOT}/runtime/src/psx_sha256.c")
    target_compile_features(tomba-seamless-prepare-tests PRIVATE cxx_std_17)
    target_include_directories(tomba-seamless-prepare-tests PRIVATE
        src/mods "${PSXRECOMP_ROOT}/runtime/include")
    set(TOMBA_TEST_DISC "" CACHE FILEPATH "Original SCUS-94236 .bin for disc tests")
    if(TOMBA_TEST_DISC)
        add_test(NAME tomba_seamless_prepare
            COMMAND tomba-seamless-prepare-tests "${TOMBA_TEST_DISC}"
                    "${CMAKE_CURRENT_BINARY_DIR}/seamless-test-cache")
    endif()
    add_executable(tomba-adaptive-tests tests/test_adaptive_widescreen.c
        "${PSXRECOMP_ROOT}/runtime/src/psx_ram_geometry.c")
    target_include_directories(tomba-adaptive-tests PRIVATE "${PSXRECOMP_ROOT}/runtime/include")
    add_test(NAME tomba_adaptive_widescreen COMMAND tomba-adaptive-tests)
    find_package(Python3 QUIET COMPONENTS Interpreter)
    if(Python3_FOUND)
        add_test(NAME tomba_runtime_metadata
            COMMAND "${Python3_EXECUTABLE}"
                "${CMAKE_CURRENT_SOURCE_DIR}/tools/test_runtime_config_metadata.py")
        add_test(NAME tomba_seamless_asset_probe
            COMMAND "${Python3_EXECUTABLE}"
                "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_seamless_asset_probe.py")
    endif()
endif()
