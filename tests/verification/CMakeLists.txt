add_executable(sentinel_tests
    test_verification_core.cpp
)

target_link_libraries(sentinel_tests
    PRIVATE
        sentinel_core
)

set_target_properties(sentinel_tests PROPERTIES
    CXX_STANDARD 20
    CXX_STANDARD_REQUIRED ON
)

if(MSVC)
    target_compile_options(sentinel_tests PRIVATE /EHsc /utf-8)
endif()

add_test(NAME VerificationCoreTests COMMAND sentinel_tests)
