cmake_minimum_required(VERSION 3.15)
project(apogee LANGUAGES CXX)

find_package(Eigen3 CONFIG REQUIRED)

# Keep simulation logic reusable without depending on Python bindings.
add_library(apogee_core STATIC
    src/cpp/analysis/radar_range.cpp
    src/cpp/logging.cpp
    src/cpp/math/radar_range_equation.cpp
    src/cpp/run_sim.cpp
    src/cpp/scenarios/default/default_scenario.cpp
    src/cpp/simulation/scenario_runtime.cpp
    src/cpp/systems/ground_motion.cpp
    src/cpp/systems/motion_system.cpp
    src/cpp/systems/orbital_motion.cpp
    src/cpp/systems/radar_system.cpp
    src/cpp/systems/range_doppler_map.cpp
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
    pybind11_add_module(apogee src/cpp/bindings.cpp)
    target_link_libraries(apogee PRIVATE apogee_core)
    if(MSVC)
        target_compile_options(apogee PRIVATE /FS)
    endif()
endif()

include(CTest)
if(BUILD_TESTING)
    add_executable(apogee_core_tests tests/cpp/test_simulation.cpp)
    target_link_libraries(apogee_core_tests PRIVATE apogee_core)
    add_test(NAME apogee_core_tests COMMAND apogee_core_tests)
endif()

if(MSVC)
    # Serialize access to compiler PDB files during parallel builds.
    target_compile_options(apogee_core PRIVATE /FS)
endif()
