cmake_minimum_required(VERSION 3.20)

# ============================================================
# Sentinel Core Verification SDK Library
# ============================================================

set(SENTINEL_SDK_SOURCES
    src/analysis/ast_analyzer.cpp
    src/dependency/dependency_analyzer.cpp
    src/harness/harness_generator.cpp
    src/comparator/scalar_comparator.cpp
    src/compiler/gcc_compiler.cpp
    src/coverage/gcov_provider.cpp
    src/mcdc/mcdc_expression.cpp
    src/mcdc/mcdc_evaluator.cpp
    src/mcdc/mcdc_gap_advisor.cpp
    src/traceability/traceability_engine.cpp
    src/evidence/sha256.cpp
    src/evidence/evidence_record.cpp
    src/capsule/verification_capsule.cpp
    src/common/process.cpp
)

add_library(sentinel_core STATIC ${SENTINEL_SDK_SOURCES})

target_include_directories(sentinel_core PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

target_compile_features(sentinel_core PUBLIC cxx_std_20)

if(MSVC)
    target_compile_options(sentinel_core PRIVATE /W4 /EHsc /permissive- /utf-8 /D_CRT_SECURE_NO_WARNINGS)
else()
    target_compile_options(sentinel_core PRIVATE -Wall -Wextra -Wpedantic)
endif()

# Check for Clang LibTooling
find_package(Clang CONFIG QUIET)
find_package(LLVM CONFIG QUIET)
if(Clang_FOUND AND LLVM_FOUND)
    message(STATUS "Clang LibTooling development packages FOUND. Enabling native Clang AST frontends.")
    target_compile_definitions(sentinel_core PUBLIC SENTINEL_HAS_CLANG_LIBTOOLING=1)
    target_link_libraries(sentinel_core PUBLIC clangTooling clangASTMatchers clangAST clangBasic clangFrontend)
else()
    message(STATUS "NOTE: Clang development libraries (LLVM/Clang LibTooling) not found on host.")
    message(STATUS "      Sentinel is configured with the Built-in C-Subset Deterministic AST Parser.")
    message(STATUS "      To enable native Clang LibTooling, install LLVM and set Clang_DIR.")
endif()

# ============================================================
# Sentinel CLI Binary
# ============================================================

add_executable(sentinel src/cli/main.cpp)
target_link_libraries(sentinel PRIVATE sentinel_core)
target_compile_features(sentinel PRIVATE cxx_std_20)

if(MSVC)
    target_compile_options(sentinel PRIVATE /EHsc /utf-8)
endif()
