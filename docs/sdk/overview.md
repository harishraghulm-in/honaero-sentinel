# HonAero Sentinel — Verification Core C/C++ SDK

## 1. Overview
The verification core contains the native analysis, AST extraction, and instrumentation interfaces designed for embedded cross-compilers and native verification harnesses.

## 2. Directory Layout
```
sdk/
├── include/
│   └── sentinel/
│       ├── harness.h       # Test harness macros and assertions
│       ├── stubs.h         # Deterministic mock & stub primitives
│       └── types.h         # Portable verification types
├── src/
│   ├── harness.c           # Harness runner runtime
│   └── stubs.c             # Call counter and order trackers
├── tests/                  # Native verification unit tests
└── CMakeLists.txt          # Portable CMake build configuration
```

## 3. Integration with Embedded Toolchains
While the studio initially compiles using GCC and GCOV, the SDK CMake configuration allows cross-compilation for embedded targets (ARM Cortex-R, PowerPC, Clang, and future HIL test beds).

