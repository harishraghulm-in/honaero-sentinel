add_executable(sentinel-coverage-worker
    src/main.cpp
)

target_link_libraries(sentinel-coverage-worker
    PRIVATE
        sentinel_core
)

set_target_properties(sentinel-coverage-worker PROPERTIES
    CXX_STANDARD 20
    CXX_STANDARD_REQUIRED ON
)
