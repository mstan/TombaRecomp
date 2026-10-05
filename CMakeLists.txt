cmake_minimum_required(VERSION 3.20)
project(TombaRecomp LANGUAGES C CXX)
include(CTest)

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
)

target_sources(psx-runtime PRIVATE ${TOMBA_MOD_PLUGIN_SOURCES})
if(TARGET psx-runtime-pgxp)
    target_sources(psx-runtime-pgxp PRIVATE ${TOMBA_MOD_PLUGIN_SOURCES})
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
    add_executable(tomba-seamless-prepare-tests
        tests/test_seamless_prepare.cpp src/mods/tomba_seamless_prepare.cpp
        "${PSXRECOMP_ROOT}/runtime/src/psx_sha256.c")
    target_compile_features(tomba-seamless-prepare-tests PRIVATE cxx_std_17)
    target_include_directories(tomba-seamless-prepare-tests PRIVATE "${PSXRECOMP_ROOT}/runtime/include")
    add_executable(tomba-adaptive-tests tests/test_adaptive_widescreen.c)
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
