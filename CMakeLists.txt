cmake_minimum_required(VERSION 3.15)
project(apogee LANGUAGES CXX)

find_package(Python COMPONENTS Interpreter Development REQUIRED)
message(STATUS "Using Python ${Python_VERSION} at ${Python_EXECUTABLE}")

find_package(pybind11 CONFIG REQUIRED)
find_package(Eigen3 CONFIG REQUIRED)

# Compile the C++ simulation and bindings into one importable Python module.
pybind11_add_module(apogee
    src/cpp/bindings.cpp
    src/cpp/analysis/radar_range.cpp
    src/cpp/logging.cpp
    src/cpp/math/relative_kinematics.cpp
    src/cpp/math/radar_range_equation.cpp
    src/cpp/run_sim.cpp
    src/cpp/scenarios/default/default_scenario.cpp
    src/cpp/systems/motion_system.cpp
    src/cpp/systems/radar_system.cpp
    src/cpp/systems/range_doppler_map.cpp
)

# Make the compiler find the public simulation headers.
target_include_directories(apogee PRIVATE "${CMAKE_SOURCE_DIR}/src/cpp")

# Inherit Eigen's header path so C++ files can include <Eigen/Dense>.
target_link_libraries(apogee PRIVATE Eigen3::Eigen)

target_compile_features(apogee PRIVATE cxx_std_20)

if(MSVC)
    # Serialize access to compiler PDB files during parallel builds.
    target_compile_options(apogee PRIVATE /FS)
endif()
