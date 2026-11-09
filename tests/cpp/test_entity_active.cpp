#include <algorithm>
#include <iostream>
#include <random>
#include <stdexcept>

#include "controls/control_system.hpp"
#include "guidance/guidance_system.hpp"
#include "logging/logging.hpp"
#include "math/constants.hpp"
#include "motion/motion_system.hpp"
#include "scenarios/default_scenario.hpp"
#include "sensors/radar/radar_system.hpp"
#include "simulation/scenario_runtime.hpp"

namespace
{
    using namespace apogee;
    void check(bool condition, const char *message)
    {
        if (!condition) throw std::runtime_error(message);
    }

    void test_disabled_systems_and_targets()
    {
        std::vector<Entity> entities(2);
        auto &missile = entities[0];
        missile.id = 1;
        missile.type = "missile";
        missile.kinematics.pos_m = Vec3{ constants::earth_radius_m + 200'000.0, 0.0, 0.0 };
        missile.kinematics.vel_mps = Vec3{ 0.0, 100.0, 0.0 };
        missile.guidance.target_index = 1;
        missile.guidance.accel_command = Vec3::Ones();
        missile.controls.accel_actual = Vec3::Ones();
        missile.active = false;
        entities[1].active = false; // An invalid target state must not reach a model.
        std::mt19937 rng(42);
        guidance_commands(entities, rng);
        controls_update(entities, 0.1);
        const auto before = missile.kinematics;
        motion_step(entities, 0.1);
        check(missile.guidance.accel_command.isZero() && missile.controls.accel_actual.isZero(),
              "Inactive entities must clear guidance and control outputs.");
        check(missile.kinematics.pos_m == before.pos_m && missile.kinematics.vel_mps == before.vel_mps,
              "Inactive entities must not advance motion.");

        missile.active = true;
        missile.guidance.accel_command = Vec3::Ones();
        guidance_commands(entities, rng);
        check(missile.guidance.accel_command.isZero(), "Guidance must ignore an inactive target.");
        motion_step(entities, 0.1);
        check(missile.kinematics.pos_m != before.pos_m, "Reactivated entities must advance again.");

        missile.motion_type = MotionType::EarthFixed;
        missile.active = false;
        const auto fixed_before = missile.kinematics.pos_m;
        motion_step(entities, 0.1);
        check(missile.kinematics.pos_m == fixed_before, "Inactive Earth-fixed entities must also freeze.");
    }

    void test_instantiation_and_history()
    {
        auto params = make_default_scenario();
        for (auto &definition : params.entities) definition.active = false;
        auto entities = instantiate_entities(params);
        initialize_pursuits(params, entities);
        check(std::all_of(entities.begin(), entities.end(), [](const Entity &e) { return !e.active; }),
              "Every entity type must inherit the configured activity state.");
        check(require_entity(entities, "red_missile").kinematics.vel_mps.norm() > 0.0,
              "Disabled entities must retain their initial state for later reactivation.");
        Result result;
        Logger logger(entities, result);
        logger.log(entities, 0.0);
        entities[0].active = true;
        logger.log(entities, 0.1);
        auto field = std::find_if(result.scalars.begin(), result.scalars.end(), [&](const auto &item)
            { return item.entity_id == entities[0].id && item.system == "entity" && item.key == "active"; });
        check(field != result.scalars.end() && field->values == std::vector<double>{ 0.0, 1.0 },
              "Active state changes must be logged on the simulation timeline.");
    }

    void test_radar_activity()
    {
        std::vector<Entity> entities(3);
        entities[0].id = 1;
        entities[0].motion_type = MotionType::EarthFixed;
        entities[0].kinematics.pos_m = Vec3{ constants::earth_radius_m + 100.0, 0.0, 0.0 };
        auto params = *make_default_scenario().entities.front().radar;
        params.bandwidth_hz = 20.0;
        params.pw_us = 50'000.0;
        params.pri_us = 200'000.0;
        params.pulse_num = 2;
        params.doppler_zero_pad_factor = 1;
        entities[0].radars.push_back(RadarComponent{ .params = finalize_radar_params(params) });
        entities[1].id = 2;
        entities[1].kinematics.pos_m = Vec3{ constants::earth_radius_m + 200'000.0, 0.0, 0.0 };
        entities[2] = entities[1];
        entities[2].id = 3;
        entities[2].active = false;
        std::mt19937 rng(42);
        radar_system(entities, rng);
        auto &radar = entities[0].radars[0];
        check(radar.targets.size() == 1 && radar.targets[0].id == 2,
              "Radar must omit inactive entities from its targets.");
        radar.state.range_pulse_map.setConstant(Complex{ 7.0, 0.0 });
        entities[0].active = false;
        radar_system(entities, rng);
        check(radar.targets.empty() && radar.state.range_pulse_map(0, 0) == Complex{ 7.0, 0.0 },
              "Inactive radar owners must clear target lists and skip sensor processing.");
    }
}

int main()
{
    try
    {
        test_disabled_systems_and_targets();
        test_instantiation_and_history();
        test_radar_activity();
        std::cout << "Entity active checks passed.\n";
        return 0;
    }
    catch (const std::exception &error)
    {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
