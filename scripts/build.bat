@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo HONAERO SENTINEL — VERIFICATION CORE BUILD RUNNER
echo ============================================================

call "C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat"

set CMAKE_BIN="C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"
set NINJA_BIN="C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe"

if not exist build (
    mkdir build
)

echo.
echo [1/3] Configuring CMake with Ninja...
%CMAKE_BIN% -B build -S . -G "Ninja" -DCMAKE_MAKE_PROGRAM=%NINJA_BIN% -DCMAKE_BUILD_TYPE=Release
if %ERRORLEVEL% neq 0 (
    echo [ERROR] CMake configuration failed with code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

echo.
echo [2/3] Building Verification Core Targets...
%CMAKE_BIN% --build build --config Release
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Build failed with code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

echo.
echo [3/3] Running Verification Core Test Suite...
cd build\tests\verification
sentinel_tests.exe
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Tests failed with exit code %ERRORLEVEL%
    cd ..\..\..
    exit /b 1
)
cd ..\..\..

echo.
echo ============================================================
echo BUILD AND TESTS SUCCEEDED (EXIT 0)
echo ============================================================
exit /b 0
