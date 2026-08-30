"""Aviation route parser.

Converts textual ICAO route strings such as:

    VABB DCT BOM A466 GADIN DCT VIDP

into structured legs.

Tokens rules (simplified, ICAO-style):
- identifiers may be alpha-alphanumeric, up to 7 chars, but we use up to 12 to allow airways.
- 'DCT' between two fixes means "direct".
- An airway token is identified by a leading letter (e.g. A466, B208, L301) and
  the next token is the join fix and the token after that is the leave fix.
- 'SID', 'STAR' are ignored here (handled by procedure engine).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Tokens like A466, B208, L301, M890, N895, P574, R650, UL333, UM551, UN859, UT10 ...
AIRWAY_PATTERN = re.compile(r"^[A-Z]{1,2}\d{1,4}$")
# Standard reserved words
RESERVED = {"DCT", "SID", "STAR", "APP", "APPR"}

_IDENT = re.compile(r"^[A-Z0-9]{2,12}$")


@dataclass
class ParsedLeg:
    sequence: int
    ident: str
    leg_type: str  # "AIRWAY" or "DCT"
    airway: str | None = None
    via: tuple[str, str] | None = None  # (join, leave) for airway legs


@dataclass
class ParseResult:
    legs: list[ParsedLeg] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def normalize(text: str) -> list[str]:
    return [t.upper() for t in text.replace("\n", " ").split() if t]


def is_airway(token: str) -> bool:
    return bool(AIRWAY_PATTERN.match(token)) and token not in RESERVED


def is_reserved(token: str) -> bool:
    return token in RESERVED


def is_identifier(token: str) -> bool:
    return bool(_IDENT.match(token)) and not is_airway(token) and not is_reserved(token)


def parse_route(text: str) -> ParseResult:
    """Parse a route string into legs. No validity check against the navigation database."""
    tokens = normalize(text)
    if not tokens:
        return ParseResult(errors=["Route is empty."])

    result = ParseResult()
    i = 0
    seq = 0
    first_ident: str | None = None
    last_ident: str | None = None

    # collect ident tokens in order; when we see AIRWAY, the previous ident is join
    # and the next ident is leave; everything between two idents is implicit DCT
    while i < len(tokens):
        t = tokens[i]
        if t in {"SID", "STAR", "APP", "APPR"}:
            # procedures are not represented in route string; skip with a note
            result.errors.append(f"Procedure keyword '{t}' is not part of the route string.")
            i += 1
            continue
        if is_airway(t):
            # previous ident is the join, next ident is the leave
            if not result.legs:
                result.errors.append(f"Airway '{t}' has no preceding fix.")
                i += 1
                continue
            if i + 1 >= len(tokens) or not is_identifier(tokens[i + 1]):
                result.errors.append(f"Airway '{t}' must be followed by a leave fix.")
                i += 1
                continue
            join = result.legs[-1].ident
            leave = tokens[i + 1]
            seq += 1
            result.legs.append(ParsedLeg(sequence=seq, ident=leave, leg_type="AIRWAY", airway=t, via=(join, leave)))
            last_ident = leave
            i += 2
            continue
        if is_identifier(t):
            seq += 1
            if first_ident is None:
                first_ident = t
            if result.legs and result.legs[-1].leg_type != "DCT":
                # last leg is end of an airway, so between them is implicit DCT
                # (we represent airway as a single leg ending at 'leave'; the join->leave
                # replaces the direct leg. No DCT is needed here.)
                pass
            elif result.legs and result.legs[-1].leg_type == "DCT":
                # update distance target is fine, the leg already represents DCT from previous
                # We'll just add this as a "via" DCT point
                pass
            result.legs.append(ParsedLeg(sequence=seq, ident=t, leg_type="DCT"))
            last_ident = t
            i += 1
            continue
        # unknown token
        result.errors.append(f"Unrecognized route token: '{t}'.")
        i += 1

    # Validation rules
    if not result.legs:
        result.errors.append("No identifiers were parsed from the route.")

    # Adjacent duplicates
    for a, b in zip(result.legs, result.legs[1:]):
        if a.ident == b.ident:
            result.errors.append(f"Duplicate fix '{a.ident}' in route.")

    return result
