cmake_minimum_required(VERSION 3.15)
project(apogee LANGUAGES CXX)

find_package(Eigen3 CONFIG REQUIRED)

# Keep simulation logic reusable without depending on Python bindings.
add_library(apogee_core STATIC
    src/cpp/analysis/radar_range.cpp
    src/cpp/controls/control_system.cpp
    src/cpp/estimation/estimation_system.cpp
    src/cpp/guidance/guidance_system.cpp
    src/cpp/motion/models/drag.cpp
    src/cpp/motion/models/gravity.cpp
    src/cpp/motion/models/ground_motion.cpp
    src/cpp/motion/models/thrust.cpp
    src/cpp/motion/motion_system.cpp
    src/cpp/logging/logging.cpp
    src/cpp/math/dsp/convolve.cpp
    src/cpp/math/dsp/window.cpp
    src/cpp/math/geometry/boresight_angle.cpp
    src/cpp/math/geometry/los_occluded.cpp
    src/cpp/run_sim.cpp
    src/cpp/scenarios/default_scenario.cpp
    src/cpp/simulation/scenario_runtime.cpp
    src/cpp/sensors/radar/models/radar_range_equation.cpp
    src/cpp/sensors/radar/models/radar_returns.cpp
    src/cpp/sensors/radar/models/radar_processing.cpp
    src/cpp/sensors/radar/radar_system.cpp
    src/cpp/sensors/radar/models/range_doppler_map.cpp
    src/cpp/sensors/sensor_system.cpp
)

target_include_directories(apogee_core PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/src/cpp")
target_link_libraries(apogee_core PUBLIC Eigen3::Eigen)
target_compile_features(apogee_core PUBLIC cxx_std_20)
set_target_properties(apogee_core PROPERTIES POSITION_INDEPENDENT_CODE ON)

option(APOGEE_BUILD_PYTHON "Build the Python extension" ON)
if(APOGEE_BUILD_PYTHON)
    find_package(Python COMPONENTS Interpreter Development REQUIRED)
    message(STATUS "Using Python ${Python_VERSION} at ${Python_EXECUTABLE}")
    find_package(pybind11 CONFIG REQUIRED)

    # Preserve the public extension name while keeping its target focused on bindings.
    pybind11_add_module(apogee src/cpp/pybind/bindings.cpp)
    target_link_libraries(apogee PRIVATE apogee_core)
    if(MSVC)
        target_compile_options(apogee PRIVATE /FS)
    endif()
endif()

include(CTest)
if(BUILD_TESTING)
    add_executable(apogee_window_tests
        tests/cpp/test_window.cpp
        src/cpp/math/dsp/window.cpp)
    target_include_directories(apogee_window_tests PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src/cpp")
    target_link_libraries(apogee_window_tests PRIVATE Eigen3::Eigen)
    target_compile_features(apogee_window_tests PRIVATE cxx_std_20)
    add_test(NAME apogee_window_tests COMMAND apogee_window_tests)

    # Exercise logging independently while simulation subsystems are unfinished.
    add_executable(apogee_logging_tests
        tests/cpp/test_logging.cpp
        src/cpp/logging/logging.cpp)
    target_include_directories(apogee_logging_tests PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src/cpp")
    target_link_libraries(apogee_logging_tests PRIVATE Eigen3::Eigen)
    target_compile_features(apogee_logging_tests PRIVATE cxx_std_20)
    add_test(NAME apogee_logging_tests COMMAND apogee_logging_tests)

    add_executable(apogee_core_tests tests/cpp/test_simulation.cpp)
    target_link_libraries(apogee_core_tests PRIVATE apogee_core)
    add_test(NAME apogee_core_tests COMMAND apogee_core_tests)

    add_executable(apogee_coords_tests tests/cpp/test_coords.cpp)
    target_link_libraries(apogee_coords_tests PRIVATE apogee_core)
    add_test(NAME apogee_coords_tests COMMAND apogee_coords_tests)
endif()

if(MSVC)
    # Serialize access to compiler PDB files during parallel builds.
    target_compile_options(apogee_core PRIVATE /FS)
endif()
