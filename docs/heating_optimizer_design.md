# Heating Optimizer: Concept & Water Tank Strategy

This document captures the early design ideas for a generic heating optimization framework and outlines the first device profile (the domestic hot-water tank). The focus is on building reusable patterns that support multiple appliance types, flexible control strategies, and price-aware scheduling using the [porssisahko.net v2 API](../porssisahko.net%20API%20Documentation.md).

## High-Level Goals
- Allow users to add diverse heating appliances, each with their own cycles, operating limits, and control interfaces.
- Support configurable objectives (comfort bands, peak-shaving, cost ceilings) while remaining hardware-agnostic.
- Incorporate quarter-hour electricity pricing, forecast data, and optional external signals when planning heat cycles.
- Provide fallback/override logic so that safety mechanisms (e.g., mechanical switches, oil burners) continue to operate correctly.
- Expose device state, upcoming heat plans, and price insights to Home Assistant for visualization and automation.

## Core Concepts
- **Device Profile**: Describes capabilities (switches, sensors, external blockers), thermal characteristics (loss curves, safety ranges), and user preferences (comfort windows, min/max temps). Each profile can be stored as a config entry with options or referenced from a central registry.
- **Coordinator / Scheduler**: Aggregates inputs (prices, device states, household schedule) and produces heat/idle commands per 15-minute slot. The scheduler should be modular so different optimization strategies can be swapped in.
- **Constraints Engine**: Enforces limits such as maximum simultaneous power draw, fuse sharing (“secondary element allowed” flag), and minimum rest times between cycles.
- **Data Sources**:
  - Electricity prices: fetched periodically from `latest-prices.json`. Cache locally to avoid rate limits; update at least twice daily or when data expires.
  - Device telemetry: Home Assistant entities (temperature sensors, binary sensors, switches).
  - Calendar/schedule: Optionally integrate with HA calendars, person presence, or manual schedules to adjust comfort setpoints.
- **Plan Execution**: Use `switch.turn_on/off` and expose a virtual coordinator entity that publishes the current plan, next change, and reason (cheap price, maintain comfort, oil fallback).

## Current Implementation Snapshot
- `PriceCoordinator` downloads and caches quarter-hour prices from porssisahko.net for up to 24 h of planning.
- `PlanCoordinator` consumes prices + the configured temperature sensor to simulate the water-tank trajectory with a loss model (≈1–2 °C/h) and simple staging heuristics.
- A diagnostic sensor (`sensor.<device>_heating_plan_status`) shows the upcoming action (`idle`, `heat_primary`, `heat_dual`) plus a preview of the next slots without touching the actual relays.
- Defaults: comfort windows at 05:30–09:00 and 16:00–22:00, comfort target 75 °C, minimum 60 °C, cheap/expensive thresholds 4 c / 15 c per kWh.
- Limitations: secondary element availability flag is not yet modelled; optimisation is greedy; prices come directly from the API without local persistence beyond the coordinator cache.

## Water Tank Device Profile (Initial Implementation)
- **Hardware Summary**:
  - Two independent 2 kW heating elements controllable as switches.
  - Temperature sensor providing tank temperature.
  - External binary sensor gating availability of the second element (shared fuse).
  - Mechanical oil burner takes over under 60 °C.
- **Thermal Model**:
  - Max safe temperature ≈ 90 °C.
  - Loss rate ≈ 2 °C/h at 90 °C, ≈ 1 °C/h at 70 °C (define as piecewise or curve).
  - Comfortable hot-water target ≥ 75 °C for normal operation; preheat/overheat allowed when prices are low.
- **Control Objectives**:
  1. Maintain ≥ 75 °C before periods of expected usage (morning/evening).
  2. Overheat up to 90 °C when prices fall below a “very cheap” threshold (e.g., 4 c/kWh) to ride through future spikes.
  3. Avoid electric heating if price ≥ 15 c/kWh unless temperature would otherwise drop below 60 °C imminently.
  4. Allow mechanical oil burner to operate when electricity stays expensive for extended periods.
- **Inputs & Signals**:
  - `sensor.tank_temperature`
  - `switch.element_primary`, `switch.element_secondary`
  - `binary_sensor.secondary_allowed`
  - Price feed entity (custom price coordinator)
  - Optional schedule (workday vs weekend, presence-based overrides)
- **Outputs**:
  - Switch commands to elements (with guard against simultaneous >4 kW if that conflicts with other loads).
  - Virtual sensor showing planned target temperature trajectory.
  - Diagnostics data in HA (`price_now`, `next_price_drop`, `predicted_oil_usage`).

## Suggested Control Flow
1. **Price Ingestion**:
   - Fetch `latest-prices.json` every 12 hours and store in local cache (e.g., `DataUpdateCoordinator`).
   - Derive rolling windows: current 24 hours, next 24 hours, price percentiles.
2. **Demand Forecasting**:
   - Start with static time windows (morning/evening). Future enhancement: learn from usage patterns or HA utility meters.
3. **Thermal Simulation**:
   - Predict tank temperature decay for each 15-minute slot based on current temperature and loss curve.
   - Predict electric heating effect for one or both elements (2 kW each -> ΔT per slot).
4. **Optimization Loop**:
   - Evaluate each upcoming slot, deciding whether to run 0/1/2 elements.
   - Constraints:
     - Do not exceed target max (90 °C).
     - Only use secondary element if `binary_sensor.secondary_allowed` is on.
     - Keep temperature above dynamic minimum (baseline 60 °C, raised to 75 °C during comfort windows).
     - Respect price thresholds (skip heating if price ≥ 15 c unless minimum would be breached soon).
   - Use greedy approach initially (backward induction to ensure comfort time has enough heat), later swap in linear programming if necessary.
5. **Execution & Feedback**:
   - Publish next actions via HA entities.
   - Issue commands close to slot boundary with small lookahead (e.g., 5 minutes).
   - Re-run planning when key inputs change (price update, temp delta, schedule change).

## Config Entry Proposal
- **General Options**:
  - Appliance type (water tank, storage heater, floor heating, etc.).
  - Comfort schedule (time ranges + target temps).
  - Price thresholds: `overheat_price`, `normal_limit_price`, `oil_preference_price`.
  - Safety margins: max temp, min temp.
- **Device Mapping**:
  - Primary/secondary switch entity IDs.
  - Temperature sensor entity ID.
  - Optional availability sensor for extra stages.
  - Optional cost data (fixed delivery fee, multipliers).
- **Advanced**:
  - Thermal model parameters (loss coefficients, heating rate).
  - Shared circuit group (for future multi-device coordination).

## Testing Strategy
- Scheduler tests with synthetic price curves validate preheat vs expensive avoidance.
- Integration tests exercise the config flow and confirm the diagnostic sensor renders a plan (and surfaces `unavailable` if temperature data disappears).

## Next Steps
1. Persist price history / predictions to allow more advanced forecasting and support other device profiles.
2. Extend the config flow & options to capture thresholds, comfort schedules, and optional secondary-element sensor.
3. Introduce actuator abstractions so the planner can produce actionable commands while still allowing dry-run simulation.
4. Improve the planner (predict water usage, account for shared circuits, consider multi-day optimisation).
5. Add diagnostics panels and trace logging to make tuning easier in real deployments.
