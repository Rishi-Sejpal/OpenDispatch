"""Unit conversion utilities. All functions are pure and deterministic."""

from __future__ import annotations

# Conversions
# Each constant is named `<UNIT_A>_PER_<UNIT_B>` meaning 1 unit_B == constant unit_A.
KM_PER_NM = 1.852  # 1 NM = 1.852 km
NM_PER_KM = 1 / KM_PER_NM
FT_PER_M = 3.280839895  # 1 m = 3.280839895 ft
M_PER_FT = 1 / FT_PER_M
LB_PER_KG = 2.20462262185  # 1 kg = 2.2046 lb
KG_PER_LB = 1 / LB_PER_KG
L_PER_GAL = 3.785411784  # 1 US gal = 3.785 L
GAL_PER_L = 1 / L_PER_GAL
KMH_PER_KT = 1.852  # 1 kt = 1.852 km/h
KT_PER_KMH = 1 / KMH_PER_KT
KTS_PER_MACH = 661.47  # at sea level, ISA; varies with altitude but useful approximation

# Aviation-specific
ISA_SEA_LEVEL_TEMP_C = 15.0
ISA_TROPOPAUSE_FT = 36089
ISA_LAPSE_RATE_C_PER_FT = 0.0019812  # ~2°C per 1000ft below tropopause
EARTH_RADIUS_NM = 3440.065


def nm_to_km(nm: float) -> float:
    return nm * KM_PER_NM


def km_to_nm(km: float) -> float:
    return km * NM_PER_KM


def ft_to_m(ft: float) -> float:
    return ft * M_PER_FT


def m_to_ft(m: float) -> float:
    return m * FT_PER_M


def kg_to_lb(kg: float) -> float:
    return kg * LB_PER_KG


def lb_to_kg(lb: float) -> float:
    return lb * KG_PER_LB


def gal_to_l(g: float) -> float:
    return g * L_PER_GAL


def l_to_gal(l: float) -> float:
    return l * GAL_PER_L


def kt_to_kmh(kt: float) -> float:
    return kt * KMH_PER_KT


def kmh_to_kt(kmh: float) -> float:
    return kmh * KT_PER_KMH


def c_to_f(c: float) -> float:
    return c * 9 / 5 + 32


def f_to_c(f: float) -> float:
    return (f - 32) * 5 / 9


def hpa_to_inhg(hpa: float) -> float:
    return hpa * 0.0295299830714


def inhg_to_hpa(inhg: float) -> float:
    return inhg / 0.0295299830714


def isa_temp_at_altitude(altitude_ft: float) -> float:
    """ISA temperature in °C at given pressure altitude (ft)."""
    if altitude_ft <= ISA_TROPOPAUSE_FT:
        return ISA_SEA_LEVEL_TEMP_C - ISA_LAPSE_RATE_C_PER_FT * altitude_ft
    tropopause_temp = ISA_SEA_LEVEL_TEMP_C - ISA_LAPSE_RATE_C_PER_FT * ISA_TROPOPAUSE_FT
    return tropopause_temp


def mach_to_tas_kts(mach: float, altitude_ft: float) -> float:
    """Convert Mach number to TAS in knots.

    Speed of sound: a = sqrt(gamma * R * T) where gamma=1.4, R=287.0528 J/(kg*K).
    At ISA sea level (T=288.15K), a = 340.29 m/s.
    """
    t_c = isa_temp_at_altitude(altitude_ft)
    t_k = t_c + 273.15
    speed_of_sound_mps = (1.4 * 287.0528 * t_k) ** 0.5  # m/s
    speed_of_sound_kt = speed_of_sound_mps / 0.5144444  # m/s -> kt
    return mach * speed_of_sound_kt


def tas_to_mach(tas_kts: float, altitude_ft: float) -> float:
    t_c = isa_temp_at_altitude(altitude_ft)
    t_k = t_c + 273.15
    speed_of_sound_kt = ((1.4 * 287.0528 * t_k) ** 0.5) / 0.5144444
    if speed_of_sound_kt <= 0:
        return 0.0
    return tas_kts / speed_of_sound_kt


def flight_level_to_altitude_ft(fl: int | float) -> int:
    return int(fl) * 100


def altitude_to_flight_level(altitude_ft: float) -> int:
    return int(round(altitude_ft / 100))


def format_nm(value: float, decimals: int = 1) -> str:
    return f"{value:,.{decimals}f} NM"


def format_kg(value: float, decimals: int = 0) -> str:
    return f"{value:,.{decimals}f} kg"


def format_lb(value: float, decimals: int = 0) -> str:
    return f"{value:,.{decimals}f} lb"


def format_ft(value: float, decimals: int = 0) -> str:
    return f"{value:,.{decimals}f} ft"


def format_kt(value: float, decimals: int = 0) -> str:
    return f"{value:,.{decimals}f} kt"
