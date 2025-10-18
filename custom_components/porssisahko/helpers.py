"""Shared helpers for handling price slots."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from homeassistant.util import dt as dt_util

from .coordinator import PriceSlot


def current_slot(slots: Iterable[PriceSlot] | None, *, now: datetime | None = None) -> PriceSlot | None:
    """Return the price slot covering the provided time."""
    if not slots:
        return None
    moment = now or dt_util.utcnow()
    for slot in slots:
        if slot.start <= moment < slot.end:
            return slot
    return None


def slot_for_time(slots: Iterable[PriceSlot] | None, target: datetime) -> PriceSlot | None:
    """Return the slot covering the target time."""
    if not slots:
        return None
    for slot in slots:
        if slot.start <= target < slot.end:
            return slot
    return None


def format_slot_time(value: datetime) -> str:
    """Convert a slot timestamp to the local ISO-8601 representation."""
    return dt_util.as_local(value).isoformat(timespec="minutes")
