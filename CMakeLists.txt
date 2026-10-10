cmake_minimum_required(VERSION 3.20)
project(HonaeroSentinel VERSION 1.0.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Enable CTest
enable_testing()

message(STATUS "============================================================")
message(STATUS "HONAERO SENTINEL — SMART VERIFICATION STUDIO BUILD SYSTEM")
message(STATUS "Target Standard: C++20")
message(STATUS "============================================================")

# Subsystems
add_subdirectory(sdk)
add_subdirectory(services/coverage-worker)
add_subdirectory(tests/verification)
