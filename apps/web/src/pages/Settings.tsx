import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { useActiveCycle, useOrganizations } from '../lib/queries';

export default function Settings() {
  const me = useQuery({ queryKey: ['me'], queryFn: async () => (await api.get('/auth/me')).data });
  const cycle = useActiveCycle();
  const orgs = useOrganizations();

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <h1 className="text-2xl font-semibold">Settings</h1>

      <section className="bg-bg-panel border border-bg-line rounded-md p-4">
        <h2 className="font-semibold mb-2">Account</h2>
        <div className="text-sm">
          <div>
            <span className="text-slate-400">Name:</span> {me.data?.full_name}
          </div>
          <div>
            <span className="text-slate-400">Email:</span> {me.data?.email}
          </div>
          <div>
            <span className="text-slate-400">Role:</span>{' '}
            {me.data?.is_superuser ? 'Superuser' : 'Member'}
          </div>
        </div>
      </section>

      <section className="bg-bg-panel border border-bg-line rounded-md p-4">
        <h2 className="font-semibold mb-2">Active AIRAC cycle</h2>
        {cycle.data ? (
          <div className="text-sm">
            <div>
              <span className="text-slate-400">Cycle:</span>{' '}
              <span className="font-mono">{cycle.data.cycle}</span>
            </div>
            <div>
              <span className="text-slate-400">Effective:</span>{' '}
              {formatDate(cycle.data.effective_from)} → {formatDate(cycle.data.effective_to)}
            </div>
            <div>
              <span className="text-slate-400">Source:</span> {cycle.data.source}
            </div>
          </div>
        ) : (
          <div className="text-sm text-slate-500">No active AIRAC cycle. Run the seed script.</div>
        )}
      </section>

      <section className="bg-bg-panel border border-bg-line rounded-md p-4">
        <h2 className="font-semibold mb-2">Organizations</h2>
        {orgs.data?.map((o) => (
          <div key={o.id} className="text-sm py-1 flex justify-between">
            <div>
              <span className="font-semibold">{o.name}</span>{' '}
              <span className="text-slate-500 text-xs">/{o.slug}</span>
            </div>
            <div>
              <span className="chip-info">{o.role}</span>
            </div>
          </div>
        ))}
      </section>

      <section className="bg-bg-panel border border-bg-line rounded-md p-4">
        <h2 className="font-semibold mb-2">About</h2>
        <div className="text-xs text-slate-400 leading-relaxed">
          OpenDispatch v0.1.0 · This software provides planning estimates and is not
          a substitute for certified aircraft performance data, official navigation
          data, ATC clearance, operational control procedures, or legally required
          dispatch systems. See ARCHITECTURE.md and AVIATION_CALCULATIONS.md for
          details on the simplified models used.
        </div>
      </section>
    </div>
  );
}

function formatDate(s: string) {
  return new Date(s).toISOString().slice(0, 10);
}
