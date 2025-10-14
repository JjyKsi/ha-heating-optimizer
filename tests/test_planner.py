"""Unit tests for the planning utilities."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from custom_components.heating_optimizer.planner import (
    PlanEntry,
    PriceSlot,
    generate_water_tank_plan,
)


def _build_price_slots(start: datetime, count: int, base_price: float) -> list[PriceSlot]:
    slots: list[PriceSlot] = []
    cursor = start
    for _ in range(count):
        slot_end = cursor + timedelta(minutes=15)
        slots.append(PriceSlot(start=cursor, end=slot_end, price=base_price))
        cursor = slot_end
    return slots


def test_generate_plan_handles_price_signals() -> None:
    """Check that the heuristic plan responds to cheap/expensive prices."""
    now = datetime(2024, 6, 1, 6, 5, tzinfo=timezone.utc)
    prices = _build_price_slots(now - timedelta(hours=2), 96, 6.0)

    # Mark an upcoming cheap window and an expensive window later in the day.
    cheap_index = 6  # soon after now
    expensive_index = 24
    prices[cheap_index] = PriceSlot(
        start=prices[cheap_index].start,
        end=prices[cheap_index].end,
        price=2.5,
    )
    prices[expensive_index] = PriceSlot(
        start=prices[expensive_index].start,
        end=prices[expensive_index].end,
        price=22.0,
    )

    plan = generate_water_tank_plan(
        now=now,
        current_temperature=74.0,
        prices=prices,
        cheap_threshold=4.0,
        expensive_threshold=15.0,
        comfort_temp=75.0,
        min_temp=60.0,
        max_temp=90.0,
        device_name="Test Tank",
    )

    assert plan.plan, "Plan should include at least one slot"
    first_entry: PlanEntry = plan.plan[0]
    assert first_entry.action in {"heat_primary", "heat_dual"}
    assert first_entry.target_temp >= 75.0

    cheap_entry = next(entry for entry in plan.plan if entry.price <= 3.0)
    assert cheap_entry.action == "heat_dual"
    assert cheap_entry.reason == "cheap_preheat"

    expensive_entry = next(entry for entry in plan.plan if entry.price >= 20.0)
    assert expensive_entry.action == "idle"
    assert expensive_entry.reason in {"skip_expensive", "at_temperature_cap"}
