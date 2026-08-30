import { Link } from 'react-router-dom';
import { useFlightPlans } from '../lib/queries';
import { formatIso } from '../lib/format';

export default function FlightPlans() {
  const plans = useFlightPlans();

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex items-end justify-between mb-4">
        <div>
          <h1 className="text-2xl font-semibold">Flight Plans</h1>
          <div className="text-sm text-slate-400">{plans.data?.length ?? 0} total</div>
        </div>
        <Link to="/flight-plans/new" className="btn-primary">
          + New Flight Plan
        </Link>
      </div>
      <div className="bg-bg-panel border border-bg-line rounded-md">
        <table className="w-full od-table">
          <thead>
            <tr>
              <th>Status</th>
              <th>Callsign</th>
              <th>Dep</th>
              <th>Arr</th>
              <th>Alt</th>
              <th>Aircraft</th>
              <th>Scheduled off-block</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {plans.data?.map((p) => (
              <tr key={p.id} onClick={() => (window.location.href = `/flight-plans/${p.id}`)} className="cursor-pointer">
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
                <td className="text-xs">{formatIso(p.created_at)}</td>
              </tr>
            ))}
            {plans.data?.length === 0 && (
              <tr>
                <td colSpan={8} className="text-center text-slate-500 py-8">
                  No flight plans yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
