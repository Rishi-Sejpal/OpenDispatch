import { useFlightPlans } from '../lib/queries';
import { formatIso } from '../lib/format';

export default function Documents() {
  const plans = useFlightPlans();

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-semibold mb-4">Documents</h1>
      <p className="text-sm text-slate-400 mb-4">
        OFP, navigation log, fuel summary and weight summary PDFs are generated per flight plan.
        Open a plan to generate and download its documents.
      </p>
      <div className="bg-bg-panel border border-bg-line rounded-md">
        <table className="w-full od-table">
          <thead>
            <tr>
              <th>Plan</th>
              <th>Route</th>
              <th>Status</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {plans.data?.map((p) => (
              <tr
                key={p.id}
                onClick={() => (window.location.href = `/flight-plans/${p.id}`)}
                className="cursor-pointer"
              >
                <td className="font-mono">{p.id.slice(0, 8)}</td>
                <td className="font-mono">
                  {p.departure_icao} → {p.arrival_icao}
                </td>
                <td>
                  <span className="chip-info">{p.status}</span>
                </td>
                <td className="text-xs">{formatIso(p.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
