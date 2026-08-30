import { Link } from 'react-router-dom';
import { useFlightPlans, useActiveCycle } from '../lib/queries';
import { formatIso, formatDuration, formatNm } from '../lib/format';

export default function Dashboard() {
  const plans = useFlightPlans();
  const cycle = useActiveCycle();

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex items-end justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <div className="text-sm text-slate-400">
            OpenDispatch flight planning and dispatch workstation
          </div>
        </div>
        <Link to="/flight-plans/new" className="btn-primary">
          + New Flight Plan
        </Link>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-bg-panel border border-bg-line rounded-md p-4">
          <div className="text-[10px] uppercase text-slate-400 tracking-wider mb-1">Active AIRAC cycle</div>
          <div className="text-2xl font-semibold font-mono">
            {cycle.data?.cycle ?? '—'}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            {cycle.data
              ? `${formatIso(cycle.data.effective_from)} → ${formatIso(cycle.data.effective_to)}`
              : 'No cycle active'}
          </div>
        </div>
        <div className="bg-bg-panel border border-bg-line rounded-md p-4">
          <div className="text-[10px] uppercase text-slate-400 tracking-wider mb-1">Total plans</div>
          <div className="text-2xl font-semibold font-mono">{plans.data?.length ?? '—'}</div>
          <div className="text-xs text-slate-500 mt-1">All organizations you belong to</div>
        </div>
        <div className="bg-bg-panel border border-bg-line rounded-md p-4">
          <div className="text-[10px] uppercase text-slate-400 tracking-wider mb-1">Dispatched</div>
          <div className="text-2xl font-semibold font-mono">
            {plans.data?.filter((p) => p.status === 'DISPATCHED').length ?? '—'}
          </div>
          <div className="text-xs text-slate-500 mt-1">Immutable historical plans</div>
        </div>
      </div>

      <div className="bg-bg-panel border border-bg-line rounded-md">
        <div className="p-4 border-b border-bg-line flex justify-between items-center">
          <h2 className="font-semibold">Recent flight plans</h2>
          <Link to="/flight-plans" className="text-sm text-accent hover:underline">
            View all
          </Link>
        </div>
        <table className="w-full od-table">
          <thead>
            <tr>
              <th>Status</th>
              <th>Callsign</th>
              <th>Dep</th>
              <th>Arr</th>
              <th>Alt</th>
              <th>Aircraft</th>
              <th>Scheduled</th>
            </tr>
          </thead>
          <tbody>
            {plans.data?.slice(0, 10).map((p) => (
              <tr key={p.id} className="cursor-pointer" onClick={() => (window.location.href = `/flight-plans/${p.id}`)}>
                <td>
                  <span
                    className={
                      p.status === 'DISPATCHED'
                        ? 'chip-ok'
                        : p.status === 'DRAFT'
                        ? 'chip-warn'
                        : p.status === 'ARCHIVED'
                        ? 'chip-info'
                        : 'chip-info'
                    }
                  >
                    {p.status}
                  </span>
                </td>
                <td className="font-mono">{p.callsign || '—'}</td>
                <td className="font-mono">{p.departure_icao}</td>
                <td className="font-mono">{p.arrival_icao}</td>
                <td className="text-xs">{p.alternate_icaos.join(', ') || '—'}</td>
                <td className="font-mono text-xs">
                  {p.aircraft_registration || p.aircraft_type_icao || '—'}
                </td>
                <td className="text-xs">{formatIso(p.scheduled_off_block)}</td>
              </tr>
            ))}
            {plans.data?.length === 0 && (
              <tr>
                <td colSpan={7} className="text-center text-slate-500 py-8">
                  No flight plans yet.{' '}
                  <Link to="/flight-plans/new" className="text-accent hover:underline">
                    Create your first.
                  </Link>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-6 text-xs text-slate-500 leading-relaxed">
        <strong className="text-slate-400">Safety notice.</strong> This software provides planning
        estimates and is not a substitute for certified aircraft performance data, official
        navigation data, ATC clearance, operational control procedures, or legally required dispatch
        systems.
      </div>
    </div>
  );
}
