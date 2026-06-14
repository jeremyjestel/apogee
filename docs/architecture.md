# APOGEE Architecture

## Purpose

APOGEE is a modular C++/Python simulation framework for modeling sensing, tracking, autonomy, guidance, control, and engagement outcomes in a missile intercept scenario.

---

## Coordinate System

### Internal Simulation Frame

ENU (East-North-Up)

```text
x = East
y = North
z = Up
```

---

## Units

```text
Length      meters
Time        seconds
Mass        kilograms
Velocity    meters/second
Acceleration meters/second²
Angle       radians
Angular Rate radians/second
```

Conversions occur only at interfaces.

---

## Time Model

Simulation uses a fixed timestep.

```text
t = n * dt
```

The simulation is deterministic for a given configuration and random seed.

---

## Source of Truth

The simulation state is the authoritative representation of the environment.

Visualization is not part of the simulation loop.

All visualization is derived from logged simulation outputs.

---

## Probability of Mission Success

P(success) = f(sensor quality, estimation error, latency, control limits, kinematics)

---

## Language Responsibilities

### C++

Owns:

* Simulation engine
* State propagation
* Physics
* Tracking
* Guidance
* Control
* Performance-critical algorithms

### Python

Owns:

* Scenario definition
* Configuration
* Batch execution
* Analysis
* Visualization
* Machine learning workflows

---

## State Separation

The following representations remain distinct:

```text
Truth State
Measurement
Track Estimate
Decision State
```

---

## Configuration

Simulation parameters shall be defined through configuration files.

Scenario behavior shall not be hardcoded.

---

## Logging

Simulation outputs are recorded as structured logs.

Logs are a first-class artifact.

Analysis and visualization operate on logs rather than live simulation state.
