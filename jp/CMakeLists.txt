cmake_minimum_required(VERSION 3.20)
project(OreTombaJapan LANGUAGES C CXX)
get_filename_component(TOMBA_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/.." ABSOLUTE)
set(PSXRECOMP_ROOT "${TOMBA_ROOT}/psxrecomp" CACHE PATH "Shared framework")
set(RECOMP_UI_ROOT "${TOMBA_ROOT}/recomp-ui" CACHE PATH "Shared launcher")
set(PSX_SETUP_WIZARD OFF CACHE BOOL "No developer wizard" FORCE)
set(PSXRECOMP_REQUIRE_GAME_C ON CACHE BOOL "Verified native boot required" FORCE)
include("${PSXRECOMP_ROOT}/runtime/runtime.cmake")
# The enhanced build carries every Japanese feature: Seamless Loading and FMV
# Skip (checked loader/movie bindings) and Widescreen (checked shared-renderer
# adapter, jp/widescreen_profile.py).
option(TOMBA_JP_ENHANCEMENTS "Seamless Loading, FMV Skip and Widescreen" OFF)
set(TOMBA_JP_GENERATED_DIR "${TOMBA_ROOT}/build-jp/generated" CACHE PATH "Japanese boot code directory")
set(input_mods "${CMAKE_CURRENT_BINARY_DIR}/input-preloaded")
file(COPY "${TOMBA_ROOT}/mods/preloaded/packages/tombi.enhancement.low-input-latency"
    DESTINATION "${input_mods}/packages")
set(jp_mods "${input_mods}")
if(TOMBA_JP_ENHANCEMENTS)
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    get_filename_component(jp_generated "${TOMBA_JP_GENERATED_DIR}" DIRECTORY)
    execute_process(COMMAND "${Python3_EXECUTABLE}" -I -B "${CMAKE_CURRENT_SOURCE_DIR}/seamless_profile.py" --output "${jp_generated}" COMMAND_ERROR_IS_FATAL ANY)
    execute_process(COMMAND "${Python3_EXECUTABLE}" -I -B "${CMAKE_CURRENT_SOURCE_DIR}/fmv_profile.py" --output "${jp_generated}" COMMAND_ERROR_IS_FATAL ANY)
    execute_process(COMMAND "${Python3_EXECUTABLE}" -I -B "${TOMBA_ROOT}/eu/seamless_catalog.py" --variant jp --output "${jp_generated}" COMMAND_ERROR_IS_FATAL ANY)
    execute_process(COMMAND "${Python3_EXECUTABLE}" -I -B "${CMAKE_CURRENT_SOURCE_DIR}/widescreen_profile.py" --output "${jp_generated}" COMMAND_ERROR_IS_FATAL ANY)
    set(jp_mods "${CMAKE_CURRENT_SOURCE_DIR}/mods")
endif()
psxrecomp_add_game_runtime(tomba-jp
    PGXP
    WINDOW_TITLE "Ore! Tomba"
    DEFAULT_GAME_CONFIG_PATH "game.toml"
    VERSION_FILE "${TOMBA_ROOT}/VERSION"
    MAX_PLAYERS 1
    LAUNCHER_BOXART "${CMAKE_CURRENT_SOURCE_DIR}/launcher_assets/img/boxart.tga"
    GEN_MARKER "${TOMBA_JP_GENERATED_DIR}/SLPS_011.44_dispatch.c"
    GEN_FULL_GLOB "${TOMBA_JP_GENERATED_DIR}/SLPS_011.44_full_*.c"
    PRELOADED_MODS_DIR "${jp_mods}"
    EXCLUDE_BUILTIN_MODS psx.enhancement.8mb-ram psx.enhancement.cd-speed
        psx.enhancement.fast-loading)
set_target_properties(tomba-jp PROPERTIES OUTPUT_NAME "TombaRecompJP")
if(TOMBA_JP_ENHANCEMENTS)
    set(jp_ws "${jp_generated}/adapter")
    target_sources(tomba-jp PRIVATE "${jp_ws}/eu_widescreen.c"
        "${jp_ws}/tomba_widescreen_plugin.c" "${jp_ws}/tomba_widescreen_residency.c"
        "${jp_ws}/tomba_widescreen_scripts.c" "${TOMBA_ROOT}/src/mods/tomba_dispatch.c")
    target_include_directories(tomba-jp PRIVATE "${jp_ws}" "${TOMBA_ROOT}/src/mods")
    target_sources(tomba-jp PRIVATE "${jp_generated}/jp_loader.c" "${TOMBA_ROOT}/src/mods/tomba_seamless_prepare.cpp" "${TOMBA_ROOT}/src/mods/tomba_skip_fmv_plugin.c")
    target_include_directories(tomba-jp PRIVATE "${jp_generated}" "${TOMBA_ROOT}/eu/seamless" "${TOMBA_ROOT}/src/mods")
    set_source_files_properties("${TOMBA_ROOT}/src/mods/tomba_seamless_prepare.cpp" PROPERTIES COMPILE_DEFINITIONS "TOMBA_SEAMLESS_CATALOG_HEADER=\"${jp_generated}/eu_catalog.inc\";TOMBA_SEAMLESS_PACK_FORMAT=\"slps01144-gam-v1\"")
    if(PSX_DEBUG_TOOLS)
        add_executable(tomba-jp-loader-tests "${jp_generated}/jp_loader_tests.c")
        target_include_directories(tomba-jp-loader-tests PRIVATE "${jp_generated}" "${TOMBA_ROOT}/eu/seamless" "${TOMBA_ROOT}/src/mods" "${PSXRECOMP_ROOT}/runtime/include")
        target_compile_options(tomba-jp-loader-tests PRIVATE -O2 -UNDEBUG -ffunction-sections -fdata-sections)
        target_link_options(tomba-jp-loader-tests PRIVATE -Wl,--gc-sections)
        add_executable(tomba-jp-prepare-tests "${TOMBA_ROOT}/tests/test_seamless_prepare.cpp" "${TOMBA_ROOT}/src/mods/tomba_seamless_prepare.cpp" "${PSXRECOMP_ROOT}/runtime/src/mod_resident.cpp" "${PSXRECOMP_ROOT}/runtime/src/psx_sha256.c")
        target_include_directories(tomba-jp-prepare-tests PRIVATE "${TOMBA_ROOT}/src/mods" "${PSXRECOMP_ROOT}/runtime/include")
        target_compile_features(tomba-jp-prepare-tests PRIVATE cxx_std_17)
        target_compile_definitions(tomba-jp-prepare-tests PRIVATE TOMBA_SEAMLESS_CATALOG_HEADER="${jp_generated}/eu_catalog.inc")
    endif()
endif()
# The shared launcher already embeds the UTF-8 application manifest
# (recomp-ui windows/recomp_utf8.manifest); a second manifest resource would
# collide with it at link time.

target_sources(tomba-jp PRIVATE "${TOMBA_ROOT}/src/mods/tomba_low_input_latency_plugin.c")
