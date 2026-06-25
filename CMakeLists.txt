cmake_minimum_required(VERSION 3.15)
project(apogee LANGUAGES CXX)

find_package(Python COMPONENTS Interpreter Development REQUIRED)
message(STATUS "Using Python ${Python_VERSION} at ${Python_EXECUTABLE}")

find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(apogee
    src/cpp/bindings.cpp
    src/cpp/params_conversion.cpp
    # add other .cpp sources here as needed
)

# make the compiler find params.hpp and params_fields.inc
target_include_directories(apogee PRIVATE "${CMAKE_SOURCE_DIR}/src/cpp")

