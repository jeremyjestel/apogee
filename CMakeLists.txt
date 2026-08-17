cmake_minimum_required(VERSION 3.15)
project(apogee LANGUAGES CXX)

find_package(Python COMPONENTS Interpreter Development REQUIRED)
message(STATUS "Using Python ${Python_VERSION} at ${Python_EXECUTABLE}")

find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(apogee
    src/cpp/bindings.cpp
    src/cpp/analysis/radar_range.cpp
    src/cpp/logging.cpp
    src/cpp/run_sim.cpp
    src/cpp/systems/motion_system.cpp
)

# Make the compiler find the public simulation headers.
target_include_directories(apogee PRIVATE "${CMAKE_SOURCE_DIR}/src/cpp")

target_compile_features(apogee PRIVATE cxx_std_20)

if(MSVC)
    # Serialize access to compiler PDB files during parallel builds.
    target_compile_options(apogee PRIVATE /FS)
endif()
