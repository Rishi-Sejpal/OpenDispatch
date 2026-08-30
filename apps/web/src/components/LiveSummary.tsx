import type { FlightPlan } from '../lib/types';
import { formatDuration, formatKg, formatLb, formatNm, formatKt } from '../lib/format';

export function LiveSummary({ plan, cycle }: { plan: FlightPlan | null; cycle: string }) {
  if (!plan) {
    return (
      <div className="bg-bg-panel border border-bg-line rounded-md p-4 text-sm text-slate-500">
        Create the draft to see live calculations.
      </div>
    );
  }
  const c = plan.calculation;
  const f = plan.fuel;
  const w = plan.weights;
  const cell = (label: string, value: string, unit?: string) => (
    <div>
      <div className="text-[10px] uppercase text-slate-400 tracking-wider">{label}</div>
      <div className="text-base font-mono">{value}</div>
      {unit && <div className="text-[10px] text-slate-500">{unit}</div>}
    </div>
  );
  return (
    <div className="bg-bg-panel border border-bg-line rounded-md p-4 sticky top-4">
      <div className="text-[10px] uppercase text-slate-400 tracking-wider mb-2">Live summary</div>
      <div className="grid grid-cols-2 gap-3">
        {cell('Distance', c ? formatNm(c.total_distance_nm) : '—')}
        {cell('ETE', c ? formatDuration(c.estimated_time_enroute_seconds) : '—')}
        {cell('Trip fuel', f ? formatKg(f.trip_kg) : '—', f ? formatLb(f.trip_kg) : undefined)}
        {cell('Block fuel', f ? formatKg(f.block_kg) : '—', f ? formatLb(f.block_kg) : undefined)}
        {cell('Cruise altitude', `FL${Math.round(plan.cruise_altitude_ft / 100)}`)}
        {cell('Avg ground speed', c ? formatKt(c.average_ground_speed_kts) : '—')}
        {cell('TOW', w ? formatKg(w.tow_kg) : '—')}
        {cell('Landing weight', w ? formatKg(w.lw_kg) : '—')}
        {cell('ZFW', w ? formatKg(w.zfw_kg) : '—')}
        {cell('AIRAC cycle', cycle)}
      </div>
    </div>
  );
}
