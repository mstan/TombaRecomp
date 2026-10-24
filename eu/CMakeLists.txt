cmake_minimum_required(VERSION 3.20)
project(TombiEUPrototype LANGUAGES C CXX)
get_filename_component(TOMBA_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/.." ABSOLUTE)
set(PSXRECOMP_ROOT "${TOMBA_ROOT}/psxrecomp" CACHE PATH "PSXRecomp framework")
set(RECOMP_UI_ROOT "${TOMBA_ROOT}/recomp-ui" CACHE PATH "Launcher")
set(PSX_SETUP_WIZARD OFF CACHE BOOL "No developer wizard" FORCE)
set(PSXRECOMP_REQUIRE_GAME_C ON CACHE BOOL "Require original EU generated code" FORCE)
include("${PSXRECOMP_ROOT}/runtime/runtime.cmake")
option(TOMBI_PC_FEATURES "Build isolated EU PC feature target" OFF)
option(TOMBI_SEAMLESS "Build isolated EU seamless development target" OFF)
option(TOMBI_PLAYER_RELEASE "Build relocatable player package without developer paths" OFF)
if(TOMBI_SEAMLESS)
    set(TOMBI_PC_FEATURES ON)
endif()
set(tombi_target tombi-eu)
set(tombi_mods NONE)
set(tombi_exclude)
set(tombi_config "${CMAKE_CURRENT_SOURCE_DIR}/game.toml")
if(TOMBI_PC_FEATURES)
    option(TOMBI_GEOMETRY_VALIDATE "Local-only original EU/HLE differential comparison" OFF)
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    execute_process(COMMAND "${Python3_EXECUTABLE}" -I -B
        "${CMAKE_CURRENT_SOURCE_DIR}/widescreen_profile.py"
        COMMAND_ERROR_IS_FATAL ANY)
    set(tombi_target tombi-eu-pc)
    set(tombi_mods "${CMAKE_CURRENT_SOURCE_DIR}/mods/preloaded")
    set(tombi_exclude psx.enhancement.hd-textures)
    set(tombi_config "${CMAKE_CURRENT_SOURCE_DIR}/pc.toml")
    set(PSX_BUILTIN_MOD_ALLOWLIST psx.enhancement.pgxp psx.presentation.bezel)
endif()
if(TOMBI_SEAMLESS)
    set(tombi_target tombi-eu-seamless)
    set(tombi_config "${CMAKE_CURRENT_SOURCE_DIR}/seamless/game.toml")
    set(tombi_mods "${CMAKE_CURRENT_BINARY_DIR}/seamless-preloaded")
    file(COPY "${CMAKE_CURRENT_SOURCE_DIR}/mods/preloaded/packages/"
        DESTINATION "${tombi_mods}/packages")
    file(COPY "${CMAKE_CURRENT_SOURCE_DIR}/seamless/mods/packages/"
        DESTINATION "${tombi_mods}/packages")
endif()
if(TOMBI_PLAYER_RELEASE)
    set(tombi_config "game.toml")
    file(COPY "${CMAKE_CURRENT_SOURCE_DIR}/release/mods/packages/"
        DESTINATION "${tombi_mods}/packages")
endif()
psxrecomp_add_game_runtime(${tombi_target}
    WINDOW_TITLE "Tombi! Europe Rev 1"
    DEFAULT_GAME_CONFIG_PATH "${tombi_config}"
    VERSION_FILE "${CMAKE_CURRENT_SOURCE_DIR}/VERSION"
    MAX_PLAYERS 1
    LAUNCHER_BOXART "${CMAKE_CURRENT_SOURCE_DIR}/launcher_assets/img/boxart.tga"
    GEN_MARKER "${TOMBA_ROOT}/build-eu-prototype/generated/SCES_013.30_dispatch.c"
    GEN_FULL_GLOB "${TOMBA_ROOT}/build-eu-prototype/generated/SCES_013.30_full_*.c"
    PRELOADED_MODS_DIR "${tombi_mods}"
    EXCLUDE_BUILTIN_MODS ${tombi_exclude})
if(TOMBI_PLAYER_RELEASE)
    # Cover diagnostics/__FILE__ and debug metadata in owned runtime sources.
    target_compile_options(${tombi_target} PRIVATE
        "-ffile-prefix-map=${TOMBA_ROOT}=."
        "-fdebug-prefix-map=${TOMBA_ROOT}=.")
    target_link_options(${tombi_target} PRIVATE -Wl,--strip-all)
endif()
if(TOMBI_PC_FEATURES)
    set_target_properties(${tombi_target} PROPERTIES OUTPUT_NAME "Tombi_EU_PC")
    set(tombi_ws "${TOMBA_ROOT}/build-eu-seamless/generated/widescreen")
    target_sources(${tombi_target} PRIVATE
        "${tombi_ws}/eu_widescreen.c"
        "${tombi_ws}/tomba_widescreen_plugin.c"
        "${tombi_ws}/tomba_widescreen_residency.c"
        "${tombi_ws}/tomba_widescreen_scripts.c"
        "${TOMBA_ROOT}/src/mods/tomba_dispatch.c")
    target_include_directories(${tombi_target} PRIVATE
        "${tombi_ws}" "${TOMBA_ROOT}/src/mods")
    if(TOMBI_SEAMLESS)
        set_target_properties(${tombi_target} PROPERTIES OUTPUT_NAME "Tombi_EU_Seamless")
        if(TOMBI_PLAYER_RELEASE)
            set_target_properties(${tombi_target} PROPERTIES OUTPUT_NAME "TombiRecompEU")
        endif()
        target_sources(${tombi_target} PRIVATE seamless/loader.c boot.c
            geometry.c
            "${TOMBA_ROOT}/src/mods/tomba_seamless_prepare.cpp")
        if(TOMBI_GEOMETRY_VALIDATE)
            target_sources(${tombi_target} PRIVATE "${TOMBA_ROOT}/build-eu-seamless/generated/eu_geometry_reference.c")
            set_source_files_properties(geometry.c PROPERTIES COMPILE_DEFINITIONS TOMBA_GEOMETRY_VALIDATE=1)
        endif()
        target_include_directories(${tombi_target} PRIVATE
            "${TOMBA_ROOT}/src/mods" "${TOMBA_ROOT}/build-eu-seamless/generated")
        target_compile_definitions(${tombi_target} PRIVATE
            TOMBA_SEAMLESS_CATALOG_HEADER="${TOMBA_ROOT}/build-eu-seamless/generated/eu_catalog.inc"
            TOMBA_SEAMLESS_PACK_FORMAT="sces01330-rev1-five-languages-gam-v1")
        add_executable(tombi-loader-tests seamless/tests.c)
        target_include_directories(tombi-loader-tests PRIVATE
            "${TOMBA_ROOT}/src/mods" "${PSXRECOMP_ROOT}/runtime/include"
            "${TOMBA_ROOT}/build-eu-seamless/generated")
        target_compile_options(tombi-loader-tests PRIVATE -O2 -UNDEBUG -ffunction-sections -fdata-sections)
        target_link_options(tombi-loader-tests PRIVATE -Wl,--gc-sections)
    endif()
    # Address-free host policy; guest widescreen hooks use checked EU adapters.
    target_sources(${tombi_target} PRIVATE
        "${TOMBA_ROOT}/src/mods/tomba_hybrid_controller_plugin.c"
        "${TOMBA_ROOT}/src/mods/tomba_skip_fmv_plugin.c")
    if(TARGET ${tombi_target}-pgxp)
        target_sources(${tombi_target}-pgxp PRIVATE
            "${TOMBA_ROOT}/src/mods/tomba_hybrid_controller_plugin.c"
            "${TOMBA_ROOT}/src/mods/tomba_skip_fmv_plugin.c")
    endif()
    include(CTest)
    if(BUILD_TESTING)
        add_executable(tombi-widescreen-identity-tests tests/test_widescreen_identity.c
            "${tombi_ws}/eu_widescreen.c")
        target_include_directories(tombi-widescreen-identity-tests PRIVATE
            "${tombi_ws}" "${PSXRECOMP_ROOT}/runtime/include")
        add_test(NAME tombi_widescreen_identity COMMAND tombi-widescreen-identity-tests "${TOMBA_ROOT}/disc")
        add_executable(tombi-hd-install-tests tests/test_hd_install.cpp
            "${PSXRECOMP_ROOT}/runtime/src/texture_pack_install.cpp"
            "${PSXRECOMP_ROOT}/runtime/src/duckstation_texture_pack.cpp")
        target_include_directories(tombi-hd-install-tests PRIVATE "${PSXRECOMP_ROOT}/runtime/include" "${PSXRECOMP_ROOT}/recompiler/lib/toml11")
        target_link_libraries(tombi-hd-install-tests PRIVATE psx_texture_image_decode Threads::Threads)
        add_executable(tombi-host-sha-tests tests/test_host_sha256.cpp "${PSXRECOMP_ROOT}/runtime/src/psx_sha256.c")
        target_include_directories(tombi-host-sha-tests PRIVATE "${PSXRECOMP_ROOT}/runtime/include")
        target_compile_options(tombi-host-sha-tests PRIVATE -UNDEBUG)
        add_test(NAME tombi_host_sha256 COMMAND tombi-host-sha-tests)
        add_executable(tombi-language-confirmation-tests tests/test_language_confirmation.cpp boot.c)
        target_include_directories(tombi-language-confirmation-tests PRIVATE
            "${PSXRECOMP_ROOT}/runtime/include" "${TOMBA_ROOT}/build-eu-seamless/generated")
        target_compile_options(tombi-language-confirmation-tests PRIVATE -UNDEBUG)
        add_test(NAME tombi_language_confirmation COMMAND tombi-language-confirmation-tests "${TOMBA_ROOT}/disc")
        add_executable(tombi-controller-reconnect-tests tests/test_controller_reconnect.cpp)
        target_include_directories(tombi-controller-reconnect-tests PRIVATE "${PSXRECOMP_ROOT}/runtime/include")
        target_link_libraries(tombi-controller-reconnect-tests PRIVATE ${PSX_SDL_LIBRARIES})
        add_test(NAME tombi_controller_reconnect COMMAND tombi-controller-reconnect-tests)
        add_executable(tombi-fast-forward-tests "${PSXRECOMP_ROOT}/runtime/tests/test_fast_forward.c")
        target_include_directories(tombi-fast-forward-tests PRIVATE "${PSXRECOMP_ROOT}/runtime/include")
        target_compile_options(tombi-fast-forward-tests PRIVATE -UNDEBUG)
        if(NOT WIN32)
            target_link_libraries(tombi-fast-forward-tests PRIVATE m)
        endif()
        add_test(NAME tombi_fast_forward COMMAND tombi-fast-forward-tests)
        add_executable(tombi-vsync-tests "${PSXRECOMP_ROOT}/runtime/tests/test_launcher_vsync.c")
        target_include_directories(tombi-vsync-tests PRIVATE "${PSXRECOMP_ROOT}/runtime/include")
        target_compile_options(tombi-vsync-tests PRIVATE -UNDEBUG)
        add_test(NAME tombi_launcher_vsync COMMAND tombi-vsync-tests)
        add_executable(tombi-spu-shadow-tests
            "${PSXRECOMP_ROOT}/runtime/tests/test_spu_shadow_normalization.c"
            "${PSXRECOMP_ROOT}/runtime/src/spu_shadow.c"
            "${PSXRECOMP_ROOT}/runtime/src/audio_shadow.c")
        target_include_directories(tombi-spu-shadow-tests PRIVATE "${PSXRECOMP_ROOT}/runtime/include")
        target_compile_options(tombi-spu-shadow-tests PRIVATE -UNDEBUG)
        if(NOT WIN32)
            target_link_libraries(tombi-spu-shadow-tests PRIVATE m)
        endif()
        add_test(NAME tombi_spu_shadow COMMAND tombi-spu-shadow-tests)
        add_executable(tombi-hybrid-tests tests/test_hybrid_controller.c
            "${TOMBA_ROOT}/src/mods/tomba_hybrid_controller_plugin.c")
        target_include_directories(tombi-hybrid-tests PRIVATE
            "${PSXRECOMP_ROOT}/runtime/include")
        if(MSVC)
            target_compile_options(tombi-hybrid-tests PRIVATE /UNDEBUG)
        else()
            target_compile_options(tombi-hybrid-tests PRIVATE -UNDEBUG)
        endif()
        add_test(NAME tombi_hybrid_controller COMMAND tombi-hybrid-tests)
        add_executable(tombi-fmv-tests "${TOMBA_ROOT}/tests/test_fmv_skip.c"
            "${TOMBA_ROOT}/src/mods/tomba_skip_fmv_plugin.c")
        target_include_directories(tombi-fmv-tests PRIVATE
            "${PSXRECOMP_ROOT}/runtime/include")
        add_test(NAME tombi_fmv_skip COMMAND tombi-fmv-tests)
    endif()
else()
    set_target_properties(${tombi_target} PROPERTIES OUTPUT_NAME "Tombi_EU_Prototype")
endif()
# Original EU profiles supply guest addresses; host policies remain shared.
