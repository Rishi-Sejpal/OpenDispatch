"""Deterministic AIRAC cycle calculator.

AIRAC cycles are published on a strict 28-day schedule. The cycle identifier is
``YYNN`` where ``YY`` is the two-digit year of the effective date and ``NN`` is
the cycle number within that year (01..13).

The reference anchor used here is the ICAO-published 2024 cycle 1 effective
date of 2024-01-25. The year-to-year first-effective dates shift by 1 day in
non-leap years and 2 days in leap years, which this module computes
deterministically.

The cycle effective window for a given cycle is the 28-day period starting at
its effective date; the next cycle's effective date is the boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

# AIRAC cycle 2301 effective 2023-01-26 is the ICAO-published first effective
# date for 2023 and the anchor from which all other cycles are derived. From
# this anchor the schedule is fully deterministic: each year has 13 cycles of
# 28 days (2024 onward; a leap year may produce 14 but for the supported range
# 2023-2030 every year has 13).
_ANCHOR_CYCLE_ID = "2301"
_ANCHOR_FIRST_OF_YEAR = date(2023, 1, 26)
_ANCHOR_YEAR = 2023
_ANCHOR_CYCLE_IN_YEAR = 1

# Cycles per year is 13 (or 14 when a 15th would still fall in that year).
# The first cycle of year Y+1 is always in January of Y+1, so the count is
# determined by the 28-day schedule, not stored here.
_CYCLE_DAYS = 28


@dataclass(frozen=True)
class AiracCycleInfo:
    """Resolved AIRAC cycle for a given date."""

    cycle: str           # e.g. "2608"
    effective_from: date  # inclusive
    effective_to: date    # exclusive (== next cycle's effective_from)
    year: int
    cycle_in_year: int


def _cycles_in_year_starting(first: date, year: int) -> int:
    """Return the number of 28-day AIRAC cycles in ``year`` whose first effective
    date is ``first``. The next effective date after the last one must fall in
    year + 1.
    """
    count = 0
    t = first
    while True:
        nxt = t + timedelta(days=_CYCLE_DAYS)
        if nxt.year == year:
            count += 1
            t = nxt
        else:
            break
    return count + 1  # include the first one


def _first_of_year(year: int) -> date:
    if year == _ANCHOR_YEAR:
        return _ANCHOR_FIRST_OF_YEAR
    if year < _ANCHOR_YEAR:
        raise ValueError(
            f"AIRAC lookup for year {year} is before the {_ANCHOR_YEAR} anchor; "
            "extend the anchor to support earlier years."
        )
    cur = _ANCHOR_FIRST_OF_YEAR
    for y in range(_ANCHOR_YEAR, year):
        n = _cycles_in_year_starting(cur, y)
        cur = cur + timedelta(days=n * _CYCLE_DAYS)
    return cur


def _cycle_of_year_starting(first: date, year: int, cycle_in_year: int) -> tuple[date, date]:
    effective_from = first + timedelta(days=(cycle_in_year - 1) * _CYCLE_DAYS)
    effective_to = effective_from + timedelta(days=_CYCLE_DAYS)
    return effective_from, effective_to


def _year_and_cycle_for_date(d: date) -> tuple[int, int]:
    """Return (year, cycle_in_year) for date ``d``."""
    # A date belongs to the year whose first effective date is on or before d
    # and whose window (first .. first + n*28) contains d. A date in the
    # calendar year d.year may actually belong to d.year - 1 (when d is before
    # d.year's first effective date), so we try d.year first then d.year - 1.
    for y in (d.year, d.year - 1):
        if y < _ANCHOR_YEAR:
            continue
        first = _first_of_year(y)
        n = _cycles_in_year_starting(first, y)
        window_end = first + timedelta(days=n * _CYCLE_DAYS)  # exclusive
        if first <= d < window_end:
            cycle_in_year = (d - first).days // _CYCLE_DAYS + 1
            return y, cycle_in_year
    raise ValueError(f"Could not resolve AIRAC cycle for date {d}")


def current_airac_cycle(today: date | None = None) -> AiracCycleInfo:
    """Return the AIRAC cycle info for the given date (defaults to today, UTC)."""
    if today is None:
        today = datetime.now(tz=timezone.utc).date()
    if not isinstance(today, date):
        raise TypeError("today must be a date")
    year, cycle_in_year = _year_and_cycle_for_date(today)
    first = _first_of_year(year)
    eff_from, eff_to = _cycle_of_year_starting(first, year, cycle_in_year)
    cycle_id = f"{year % 100:02d}{cycle_in_year:02d}"
    return AiracCycleInfo(
        cycle=cycle_id,
        effective_from=eff_from,
        effective_to=eff_to,
        year=year,
        cycle_in_year=cycle_in_year,
    )


def airac_cycle_for_date(d: date) -> AiracCycleInfo:
    """Return the AIRAC cycle info effective on date ``d`` (alias of current)."""
    return current_airac_cycle(d)


def parse_cycle(cycle_id: str) -> AiracCycleInfo:
    """Resolve an explicit cycle identifier (e.g. "2608") to its effective window.

    Raises ValueError if the cycle identifier is malformed or out of range.
    """
    s = (cycle_id or "").strip()
    if len(s) != 4 or not s.isdigit():
        raise ValueError(f"Invalid AIRAC cycle identifier: {cycle_id!r}")
    yy = int(s[:2])
    cn = int(s[2:])
    year = 2000 + yy
    if cn < 1 or cn > 14:
        raise ValueError(f"AIRAC cycle number out of range: {cn}")
    first = _first_of_year(year)
    n = _cycles_in_year_starting(first, year)
    if cn > n:
        raise ValueError(
            f"AIRAC cycle {cycle_id} does not exist in year {year} (year has {n} cycles)"
        )
    eff_from, eff_to = _cycle_of_year_starting(first, year, cn)
    return AiracCycleInfo(
        cycle=s,
        effective_from=eff_from,
        effective_to=eff_to,
        year=year,
        cycle_in_year=cn,
    )
