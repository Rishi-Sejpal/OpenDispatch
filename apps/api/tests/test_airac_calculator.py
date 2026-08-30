"""Tests for the deterministic AIRAC cycle calculator."""

from datetime import date

import pytest

from app.services.airac import (
    current_airac_cycle,
    parse_cycle,
    _first_of_year,
)


def test_anchor_cycle_2301():
    c = current_airac_cycle(date(2023, 1, 26))
    assert c.cycle == "2301"
    assert c.effective_from == date(2023, 1, 26)
    assert c.effective_to == date(2023, 2, 23)


def test_cycle_2401():
    c = current_airac_cycle(date(2024, 1, 25))
    assert c.cycle == "2401"
    assert c.effective_from == date(2024, 1, 25)
    assert c.effective_to == date(2024, 2, 22)


def test_date_before_anchor_year_first_cycle():
    # 2024-01-24 falls in 2023's last cycle (2313)
    c = current_airac_cycle(date(2024, 1, 24))
    assert c.cycle == "2313"
    assert c.effective_from == date(2023, 12, 28)
    assert c.effective_to == date(2024, 1, 25)


def test_current_cycle_today_is_2608():
    c = current_airac_cycle(date(2026, 8, 30))
    assert c.cycle == "2608"
    assert c.effective_from == date(2026, 8, 6)
    assert c.effective_to == date(2026, 9, 3)


def test_cycle_boundary_at_next_effective_date():
    # The next cycle starts at the current cycle's effective_to
    cur = current_airac_cycle(date(2026, 8, 30))
    nxt = current_airac_cycle(cur.effective_to)
    assert nxt.cycle == "2609"


def test_year_boundary_in_december_january():
    # Late December 2026 is still cycle 2613
    assert current_airac_cycle(date(2026, 12, 31)).cycle == "2613"
    # Early January 2027 before the new year's first effective date is still 2613
    assert current_airac_cycle(date(2027, 1, 1)).cycle == "2613"
    # 2027's first effective date is 2027-01-21
    assert current_airac_cycle(date(2027, 1, 21)).cycle == "2701"


def test_first_of_year_offsets():
    assert _first_of_year(2023) == date(2023, 1, 26)
    assert _first_of_year(2024) == date(2024, 1, 25)
    assert _first_of_year(2025) == date(2025, 1, 23)
    assert _first_of_year(2026) == date(2026, 1, 22)
    assert _first_of_year(2027) == date(2027, 1, 21)


def test_parse_cycle_round_trip():
    for cid in ("2301", "2313", "2401", "2506", "2608", "2613"):
        info = parse_cycle(cid)
        assert info.cycle == cid


def test_parse_cycle_invalid():
    with pytest.raises(ValueError):
        parse_cycle("abcd")
    with pytest.raises(ValueError):
        parse_cycle("2600")
    with pytest.raises(ValueError):
        parse_cycle("2614")


def test_parse_cycle_window_matches_current():
    info = parse_cycle("2608")
    assert info.effective_from == date(2026, 8, 6)
    assert info.effective_to == date(2026, 9, 3)
    assert current_airac_cycle(info.effective_from).cycle == "2608"
    assert current_airac_cycle(info.effective_to).cycle == "2609"
