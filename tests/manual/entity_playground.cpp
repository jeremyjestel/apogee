#include <iomanip>
#include <iostream>
#include <random>
#include <stdexcept>
#include <string_view>
#include <vector>

#include "core/entity.hpp"
#include "controls/control_system.hpp"
#include "guidance/guidance_system.hpp"
#include "guidance/models/point_nav.hpp"
#include "guidance/models/prop_nav.hpp"
#include "math/constants.hpp"
#include "math/coords.hpp"
#include "math/geometry/los_occluded.hpp"
#include "motion/motion_system.hpp"

namespace
{
    using namespace apogee;

    // Edit these initial states for your experiment. Positions and velocities are ECI.
    std::vector<Entity> make_test_entities()
    {
        Entity missile;
        missile.id = 1;
        missile.key = "test_missile";
        missile.type = "missile";
        missile.active = true; // Set false to disable this entity in system/pipeline tests.
        missile.blast_radius = 50.0;
        missile.size_radius = 2.0;
        missile.kinematics.pos_m = lla2eci(0.0, 0.0, 200'000.0, 0.0);
        missile.kinematics.vel_mps = Vec3{ 0.0, 1'500.0, 0.0 };
        missile.guidance.guidance_gain = 0.5;
        missile.controls.time_constant_s = 0.1;
        missile.guidance.target_index = 1; // Index in the vector below, not entity ID.

        Entity satellite;
        satellite.id = 2;
        satellite.key = "test_satellite";
        satellite.type = "satellite";
        satellite.size_radius = 5.0;
        satellite.kinematics.pos_m = lla2eci(0.0, 2.0, 500'000.0, 0.0);
        satellite.kinematics.vel_mps = Vec3{ 0.0, 7'500.0, 0.0 };

        Entity interceptor;
        interceptor.id = 3;
        interceptor.key = "test_interceptor";
        interceptor.type = "interceptor";
        interceptor.blast_radius = 25.0;
        interceptor.size_radius = 1.0;
        interceptor.kinematics.pos_m = lla2eci(1.0, -1.0, 100'000.0, 0.0);
        interceptor.kinematics.vel_mps = Vec3{ 0.0, 2'000.0, 0.0 };
        interceptor.guidance.target_index = 0;

        return { missile, satellite, interceptor };
    }

    void print_state(const Entity &entity)
    {
        std::cout << entity.key << '\n'
                  << "  active:             " << std::boolalpha << entity.active << '\n'
                  << "  blast radius (m):   " << entity.blast_radius << '\n'
                  << "  size radius (m):    " << entity.size_radius << '\n'
                  << "  position ECI (m):   " << entity.kinematics.pos_m.transpose() << '\n'
                  << "  velocity (m/s):     " << entity.kinematics.vel_mps.transpose() << '\n'
                  << "  speed (m/s):        " << entity.kinematics.vel_mps.norm() << '\n'
                  << "  altitude (m):       " << entity.kinematics.pos_m.norm() - constants::earth_radius_m << '\n'
                  << "  command (m/s^2):    " << entity.guidance.accel_command.transpose() << '\n'
                  << "  control (m/s^2):    " << entity.controls.accel_actual.transpose() << '\n'
                  << "  net accel (m/s^2):  " << entity.kinematics.accel_mps2.transpose() << '\n';
    }
}

int main(int argc, char **argv)
{
    using namespace apogee;
    const std::string_view function = argc > 1 ? argv[1] : "prop_nav";
    if (argc > 2 || (function != "prop_nav" && function != "point_nav" &&
        function != "guidance" && function != "controls" && function != "motion" && function != "pipeline"))
    {
        std::cerr << "Usage: apogee_entity_playground [prop_nav|point_nav|guidance|controls|motion|pipeline]\n";
        return 1;
    }

    try
    {
        auto entities = make_test_entities();
        constexpr double dt_s = 0.1; // Edit the step size here.
        constexpr int steps = 1;     // Used by the pipeline example only.
        std::mt19937 rng{ 42 };

        // The point-navigation example places the target beyond Earth's horizon.
        if (function == "point_nav")
            entities[1].kinematics.pos_m = lla2eci(0.0, 90.0, 500'000.0, 0.0);
        // Give the isolated controls test an input without running guidance first.
        if (function == "controls")
            entities[0].guidance.accel_command = Vec3{ 0.0, 10.0, 0.0 };

        std::cout << std::fixed << std::setprecision(6) << "Function: " << function
                  << "\nTarget visible: " << std::boolalpha
                  << has_line_of_sight(entities[0].kinematics.pos_m, entities[1].kinematics.pos_m)
                  << "\n\nBefore:\n";
        for (const auto &entity : entities) print_state(entity);

        // Set breakpoints on these calls, or replace them with the function you want to inspect.
        if (function == "prop_nav")
            entities[0].guidance.accel_command = prop_nav(entities[0], entities[1]);
        else if (function == "point_nav")
            entities[0].guidance.accel_command = point_nav(entities[0], entities[1]);
        else if (function == "guidance")
            guidance_commands(entities, rng);
        else if (function == "controls")
            controls_update(entities, dt_s);
        else if (function == "motion")
            motion_step(entities, dt_s);
        else if (function == "pipeline")
            for (int step = 0; step < steps; ++step)
            {
                guidance_commands(entities, rng);
                controls_update(entities, dt_s);
                motion_step(entities, dt_s);
            }

        std::cout << "\nAfter:\n";
        for (const auto &entity : entities)
        {
            print_state(entity);
            if (!entity.kinematics.pos_m.allFinite() || !entity.kinematics.vel_mps.allFinite() ||
                !entity.kinematics.accel_mps2.allFinite() || !entity.guidance.accel_command.allFinite() ||
                !entity.controls.accel_actual.allFinite())
                throw std::runtime_error("Non-finite output in " + entity.key);
        }
        return 0;
    }
    catch (const std::exception &error)
    {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
