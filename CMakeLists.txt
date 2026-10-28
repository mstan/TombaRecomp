cmake_minimum_required(VERSION 3.20)
project(TombaRecomp LANGUAGES C CXX)
include(CTest)

set(TOMBA_GEOMETRY_IMPL "HLE" CACHE STRING "Terrain packet implementation: HLE or LLE")
set_property(CACHE TOMBA_GEOMETRY_IMPL PROPERTY STRINGS HLE LLE)
option(TOMBA_GEOMETRY_VALIDATE "Test-only isolated HLE/LLE packet comparison" OFF)
option(TOMBA_GEOMETRY_FLAT_TRIANGLE "Select the native USA flat-triangle batch" ON)
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
option(TOMBA_NATIVE_IDLE_WAIT "Select the audited native frame wait" ON)
set(TOMBA_NATIVE_IDLE_WAIT_SITES "")
if(TOMBA_NATIVE_IDLE_WAIT)
    if(NOT COMMAND psxrecomp_native_idle_wait)
        message(FATAL_ERROR "TOMBA_NATIVE_IDLE_WAIT needs a framework with native wait-policy support")
    endif()
    # SCUS-94236 v_wait at80067D78: one timeout word atsp+16;
    # frame counter800974D4, no MMIO or other counter-dependent exit.
    # Main-loop scratchpad wait at80016588: read-only uint16 counter at
    # 1F8001E8 until it reaches v1. One edge, no calls, stores or MMIO.
    set(TOMBA_NATIVE_IDLE_WAIT_SITES 0x80067DA0 0x80067DEC 0x80016588)
endif()
# Seamless Loading replaces the framework's CD Speed and host-paced Fast
# Loading on Tomba, and 8 MB RAM has no use here; every other framework builtin
# is staged (an exclude list, so new framework mods reach Tomba by default).

psxrecomp_add_game_runtime(psx-runtime
    # ENABLE_NETPLAY_IF_PRESENT
    # NETPLAY_LOBBY_URL "ws://netplay.retcomm.net:8765"
    WINDOW_TITLE "Tomba! Recompiled"
    NATIVE_IDLE_WAIT_SITES ${TOMBA_NATIVE_IDLE_WAIT_SITES}
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
        psx.enhancement.8mb-ram psx.enhancement.cd-speed psx.enhancement.fast-loading
)

