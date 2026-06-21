#pragma once

// ==========================
// 1. STANDARD LIBRARY
// ==========================
#include <vector>
#include <memory>
#include <optional>
#include <string>

// Only include what you actually use

// ==========================
// 2. PROJECT INCLUDEScv
// ==========================
#include "core/truth_state.h"
#include "dynamics/dynamics_model.h"

// NEVER include implementation-heavy headers if forward declaration works

namespace apogee::<module> {

// ==========================
// 3. CLASS / STRUCT DEFINITION
// ==========================

// Use struct for PURE DATA ONLY (no logic)
struct ExampleState {
    double time_s;
    Vector3 position_m;
};

// Use class when behavior exists
class ExampleSystem {
public:
    // ==========================
    // 4. PUBLIC API
    // ==========================

    ExampleSystem();

    void update(double dt_s);

    // Prefer const references for read-only access
    const ExampleState& state() const;

    // Avoid exposing internal mutable state directly

    // ==========================
    // 5. RULE OF 5 (ONLY IF NEEDED)
    // ==========================
    // Only define these if you manage resources manually
    // ExampleSystem(const ExampleSystem&) = delete;
    // ExampleSystem& operator=(const ExampleSystem&) = delete;

private:
    // ==========================
    // 6. INTERNAL STATE
    // ==========================

    ExampleState state_;

    // Prefer composition over inheritance
    std::unique_ptr<DynamicsModel> dynamics_;

    // NEVER expose raw internal pointers unless necessary
};

} // namespace apogee::<module>