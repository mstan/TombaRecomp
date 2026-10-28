# Merge one shared audio declaration into the existing regional mod staging.
function(tomba_audio_sync_catalog output original)
    set(staged "${CMAKE_CURRENT_BINARY_DIR}/audio-sync-preloaded")
    # Reconfiguration must not keep packages removed by a regional revision.
    # Only our fixed generated staging directory may be replaced.
    cmake_path(IS_PREFIX CMAKE_CURRENT_BINARY_DIR "${staged}" NORMALIZE within_build)
    if(NOT within_build OR "${staged}" STREQUAL "${CMAKE_CURRENT_BINARY_DIR}")
        message(FATAL_ERROR "Audio catalog staging must stay inside the build directory")
    endif()
    file(REMOVE_RECURSE "${staged}")
    if(NOT "${original}" STREQUAL "NONE")
        file(COPY "${original}/" DESTINATION "${staged}")
    endif()
    file(COPY "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/../mods/preloaded/packages/psx.audio.low-latency"
        DESTINATION "${staged}/packages")
    set(${output} "${staged}" PARENT_SCOPE)
endfunction()
