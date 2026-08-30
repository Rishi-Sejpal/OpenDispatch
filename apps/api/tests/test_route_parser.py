"""Tests for route parser."""

from __future__ import annotations

from app.services.route_parser import is_airway, is_identifier, is_reserved, parse_route


def test_is_airway() -> None:
    assert is_airway("A466")
    assert is_airway("B208")
    assert is_airway("L301")
    assert is_airway("UN859")
    assert not is_airway("BOM")
    assert not is_airway("DCT")


def test_is_reserved() -> None:
    assert is_reserved("DCT")
    assert is_reserved("SID")
    assert not is_reserved("BOM")


def test_is_identifier() -> None:
    assert is_identifier("BOM")
    assert is_identifier("DEL")
    assert is_identifier("VABB")
    assert not is_identifier("DCT")
    assert not is_identifier("A466")


def test_parse_empty() -> None:
    result = parse_route("")
    assert not result.legs
    assert result.errors


def test_parse_dct_route() -> None:
    result = parse_route("VABB DCT BOM DCT VIDP")
    assert len(result.legs) == 3
    assert [l.ident for l in result.legs] == ["VABB", "BOM", "VIDP"]
    assert all(l.leg_type == "DCT" for l in result.legs)
    assert not result.errors


def test_parse_airway_route() -> None:
    result = parse_route("VABB BOM A466 GADIN A466 DEL")
    # 4 legs: VABB, BOM, GADIN (airway A466), DEL (airway A466)
    assert len(result.legs) == 4
    assert result.legs[0].ident == "VABB"
    assert result.legs[0].leg_type == "DCT"
    assert result.legs[2].ident == "GADIN"
    assert result.legs[2].leg_type == "AIRWAY"
    assert result.legs[2].airway == "A466"
    assert result.legs[2].via == ("BOM", "GADIN")


def test_parse_detects_duplicates() -> None:
    result = parse_route("BOM DCT BOM")
    # 2 legs (start BOM, then BOM as DCT)
    assert any("Duplicate" in e for e in result.errors)


def test_parse_unknown_token() -> None:
    result = parse_route("VABB 12345 BOM")
    assert any("Unrecognized" in e or "Unknown" in e for e in result.errors)


def test_parse_airway_without_join_fix() -> None:
    result = parse_route("A466 GADIN A466 DEL")
    # No preceding fix, should add an error
    assert any("preceding fix" in e for e in result.errors)
