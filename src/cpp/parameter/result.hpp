#pragma once

#include <vector>
#include <string>

struct DataSeries
{
    std::string name;         
    std::string unit;         
    std::vector<double> values;
};

struct SimulationDataSeries2D
{
    std::string entity_name;
    std::string name;
    std::string unit;
    std::vector<double> values;
};

struct VectorDataSeries
{
    std::string entity_name;
    std::string name;
    std::string unit;
    std::vector<double> x;
    std::vector<double> y;
    std::vector<double> z;
};

struct SimulationData2D
{
    std::string name;
    std::vector<double> times_s;
    std::vector<SimulationDataSeries2D> outputs;
};

struct SimulationData3D
{
    std::string name;
    std::vector<double> times_s;
    std::vector<VectorDataSeries> outputs;
};
    
//Analysis for plots like range vs snr and other system characterization

struct Analysis2D
{
    std::string name;
    DataSeries x;
    std::vector<DataSeries> y;
};

// for 3d data
struct Analysis3D
{
    std::string name;
    DataSeries x;
    DataSeries y;
    DataSeries z;
};

struct Result
{
    SimulationData2D simulation_2d;
    SimulationData3D simulation_3d;
    std::vector<Analysis2D> analysis_2d;
    std::vector<Analysis3D> analysis_3d;
};
