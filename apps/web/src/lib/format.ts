export function formatNm(value: number | null | undefined, decimals = 1): string {
  if (value == null) return '—';
  return `${value.toFixed(decimals)} NM`;
}

export function formatKg(value: number | null | undefined, decimals = 0): string {
  if (value == null) return '—';
  return `${value.toFixed(decimals)} kg`;
}

export function formatLb(value: number | null | undefined, decimals = 0): string {
  if (value == null) return '—';
  return `${(value * 2.20462).toFixed(decimals)} lb`;
}

export function formatFt(value: number | null | undefined): string {
  if (value == null) return '—';
  return `FL${Math.round(value / 100)}`;
}

export function formatKt(value: number | null | undefined, decimals = 0): string {
  if (value == null) return '—';
  return `${value.toFixed(decimals)} kt`;
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null) return '—';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h${m.toString().padStart(2, '0')}m`;
}

export function formatIso(dt: string | null | undefined): string {
  if (!dt) return '—';
  return new Date(dt).toISOString().replace('T', ' ').slice(0, 16) + 'Z';
}

export function formatLatLon(
  lat: number | null | undefined,
  lon: number | null | undefined,
): string {
  if (lat == null || lon == null) return '—';
  const ns = lat >= 0 ? 'N' : 'S';
  const ew = lon >= 0 ? 'E' : 'W';
  return `${Math.abs(lat).toFixed(2)}°${ns} ${Math.abs(lon).toFixed(2)}°${ew}`;
}
