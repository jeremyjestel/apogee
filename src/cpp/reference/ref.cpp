#include "entities/example_system.h"

// ONLY include what you must implement

namespace apogee::<module> {

// ==========================
// 1. CONSTRUCTOR / DESTRUCTOR
// ==========================

ExampleSystem::ExampleSystem() {
    // initialize state safely
}

// ==========================
// 2. CORE UPDATE / BEHAVIOR
// ==========================

void ExampleSystem::update(double dt_s) {
    // MAIN LOGIC GOES HERE

    // Example pattern:
    // 1. read state
    // 2. compute outputs
    // 3. update state
}

// ==========================
// 3. ACCESSORS
// ==========================

const ExampleState& ExampleSystem::state() const {
    return state_;
}

// ==========================
// 4. PRIVATE HELPERS (ONLY IF SMALL)
// ==========================

// Keep helpers here if they are ONLY used in this file
// Otherwise move to a separate module

} // namespace apogee::<module>