cmake_minimum_required(VERSION 3.15)
project(apogee LANGUAGES CXX)

find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(apogee
    src/cpp/bindings.cpp
)