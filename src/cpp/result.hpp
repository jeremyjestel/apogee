#pragma once

#include <vector>
#include <string>

struct DataSeries
{
    std::string name;         
    std::string unit;         
    std::vector<double> values;
};

struct SimulationData
{
    std::string name;
    std::vector<double> times_s;
    std::vector<DataSeries> outputs;
};
    
//Analysis for plots like range vs snr and other system characherization
struct Analysis2D
{
    std::string name;
    DataSeries x;
    std::vector<DataSeries> y;
};

struct Analysis3D
{
    std::string name;
    DataSeries x;
    DataSeries y;
    DataSeries z;
};

struct Result
{
    SimulationData simulation;
    std::vector<Analysis2D> analysis_2d;
    std::vector<Analysis3D> analysis_3d;
};