"""Weather provider abstraction.

Implementations must implement:
- get_metar(icao)
- get_taf(icao)
- get_winds_aloft(latitude, longitude, altitude_ft, valid_at)
- snapshot(icaos, valid_at)

The local provider returns deterministic synthetic weather so the application
works without internet and tests do not depend on real-world data.
"""

from __future__ import annotations

import abc
import hashlib
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable

from app.models import WeatherReport, WindsAloftReport


@dataclass
class MetarObservation:
    icao: str
    observed_at: datetime
    temperature_c: float
    dewpoint_c: float
    wind_direction_deg: float
    wind_speed_kts: float
    visibility_m: int
    ceiling_ft: int | None
    altimeter_hpa: float
    flight_category: str  # VFR / MVFR / IFR / LIFR
    raw: str

    def to_dict(self) -> dict:
        return {
            "icao": self.icao,
            "observed_at": self.observed_at.isoformat(),
            "temperature_c": self.temperature_c,
            "dewpoint_c": self.dewpoint_c,
            "wind_direction_deg": self.wind_direction_deg,
            "wind_speed_kts": self.wind_speed_kts,
            "visibility_m": self.visibility_m,
            "ceiling_ft": self.ceiling_ft,
            "altimeter_hpa": self.altimeter_hpa,
            "flight_category": self.flight_category,
        }


@dataclass
class TafForecast:
    icao: str
    valid_from: datetime
    valid_to: datetime
    raw: str
    forecast_periods: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "icao": self.icao,
            "valid_from": self.valid_from.isoformat(),
            "valid_to": self.valid_to.isoformat(),
            "raw": self.raw,
            "forecast_periods": self.forecast_periods,
        }


class WeatherProvider(abc.ABC):
    name: str = "abstract"

    @abc.abstractmethod
    def get_metar(self, icao: str) -> MetarObservation: ...

    @abc.abstractmethod
    def get_taf(self, icao: str) -> TafForecast: ...

    @abc.abstractmethod
    def get_wind_at(
        self, latitude: float, longitude: float, altitude_ft: int, valid_at: datetime
    ) -> tuple[float, float, float]:
        """Return (wind_direction_deg, wind_speed_kts, temperature_c)."""


def _stable_hash(value: str) -> int:
    h = hashlib.md5(value.encode("utf-8")).hexdigest()
    return int(h, 16)


class LocalWeatherProvider(WeatherProvider):
    """Deterministic synthetic weather.

    Wind and temperature are derived from a stable hash of the query so that
    the same airport/time/altitude always returns the same value, making the
    planning pipeline fully testable without network access.
    """

    name = "local"

    def __init__(self) -> None:
        self._metar_cache: dict[str, MetarObservation] = {}
        self._taf_cache: dict[str, TafForecast] = {}

    def get_metar(self, icao: str) -> MetarObservation:
        icao = icao.upper()
        if icao in self._metar_cache:
            return self._metar_cache[icao]
        h = _stable_hash(icao)
        wind_dir = h % 360
        wind_speed = 5 + (h // 360) % 25
        temp_c = 10 + ((h // 17) % 25) - 5
        dewpoint = temp_c - ((h // 53) % 8)
        vis = 9999 if (h % 5) else 5000
        ceiling = None if (h % 4) else (h // 7 % 5) * 1000 + 1500
        alt = 1013 + ((h // 23) % 20) - 10
        cat = "VFR"
        if ceiling is not None and ceiling < 1000:
            cat = "LIFR"
        elif ceiling is not None and ceiling < 3000:
            cat = "IFR"
        elif vis < 5000:
            cat = "MVFR"
        obs = MetarObservation(
            icao=icao,
            observed_at=datetime.now(tz=timezone.utc),
            temperature_c=float(temp_c),
            dewpoint_c=float(dewpoint),
            wind_direction_deg=float(wind_dir),
            wind_speed_kts=float(wind_speed),
            visibility_m=int(vis),
            ceiling_ft=ceiling,
            altimeter_hpa=float(alt),
            flight_category=cat,
            raw=f"{icao} {datetime.now(tz=timezone.utc).strftime('%d%H%MZ')} {wind_dir:03d}{wind_speed:02d}KT ...",
        )
        self._metar_cache[icao] = obs
        return obs

    def get_taf(self, icao: str) -> TafForecast:
        icao = icao.upper()
        if icao in self._taf_cache:
            return self._taf_cache[icao]
        h = _stable_hash(icao + "taf")
        valid_from = datetime.now(tz=timezone.utc)
        valid_to = valid_from + timedelta(hours=24)
        taf = TafForecast(
            icao=icao,
            valid_from=valid_from,
            valid_to=valid_to,
            raw=f"TAF {icao} {valid_from.strftime('%d%H%M')}Z ...",
            forecast_periods=[
                {"from": valid_from.isoformat(), "to": valid_to.isoformat(), "wind_dir_deg": h % 360, "wind_speed_kts": 5 + (h // 360) % 20},
            ],
        )
        self._taf_cache[icao] = taf
        return taf

    def get_wind_at(
        self, latitude: float, longitude: float, altitude_ft: int, valid_at: datetime
    ) -> tuple[float, float, float]:
        # Stable synthetic winds: based on altitude and lat/lon
        key = f"{latitude:.2f},{longitude:.2f},{altitude_ft // 1000}"
        h = _stable_hash(key)
        direction = (h % 360)
        speed = 10 + (h // 360) % 80 + (altitude_ft // 1000) * 1.5
        # Temperature: ISA at altitude, plus a small offset
        from aviation_units import isa_temp_at_altitude

        isa = isa_temp_at_altitude(altitude_ft)
        temp = isa - (h // 17 % 6) - 2
        return float(direction), float(speed), float(temp)


_default_provider: WeatherProvider | None = None


def get_default_provider() -> WeatherProvider:
    global _default_provider
    if _default_provider is None:
        _default_provider = LocalWeatherProvider()
    return _default_provider


def persist_weather_snapshot(
    db, provider: WeatherProvider, icaos: Iterable[str], valid_at: datetime
) -> list[WeatherReport]:
    saved: list[WeatherReport] = []
    for icao in icaos:
        metar = provider.get_metar(icao)
        taf = provider.get_taf(icao)
        report = WeatherReport(
            airport_icao=icao,
            source=provider.name,
            observed_at=metar.observed_at,
            valid_from=taf.valid_from,
            valid_to=taf.valid_to,
            metar_raw=metar.raw,
            taf_raw=taf.raw,
            parsed={"metar": metar.to_dict(), "taf": taf.to_dict()},
        )
        db.add(report)
        saved.append(report)
    db.flush()
    return saved


def persist_winds(
    db, provider: WeatherProvider, points: list[tuple[float, float, int]], valid_at: datetime
) -> WindsAloftReport:
    data: dict = {}
    for lat, lon, alt in points:
        d, s, t = provider.get_wind_at(lat, lon, alt, valid_at)
        data[f"{lat:.2f},{lon:.2f},{alt}"] = {"dir": d, "spd": s, "temp_c": t}
    report = WindsAloftReport(
        valid_from=valid_at,
        valid_to=valid_at + timedelta(hours=6),
        source=provider.name,
        data=data,
    )
    db.add(report)
    db.flush()
    return report
