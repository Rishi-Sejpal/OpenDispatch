import { useAircraftTypes, useRegistrations } from '../lib/queries';

export default function Aircraft() {
  const types = useAircraftTypes();
  const regs = useRegistrations();

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <h1 className="text-2xl font-semibold">Aircraft</h1>

      <section>
        <h2 className="text-lg font-semibold mb-2">Types</h2>
        <div className="bg-bg-panel border border-bg-line rounded-md">
          <table className="w-full od-table">
            <thead>
              <tr>
                <th>ICAO</th>
                <th>Manufacturer</th>
                <th>Model</th>
                <th>Engines</th>
                <th>MTOW (kg)</th>
                <th>Pax</th>
                <th>Cruise</th>
              </tr>
            </thead>
            <tbody>
              {types.data?.map((t) => (
                <tr key={t.id}>
                  <td className="font-mono font-semibold">{t.icao_type}</td>
                  <td>{t.manufacturer}</td>
                  <td>{t.model}</td>
                  <td>
                    {t.engines} × {t.engine_type}
                  </td>
                  <td className="font-mono">{t.mtow_kg.toFixed(0)}</td>
                  <td>{t.passenger_capacity}</td>
                  <td className="text-xs">M{t.cruise_mach} / {t.cruise_tas_kts}kt</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-2">Registrations</h2>
        <div className="bg-bg-panel border border-bg-line rounded-md">
          <table className="w-full od-table">
            <thead>
              <tr>
                <th>Registration</th>
                <th>Type</th>
                <th>Nickname</th>
                <th>Organization</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {regs.data?.map((r) => (
                <tr key={r.id}>
                  <td className="font-mono font-semibold">{r.registration}</td>
                  <td className="font-mono text-xs">{r.aircraft_type.icao_type}</td>
                  <td>{r.nickname || '—'}</td>
                  <td className="text-xs font-mono">{r.organization_id.slice(0, 8)}</td>
                  <td>
                    {r.active ? <span className="chip-ok">Active</span> : <span className="chip-warn">Inactive</span>}
                  </td>
                </tr>
              ))}
              {regs.data?.length === 0 && (
                <tr>
                  <td colSpan={5} className="text-center text-slate-500 py-6">
                    No registrations yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
