cmake_minimum_required(VERSION 3.20)
project(TombaRecomp CXX C)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_C_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(PSXRECOMP_ROOT ${CMAKE_SOURCE_DIR}/psxrecomp)
include(${PSXRECOMP_ROOT}/runner/runner.cmake)

include(FetchContent)

# GLFW
FetchContent_Declare(glfw
    GIT_REPOSITORY https://github.com/glfw/glfw.git
    GIT_TAG        3.3.8
)
set(GLFW_BUILD_DOCS OFF CACHE BOOL "" FORCE)
set(GLFW_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(GLFW_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(glfw)

# GLAD (from framework)
add_library(glad STATIC ${PSXRECOMP_GLAD_SOURCES})
target_include_directories(glad PUBLIC ${PSXRECOMP_GLAD_INCLUDE_DIRS})

# fmt
FetchContent_Declare(fmt
    GIT_REPOSITORY https://github.com/fmtlib/fmt.git
    GIT_TAG        10.1.1
)
FetchContent_MakeAvailable(fmt)

add_executable(TombaRecomp
    ${PSXRECOMP_RUNNER_SOURCES}
    extras.cpp
    generated/SCUS_942.36_full.c
    generated/SCUS_942.36_dispatch.c
)

target_include_directories(TombaRecomp PRIVATE
    ${PSXRECOMP_RUNNER_INCLUDE_DIRS}
    ${CMAKE_SOURCE_DIR}
    ${CMAKE_SOURCE_DIR}/generated
)

target_link_libraries(TombaRecomp PRIVATE glfw glad fmt)

if(WIN32)
    target_link_libraries(TombaRecomp PRIVATE opengl32 winmm comdlg32 ws2_32)
endif()

# Copy keyconfig.ini to output dir
add_custom_command(TARGET TombaRecomp POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${PSXRECOMP_ROOT}/runner/assets/keyconfig.ini"
        "$<TARGET_FILE_DIR:TombaRecomp>/keyconfig.ini"
    COMMENT "Copying keyconfig.ini to output directory"
)
