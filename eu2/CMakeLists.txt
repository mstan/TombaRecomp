cmake_minimum_required(VERSION 3.20)
project(TombiEU2Prototype LANGUAGES C CXX)
get_filename_component(TOMBA_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/.." ABSOLUTE)
set(PSXRECOMP_ROOT "${TOMBA_ROOT}/psxrecomp" CACHE PATH "Shared framework")
set(RECOMP_UI_ROOT "${TOMBA_ROOT}/recomp-ui" CACHE PATH "Shared launcher")
set(PSX_SETUP_WIZARD OFF CACHE BOOL "No developer wizard" FORCE)
set(PSXRECOMP_REQUIRE_GAME_C ON CACHE BOOL "Require verified native boot" FORCE)
include("${PSXRECOMP_ROOT}/runtime/runtime.cmake")
option(TOMBI_EU2_SEAMLESS "Verified EU2 adapter for shared EU resident loader" OFF)
option(TOMBI_EU2_PLAYER_RELEASE "Portable player executable without debug tools" OFF)
option(TOMBI_EU2_GEOMETRY_VALIDATE "Private original-vs-HLE differential checks" OFF)
if(TOMBI_EU2_PLAYER_RELEASE AND PSX_DEBUG_TOOLS)
    message(FATAL_ERROR "Player releases must use PSX_DEBUG_TOOLS=OFF")
endif()
set(input_mods "${CMAKE_CURRENT_BINARY_DIR}/input-preloaded")
file(COPY "${TOMBA_ROOT}/mods/preloaded/packages/tombi.enhancement.low-input-latency"
    DESTINATION "${input_mods}/packages")
set(eu2_mods "${input_mods}")
if(TOMBI_EU2_SEAMLESS)
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    execute_process(COMMAND "${Python3_EXECUTABLE}" -I -B
        "${CMAKE_CURRENT_SOURCE_DIR}/seamless_profile.py" COMMAND_ERROR_IS_FATAL ANY)
    set(geometry_args)
    if(TOMBI_EU2_GEOMETRY_VALIDATE)
        if(TOMBI_EU2_PLAYER_RELEASE)
            message(FATAL_ERROR "Original geometry references are private tests only")
        endif()
        set(geometry_args --references)
    endif()
    execute_process(COMMAND "${Python3_EXECUTABLE}" -I -B
        "${CMAKE_CURRENT_SOURCE_DIR}/geometry_profile.py" ${geometry_args} COMMAND_ERROR_IS_FATAL ANY)
    set(eu2_mods "${TOMBA_ROOT}/build-eu2-seamless/generated/mods")
    # Wait for Language Confirmation binds the original release's selector;
    # revisions.py drops the package for Rev 1, which is not verified.
    execute_process(COMMAND "${Python3_EXECUTABLE}" -I -B -c
        "import sys;sys.path.insert(0,r'${CMAKE_CURRENT_SOURCE_DIR}');from revisions import active;print(active())"
        OUTPUT_VARIABLE eu2_selector_revision OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ERROR_IS_FATAL ANY)
    if(eu2_selector_revision STREQUAL "original")
        execute_process(COMMAND "${Python3_EXECUTABLE}" -I -B "${CMAKE_CURRENT_SOURCE_DIR}/boot_profile.py" COMMAND_ERROR_IS_FATAL ANY)
    endif()
    execute_process(COMMAND "${Python3_EXECUTABLE}" -I -B
        "${CMAKE_CURRENT_SOURCE_DIR}/widescreen_profile.py" COMMAND_ERROR_IS_FATAL ANY)
endif()
psxrecomp_add_game_runtime(tombi-eu2
    WINDOW_TITLE "Tombi! (Europe, SCES-01331)"
    DEFAULT_GAME_CONFIG_PATH "game.toml"
    VERSION_FILE "${TOMBA_ROOT}/VERSION"
    MAX_PLAYERS 1
    # SCES-01331 shares the SCES-01330 cover artwork.
    LAUNCHER_BOXART "${TOMBA_ROOT}/eu/launcher_assets/img/boxart.tga"
    GEN_MARKER "${TOMBA_ROOT}/build-eu2/generated/SCES_013.31_dispatch.c"
    GEN_FULL_GLOB "${TOMBA_ROOT}/build-eu2/generated/SCES_013.31_full_*.c"
    PRELOADED_MODS_DIR "${eu2_mods}"
    EXCLUDE_BUILTIN_MODS psx.enhancement.8mb-ram psx.enhancement.cd-speed
        psx.enhancement.fast-loading psx.enhancement.hd-textures)
set_target_properties(tombi-eu2 PROPERTIES OUTPUT_NAME "TombiRecompEU2")
if(TOMBI_EU2_SEAMLESS)
    set(eu2_generated "${TOMBA_ROOT}/build-eu2-seamless/generated")
    if(eu2_selector_revision STREQUAL "original")
        target_sources(tombi-eu2 PRIVATE "${TOMBA_ROOT}/eu/boot.c")
    endif()
    set(eu2_widescreen "${eu2_generated}/widescreen")
    target_sources(tombi-eu2 PRIVATE "${eu2_generated}/eu2_loader.c"
        "${eu2_generated}/eu2_geometry.c"
        "${eu2_widescreen}/eu_widescreen.c"
        "${eu2_widescreen}/tomba_widescreen_plugin.c"
        "${eu2_widescreen}/tomba_widescreen_residency.c"
        "${eu2_widescreen}/tomba_widescreen_scripts.c"
        "${TOMBA_ROOT}/src/mods/tomba_dispatch.c"
        "${TOMBA_ROOT}/src/mods/tomba_hybrid_controller_plugin.c"
        "${TOMBA_ROOT}/src/mods/tomba_seamless_prepare.cpp")
    if(TOMBI_EU2_GEOMETRY_VALIDATE)
        target_sources(tombi-eu2 PRIVATE "${eu2_generated}/eu2_geometry_reference.c")
        set_source_files_properties("${eu2_generated}/eu2_geometry.c" PROPERTIES COMPILE_DEFINITIONS TOMBA_GEOMETRY_VALIDATE=1)
    endif()
    target_include_directories(tombi-eu2 PRIVATE "${eu2_generated}" "${eu2_widescreen}"
        "${TOMBA_ROOT}/eu/seamless" "${TOMBA_ROOT}/src/mods")
    set_source_files_properties("${TOMBA_ROOT}/src/mods/tomba_seamless_prepare.cpp" PROPERTIES
        COMPILE_DEFINITIONS "TOMBA_SEAMLESS_CATALOG_HEADER=\"${eu2_generated}/eu_catalog.inc\";TOMBA_SEAMLESS_PACK_FORMAT=\"sces01331-five-languages-gam-v1\"")
    if(NOT TOMBI_EU2_PLAYER_RELEASE)
    include(CTest)
    add_executable(tombi-eu2-widescreen-tests "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_widescreen_identity.c"
        "${eu2_widescreen}/eu_widescreen.c")
    execute_process(COMMAND "${Python3_EXECUTABLE}" -I -B -c
        "import sys; sys.path.insert(0,r'${CMAKE_CURRENT_SOURCE_DIR}'); from revisions import active; print(active())"
        OUTPUT_VARIABLE eu2_revision OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ERROR_IS_FATAL ANY)
    if(eu2_revision STREQUAL "rev1")
        target_compile_definitions(tombi-eu2-widescreen-tests PRIVATE TOMBI_EU2_REV1=1)
    endif()
    target_include_directories(tombi-eu2-widescreen-tests PRIVATE
        "${eu2_widescreen}" "${PSXRECOMP_ROOT}/runtime/include")
    add_test(NAME tombi_eu2_widescreen_identity
        COMMAND tombi-eu2-widescreen-tests "${TOMBA_ROOT}/disc/eu2")
    add_executable(tombi-eu2-hd-install-tests "${TOMBA_ROOT}/eu/tests/test_hd_install.cpp"
        "${PSXRECOMP_ROOT}/runtime/src/texture_pack_install.cpp"
        "${PSXRECOMP_ROOT}/runtime/src/duckstation_texture_pack.cpp")
    target_include_directories(tombi-eu2-hd-install-tests PRIVATE "${PSXRECOMP_ROOT}/runtime/include" "${PSXRECOMP_ROOT}/recompiler/lib/toml11")
    target_link_libraries(tombi-eu2-hd-install-tests PRIVATE psx_texture_image_decode Threads::Threads)
    add_executable(tombi-eu2-loader-tests "${TOMBA_ROOT}/eu/seamless/tests.c")
    target_include_directories(tombi-eu2-loader-tests PRIVATE "${eu2_generated}"
        "${TOMBA_ROOT}/eu/seamless" "${TOMBA_ROOT}/src/mods" "${PSXRECOMP_ROOT}/runtime/include")
    target_compile_definitions(tombi-eu2-loader-tests PRIVATE
        TOMBI_TEST_LOADER_SOURCE="eu2_loader.c" TOMBI_TEST_ADDRESS=eu2_address)
    target_compile_options(tombi-eu2-loader-tests PRIVATE -O2 -UNDEBUG -ffunction-sections -fdata-sections)
    target_link_options(tombi-eu2-loader-tests PRIVATE -Wl,--gc-sections)
    add_test(NAME tombi_eu2_loader COMMAND tombi-eu2-loader-tests)
    if(eu2_selector_revision STREQUAL "original")
        add_executable(tombi-eu2-language-confirmation-tests tests/test_language_confirmation.cpp
            "${TOMBA_ROOT}/eu/boot.c")
        target_include_directories(tombi-eu2-language-confirmation-tests PRIVATE
            "${PSXRECOMP_ROOT}/runtime/include" "${eu2_generated}")
        target_compile_options(tombi-eu2-language-confirmation-tests PRIVATE -UNDEBUG)
        add_test(NAME tombi_eu2_language_confirmation
            COMMAND tombi-eu2-language-confirmation-tests "${TOMBA_ROOT}/disc/eu2")
    endif()
    endif()
endif()

target_sources(tombi-eu2 PRIVATE "${TOMBA_ROOT}/src/mods/tomba_low_input_latency_plugin.c")
