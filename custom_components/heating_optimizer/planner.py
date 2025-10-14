"""Planning logic for Heating Optimizer devices."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Iterable

from homeassistant.util import dt as dt_util

from .const import PLAN_HORIZON, PLAN_SLOT_MINUTES


@dataclass(slots=True)
class PriceSlot:
    """Electricity price for a specific interval."""

    start: datetime
    end: datetime
    price: float


@dataclass(slots=True)
class PlanEntry:
    """Instruction for a heating slot."""

    start: datetime
    end: datetime
    action: str
    stages: int
    price: float
    predicted_temp: float
    target_temp: float
    reason: str


@dataclass(slots=True)
class PlanResult:
    """Plan metadata returned by the coordinator."""

    generated_at: datetime
    device_name: str
    current_temperature: float
    plan: list[PlanEntry]


COMFORT_WINDOWS = (
    (time(hour=5, minute=30), time(hour=9, minute=0)),
    (time(hour=16, minute=0), time(hour=22, minute=0)),
)
BACKGROUND_OFFSET = 5.0  # Degrees below comfort temp outside comfort windows.
HEAT_GAIN_PER_STAGE = 0.8  # Approximate °C gain per 15 minutes per element.
MAX_STAGES = 2


def _is_in_window(window: tuple[time, time], current_time: time) -> bool:
    start, end = window
    if start <= end:
        return start <= current_time <= end
    # Window wraps midnight.
    return current_time >= start or current_time <= end


def _comfort_target(dt_obj: datetime, comfort_temp: float, min_temp: float) -> float:
    local_dt = dt_util.as_local(dt_obj)
    current_time = local_dt.time()
    for window in COMFORT_WINDOWS:
        if _is_in_window(window, current_time):
            return max(min_temp, comfort_temp)
    return max(min_temp, comfort_temp - BACKGROUND_OFFSET)


def _estimate_loss(current_temp: float) -> float:
    """Approximate tank temperature loss per 15 minutes."""
    temp = max(0.0, current_temp)
    if temp >= 70:
        ratio = min((min(temp, 90) - 70) / 20, 1.0)
        base = 0.25  # ≈1°C/h at 70°C
        return base + (0.25 * ratio)  # up to ≈2°C/h at 90°C
    if temp >= 60:
        return 0.2  # ≈0.8°C/h between 60°C and 70°C
    return 0.15


def _predict_heating_gain(stages: int) -> float:
    stages = max(0, min(MAX_STAGES, stages))
    return HEAT_GAIN_PER_STAGE * stages


def _select_price_slot(prices: Iterable[PriceSlot], slot_start: datetime) -> PriceSlot | None:
    for slot in prices:
        if slot.start <= slot_start < slot.end:
            return slot
    return None


def generate_water_tank_plan(
    *,
    now: datetime,
    current_temperature: float,
    prices: list[PriceSlot],
    cheap_threshold: float,
    expensive_threshold: float,
    comfort_temp: float,
    min_temp: float,
    max_temp: float,
    device_name: str,
) -> PlanResult:
    """Simulate the next horizon for the water-tank profile."""
    plan: list[PlanEntry] = []
    predicted_temp = current_temperature
    slot_length = timedelta(minutes=PLAN_SLOT_MINUTES)
    end_time = now + PLAN_HORIZON

    slot_start = now - timedelta(
        minutes=now.minute % PLAN_SLOT_MINUTES,
        seconds=now.second,
        microseconds=now.microsecond,
    )

    while slot_start < end_time:
        slot_end = slot_start + slot_length
        price_slot = _select_price_slot(prices, slot_start)
        if price_slot is None:
            break
        price = price_slot.price

        target_temp = _comfort_target(slot_start, comfort_temp, min_temp)

        loss = _estimate_loss(predicted_temp)
        predicted_temp = predicted_temp - loss

        stage_request = 0
        decision_reason = "idle"

        if predicted_temp <= min_temp + 0.2:
            stage_request = 1
            decision_reason = "protect_minimum"
        elif predicted_temp < target_temp - 0.5:
            stage_request = 1
            decision_reason = "maintain_comfort"

        if price <= cheap_threshold and predicted_temp < max_temp - 1.0:
            stage_request = max(stage_request, 2)
            decision_reason = "cheap_preheat"

        if price >= expensive_threshold and predicted_temp > max(min_temp + 1.0, target_temp - 1.0):
            stage_request = 0
            decision_reason = "skip_expensive"

        if predicted_temp >= max_temp - 0.5:
            stage_request = 0
            decision_reason = "at_temperature_cap"

        heat_gain = _predict_heating_gain(stage_request)
        projected_temp = min(max_temp, predicted_temp + heat_gain)

        if stage_request == 0:
            action = "idle"
        elif stage_request == 1:
            action = "heat_primary"
        else:
            action = "heat_dual"

        plan.append(
            PlanEntry(
                start=slot_start,
                end=slot_end,
                action=action,
                stages=stage_request,
                price=price,
                predicted_temp=projected_temp,
                target_temp=target_temp,
                reason=decision_reason,
            )
        )

        predicted_temp = projected_temp
        slot_start = slot_end

    return PlanResult(
        generated_at=now,
        device_name=device_name,
        current_temperature=current_temperature,
        plan=plan,
    )