target_sources(psx-runtime PRIVATE ${TOMBA_MOD_PLUGIN_SOURCES})
if(CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(psx-runtime PRIVATE
        "$<$<CONFIG:Release>:-ffile-prefix-map=${CMAKE_CURRENT_SOURCE_DIR}=.>"
        "$<$<CONFIG:Release>:-fdebug-prefix-map=${CMAKE_CURRENT_SOURCE_DIR}=.>")
endif()
if(TARGET psx-runtime-pgxp)
    target_sources(psx-runtime-pgxp PRIVATE ${TOMBA_MOD_PLUGIN_SOURCES})
endif()

set(_tomba_geometry_targets psx-runtime)
if(TARGET psx-runtime-pgxp)
    list(APPEND _tomba_geometry_targets psx-runtime-pgxp)
endif()
file(GLOB _tomba_geometry_shards "${CMAKE_CURRENT_SOURCE_DIR}/generated/SCUS_942.36_full_*.c")
set(_tomba_geometry_symbols func_80024EEC func_800251C0 func_800253C8)
set(_tomba_geometry_tag 0x54474801)
if(TOMBA_GEOMETRY_FLAT_TRIANGLE)
    list(APPEND _tomba_geometry_symbols func_80024CFC)
    set(_tomba_geometry_tag 0x54474802)
    set_property(SOURCE src/hle/tomba_geometry_hle.c APPEND PROPERTY
        COMPILE_DEFINITIONS TOMBA_GEOMETRY_FLAT_TRIANGLE=1)
endif()
psxrecomp_select_guest_implementation(
    NAME tomba_geometry IMPLEMENTATION ${TOMBA_GEOMETRY_IMPL}
    TARGETS ${_tomba_geometry_targets}
    GENERATED_SOURCES ${_tomba_geometry_shards}
    SYMBOLS ${_tomba_geometry_symbols}
    HLE_SOURCES "${CMAKE_CURRENT_SOURCE_DIR}/src/hle/tomba_geometry_hle.c"
    REFERENCE_PREFIX tomba_lle_
    SNAPSHOT_TAG ${_tomba_geometry_tag})
if(TOMBA_GEOMETRY_VALIDATE)
    set_property(SOURCE src/hle/tomba_geometry_hle.c APPEND PROPERTY
        COMPILE_DEFINITIONS TOMBA_GEOMETRY_VALIDATE=1)
endif()
message(STATUS "Tomba geometry: ${TOMBA_GEOMETRY_IMPL}, validation=${TOMBA_GEOMETRY_VALIDATE}")

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
    add_executable(tomba-retired-frame-blending-tests
        tests/test_retired_frame_blending.c src/mods/tomba_frame_interpolation_plugin.c)
    target_include_directories(tomba-retired-frame-blending-tests PRIVATE
        "${PSXRECOMP_ROOT}/runtime/include")
    add_test(NAME tomba_retired_frame_blending COMMAND tomba-retired-frame-blending-tests)
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
    add_executable(tomba-camera-anchor-tests tests/test_camera_anchor.c
        src/mods/tomba_widescreen_plugin.c)
    target_include_directories(tomba-camera-anchor-tests PRIVATE
        "${PSXRECOMP_ROOT}/runtime/include")
    add_test(NAME tomba_camera_anchor COMMAND tomba-camera-anchor-tests)
    find_package(Python3 QUIET COMPONENTS Interpreter)
    if(Python3_FOUND)
        add_test(NAME tomba_vwait_contract
            COMMAND "${Python3_EXECUTABLE}"
                "${PSXRECOMP_ROOT}/runtime/tests/native_wait_caller.py"
                --framework "${PSXRECOMP_ROOT}" --cc "${CMAKE_C_COMPILER}"
                --generated "${CMAKE_CURRENT_SOURCE_DIR}/generated"
                --contract "${CMAKE_CURRENT_SOURCE_DIR}/tests/vwait_contract.json")
        set_tests_properties(tomba_vwait_contract PROPERTIES SKIP_RETURN_CODE 77 RUN_SERIAL TRUE)
        add_test(NAME tomba_scratch_wait_contract
            COMMAND "${Python3_EXECUTABLE}"
                "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_scratch_wait_contract.py"
                --framework "${PSXRECOMP_ROOT}" --cc "${CMAKE_C_COMPILER}"
                --generated "${CMAKE_CURRENT_SOURCE_DIR}/generated")
        set_tests_properties(tomba_scratch_wait_contract PROPERTIES SKIP_RETURN_CODE 77 RUN_SERIAL TRUE)
        add_test(NAME tomba_runtime_metadata
            COMMAND "${Python3_EXECUTABLE}"
                "${CMAKE_CURRENT_SOURCE_DIR}/tools/test_runtime_config_metadata.py")
        add_test(NAME tomba_seamless_asset_probe
            COMMAND "${Python3_EXECUTABLE}"
                "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_seamless_asset_probe.py")
    endif()
endif()

if(BUILD_TESTING)
    add_executable(tomba-audio-sync-tests tests/test_audio_sync_mod.c
        src/mods/tomba_audio_sync_plugin.c "${PSXRECOMP_ROOT}/runtime/src/audio_sync.c")
    target_include_directories(tomba-audio-sync-tests PRIVATE "${PSXRECOMP_ROOT}/runtime/include")
    add_test(NAME tomba_audio_sync COMMAND tomba-audio-sync-tests)
    add_executable(tomba-audio-sync-persistence-tests
        tests/test_audio_sync_persistence.cpp
        "${PSXRECOMP_ROOT}/runtime/src/mod_packages.cpp"
        "${PSXRECOMP_ROOT}/runtime/src/mod_media.cpp"
        "${PSXRECOMP_ROOT}/runtime/src/iso_reader.cpp"
        "${PSXRECOMP_ROOT}/runtime/src/cue_sheet.cpp"
        "${PSXRECOMP_ROOT}/runtime/src/crc32.c"
        "${PSXRECOMP_ROOT}/runtime/src/psx_sha256.c")
    target_include_directories(tomba-audio-sync-persistence-tests PRIVATE
        "${PSXRECOMP_ROOT}/runtime/include" "${PSXRECOMP_ROOT}/recompiler/include"
        "${PSXRECOMP_ROOT}/recompiler/lib/toml11")
    target_link_libraries(tomba-audio-sync-persistence-tests PRIVATE chdr-static)
    add_test(NAME tomba_audio_sync_persistence COMMAND tomba-audio-sync-persistence-tests
        "${CMAKE_CURRENT_SOURCE_DIR}/mods/preloaded/packages/psx.audio.low-latency/1.0.1/manifest.toml")
    add_test(NAME tomba_audio_sync_catalog COMMAND "${CMAKE_COMMAND}"
        "-DTOMBA_ROOT=${CMAKE_CURRENT_SOURCE_DIR}"
        "-DSCRATCH=${CMAKE_CURRENT_BINARY_DIR}/audio-catalog-tests"
        -P "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_audio_sync_catalog.cmake")
endif()
