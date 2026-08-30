import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  useFlightPlan,
  useCalculateFlightPlan,
  useDispatchFlightPlan,
  useGenerateDocuments,
  useAirport,
} from '../lib/queries';
import { formatDuration, formatIso, formatKg, formatNm, formatKt, formatFt } from '../lib/format';
import { FlightMap } from '../components/FlightMap';
import toast from 'react-hot-toast';
import { extractError } from '../lib/api';
import { LiveSummary } from '../components/LiveSummary';

type Tab =
  | 'summary'
  | 'route'
  | 'navlog'
  | 'fuel'
  | 'weights'
  | 'weather'
  | 'procedures'
  | 'warnings'
  | 'documents';

export default function FlightPlanDetail() {
  const { id } = useParams<{ id: string }>();
  const [tab, setTab] = useState<Tab>('summary');
  const plan = useFlightPlan(id || null);
  const calculate = useCalculateFlightPlan();
  const dispatch = useDispatchFlightPlan();
  const genDocs = useGenerateDocuments();
  const dep = useAirport(plan.data?.departure_icao || null);
  const arr = useAirport(plan.data?.arrival_icao || null);

  if (plan.isLoading) return <div className="p-8 text-slate-500">Loading…</div>;
  if (!plan.data) return <div className="p-8 text-slate-500">Not found</div>;

  const p = plan.data;
  const critical = p.warnings.filter((w) => w.severity === 'CRITICAL').length;

  const onCalculate = async () => {
    try {
      await calculate.mutateAsync(p.id);
      toast.success('Calculated');
    } catch (e) {
      toast.error(extractError(e).message);
    }
  };
  const onDispatch = async () => {
    if (!confirm('Dispatch? Dispatched plans are immutable.')) return;
    try {
      await dispatch.mutateAsync(p.id);
      toast.success('Dispatched');
    } catch (e) {
      toast.error(extractError(e).message);
    }
  };
  const onGen = async () => {
    try {
      await genDocs.mutateAsync(p.id);
      toast.success('Documents generated');
    } catch (e) {
      toast.error(extractError(e).message);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-4 flex items-end justify-between">
        <div>
          <Link to="/flight-plans" className="text-xs text-accent hover:underline">
            ← Flight plans
          </Link>
          <h1 className="text-2xl font-semibold">
            {p.callsign || p.departure_icao + ' → ' + p.arrival_icao}
          </h1>
          <div className="text-sm text-slate-400">
            <span className="font-mono">{p.id.slice(0, 8)}</span> ·{' '}
            <span className="chip-info">{p.status}</span> · AIRAC {p.airac_cycle} · engine v
            {p.calculation_engine_version}
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onCalculate}
            disabled={calculate.isPending || p.status === 'DISPATCHED'}
            className="btn-secondary"
          >
            Recalculate
          </button>
          <button onClick={onGen} disabled={genDocs.isPending} className="btn-secondary">
            Generate PDFs
          </button>
          <button
            onClick={onDispatch}
            disabled={dispatch.isPending || p.status === 'DISPATCHED' || critical > 0}
            className="btn-primary"
          >
            {p.status === 'DISPATCHED' ? 'Dispatched ✓' : 'Dispatch'}
          </button>
        </div>
      </div>

      {critical > 0 && (
        <div className="bann-critical mb-3">
          <strong>Critical warnings present.</strong> Resolve before dispatch.
        </div>
      )}

      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2">
          <div className="bg-bg-panel border border-bg-line rounded-md">
            <div className="flex border-b border-bg-line text-sm">
              {(
                [
                  'summary',
                  'route',
                  'navlog',
                  'fuel',
                  'weights',
                  'weather',
                  'procedures',
                  'warnings',
                  'documents',
                ] as Tab[]
              ).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={
                    'px-3 py-2 ' +
                    (tab === t
                      ? 'border-b-2 border-accent text-accent'
                      : 'text-slate-400 hover:text-white')
                  }
                >
                  {t}
                  {t === 'warnings' && p.warnings.length > 0 && (
                    <span className="ml-1 text-[10px] bg-bg-line px-1.5 py-0.5 rounded">
                      {p.warnings.length}
                    </span>
                  )}
                </button>
              ))}
            </div>
            <div className="p-4">
              {tab === 'summary' && <SummaryTab plan={p} />}
              {tab === 'route' && <RouteTab plan={p} />}
              {tab === 'navlog' && <NavLogTab plan={p} />}
              {tab === 'fuel' && <FuelTab plan={p} />}
              {tab === 'weights' && <WeightsTab plan={p} />}
              {tab === 'weather' && <WeatherTab plan={p} />}
              {tab === 'procedures' && <ProceduresTab plan={p} />}
              {tab === 'warnings' && <WarningsTab plan={p} />}
              {tab === 'documents' && <DocumentsTab plan={p} />}
            </div>
          </div>
        </div>
        <div className="space-y-3">
          <LiveSummary plan={p} cycle={p.airac_cycle} />
          <div className="bg-bg-panel border border-bg-line rounded-md overflow-hidden">
            <FlightMap
              legs={p.legs}
              dep={dep.data || null}
              arr={arr.data || null}
              alternates={p.alternate_icaos}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function SummaryTab({ plan }: { plan: import('../lib/types').FlightPlan }) {
  const c = plan.calculation;
  return (
    <div className="grid grid-cols-3 gap-4 text-sm">
      <Field label="Departure" value={plan.departure_icao} />
      <Field label="Destination" value={plan.arrival_icao} />
      <Field label="Alternates" value={plan.alternate_icaos.join(', ') || '—'} />
      <Field label="Departure runway" value={plan.departure_runway_ident || '—'} />
      <Field label="Arrival runway" value={plan.arrival_runway_ident || '—'} />
      <Field label="SID" value={plan.sid_id?.slice(0, 8) || '—'} />
      <Field label="STAR" value={plan.star_id?.slice(0, 8) || '—'} />
      <Field label="Approach" value={plan.approach_id?.slice(0, 8) || '—'} />
      <Field
        label="Aircraft"
        value={plan.aircraft_registration || plan.aircraft_type_icao || '—'}
      />
      <Field label="Cruise altitude" value={formatFt(plan.cruise_altitude_ft)} />
      <Field label="Cost index" value={String(plan.cost_index)} />
      <Field label="Distance" value={c ? formatNm(c.total_distance_nm) : '—'} />
      <Field label="ETE" value={c ? formatDuration(c.estimated_time_enroute_seconds) : '—'} />
      <Field label="Avg GS" value={c ? formatKt(c.average_ground_speed_kts) : '—'} />
      <Field label="Passengers" value={String(plan.passengers)} />
      <Field label="Cargo" value={formatKg(plan.cargo_kg)} />
      <Field label="Scheduled off-block" value={formatIso(plan.scheduled_off_block)} />
      <Field label="Dispatched at" value={formatIso(plan.dispatched_at)} />
      <Field label="Perf version" value={plan.aircraft_performance_version || '—'} />
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase text-slate-400 tracking-wider">{label}</div>
      <div className="font-mono">{value}</div>
    </div>
  );
}

function RouteTab({ plan }: { plan: import('../lib/types').FlightPlan }) {
  return (
    <div>
      <div className="text-[10px] uppercase text-slate-400 tracking-wider mb-1">Route string</div>
      <div className="font-mono bg-bg-card border border-bg-line rounded px-3 py-2 text-sm">
        {plan.route_text || '— (DCT)'}
      </div>
      <table className="w-full od-table mt-3">
        <thead>
          <tr>
            <th>#</th>
            <th>FIX</th>
            <th>Type</th>
            <th>Airway</th>
            <th>Lat</th>
            <th>Lon</th>
            <th>Course</th>
            <th>Dist</th>
            <th>Cum</th>
          </tr>
        </thead>
        <tbody>
          {plan.legs.map((l) => (
            <tr key={l.id}>
              <td>{l.sequence}</td>
              <td className="font-mono">{l.ident}</td>
              <td className="text-xs">{l.leg_type}</td>
              <td className="text-xs">{l.airway || '—'}</td>
              <td className="text-xs">{l.latitude?.toFixed(2) ?? '—'}</td>
              <td className="text-xs">{l.longitude?.toFixed(2) ?? '—'}</td>
              <td className="text-xs">{l.course_deg?.toFixed(0) ?? '—'}</td>
              <td className="text-xs">{l.distance_nm?.toFixed(1) ?? '—'}</td>
              <td className="text-xs">{l.cumulative_distance_nm?.toFixed(1) ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function NavLogTab({ plan }: { plan: import('../lib/types').FlightPlan }) {
  return (
    <table className="w-full od-table text-xs">
      <thead>
        <tr>
          <th>LEG</th>
          <th>FIX</th>
          <th>ALT</th>
          <th>HDG</th>
          <th>DIST</th>
          <th>WIND</th>
          <th>TAS</th>
          <th>GS</th>
          <th>TIME</th>
          <th>FUEL</th>
          <th>REMAIN</th>
        </tr>
      </thead>
      <tbody>
        {plan.legs.map((l) => (
          <tr key={l.id}>
            <td>{l.sequence}</td>
            <td className="font-mono">{l.ident}</td>
            <td>{l.altitude_ft || '—'}</td>
            <td>{l.course_deg?.toFixed(0) || '—'}</td>
            <td>{l.distance_nm?.toFixed(1) || '—'}</td>
            <td>
              {l.wind_direction_deg != null
                ? `${String(l.wind_direction_deg).padStart(3, '0')}/${Math.round(l.wind_speed_kts || 0)}`
                : '—'}
            </td>
            <td>{l.true_air_speed_kts?.toFixed(0) || '—'}</td>
            <td>{l.ground_speed_kts?.toFixed(0) || '—'}</td>
            <td>
              {l.eta_seconds != null
                ? `${String(Math.floor(l.eta_seconds / 3600)).padStart(2, '0')}:${String(Math.floor((l.eta_seconds % 3600) / 60)).padStart(2, '0')}`
                : '—'}
            </td>
            <td>{l.fuel_used_kg?.toFixed(0) || '—'}</td>
            <td>{l.fuel_remaining_kg?.toFixed(0) || '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function FuelTab({ plan }: { plan: import('../lib/types').FlightPlan }) {
  const f = plan.fuel;
  if (!f)
    return <div className="text-slate-500 text-sm">No fuel calculation yet. Click Calculate.</div>;
  return (
    <table className="w-full od-table text-sm">
      <thead>
        <tr>
          <th>Item</th>
          <th>kg</th>
          <th>lb</th>
          <th>USG</th>
        </tr>
      </thead>
      <tbody>
        <Row k="Taxi" v={f.taxi_kg} />
        <Row k="Trip" v={f.trip_kg} />
        <Row k="Contingency" v={f.contingency_kg} />
        <Row k="Alternate" v={f.alternate_kg} />
        <Row k="Final reserve" v={f.final_reserve_kg} />
        <Row k="Additional" v={f.additional_kg} />
        <Row k="Extra" v={f.extra_kg} />
        <tr className="font-semibold bg-bg-card/30">
          <td>Block fuel</td>
          <td className="font-mono">{f.block_kg.toFixed(0)}</td>
          <td className="font-mono">{(f.block_kg * 2.2046).toFixed(0)}</td>
          <td className="font-mono">{(f.block_kg * 0.317).toFixed(0)}</td>
        </tr>
      </tbody>
    </table>
  );
}

function Row({ k, v }: { k: string; v: number }) {
  return (
    <tr>
      <td>{k}</td>
      <td className="font-mono">{v.toFixed(0)}</td>
      <td className="font-mono">{(v * 2.2046).toFixed(0)}</td>
      <td className="font-mono">{(v * 0.317).toFixed(0)}</td>
    </tr>
  );
}

function WeightsTab({ plan }: { plan: import('../lib/types').FlightPlan }) {
  const w = plan.weights;
  if (!w)
    return (
      <div className="text-slate-500 text-sm">No weight calculation yet. Click Calculate.</div>
    );
  return (
    <table className="w-full od-table text-sm">
      <thead>
        <tr>
          <th>Item</th>
          <th>kg</th>
          <th>lb</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>OEW</td>
          <td className="font-mono">{(w.oew_kg || 0).toFixed(0)}</td>
          <td className="font-mono">{((w.oew_kg || 0) * 2.2046).toFixed(0)}</td>
        </tr>
        <tr>
          <td>Payload</td>
          <td className="font-mono">{w.payload_kg.toFixed(0)}</td>
          <td className="font-mono">{(w.payload_kg * 2.2046).toFixed(0)}</td>
        </tr>
        <tr>
          <td>ZFW</td>
          <td className="font-mono">{w.zfw_kg.toFixed(0)}</td>
          <td className="font-mono">{(w.zfw_kg * 2.2046).toFixed(0)}</td>
        </tr>
        <tr>
          <td>TOW</td>
          <td className="font-mono">{w.tow_kg.toFixed(0)}</td>
          <td className="font-mono">{(w.tow_kg * 2.2046).toFixed(0)}</td>
        </tr>
        <tr>
          <td>LW</td>
          <td className="font-mono">{w.lw_kg.toFixed(0)}</td>
          <td className="font-mono">{(w.lw_kg * 2.2046).toFixed(0)}</td>
        </tr>
      </tbody>
    </table>
  );
}

function WeatherTab({ plan: _plan }: { plan: import('../lib/types').FlightPlan }) {
  return (
    <div className="text-sm text-slate-400">
      Weather snapshot is captured at calculation time and stored on the plan. The local provider
      returns deterministic synthetic data so the application works without internet access.
    </div>
  );
}

function ProceduresTab({ plan: _plan }: { plan: import('../lib/types').FlightPlan }) {
  return (
    <div className="text-sm text-slate-400">
      Procedures are stored separately in the navigation database and referenced from the flight
      plan by ID. Browse them under{' '}
      <Link to="/airports" className="text-accent hover:underline">
        Airports
      </Link>
      .
    </div>
  );
}

function WarningsTab({ plan }: { plan: import('../lib/types').FlightPlan }) {
  if (plan.warnings.length === 0) {
    return <div className="text-emerald-300 text-sm">No warnings. Plan is clean.</div>;
  }
  return (
    <div className="space-y-2">
      {plan.warnings.map((w, i) => (
        <div key={i} className={`bann-${w.severity.toLowerCase()}`}>
          <div className="flex justify-between items-baseline">
            <div className="font-mono text-xs">
              [{w.severity}] {w.code}
            </div>
          </div>
          <div className="text-sm">{w.message}</div>
        </div>
      ))}
    </div>
  );
}

function DocumentsTab({ plan }: { plan: import('../lib/types').FlightPlan }) {
  if (plan.documents.length === 0) {
    return (
      <div className="text-sm text-slate-500">
        No documents yet. Click "Generate PDFs" to create OFP, navigation log, fuel summary, and
        weight summary.
      </div>
    );
  }
  return (
    <table className="w-full od-table text-sm">
      <thead>
        <tr>
          <th>Type</th>
          <th>File</th>
          <th>Size</th>
          <th>Created</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {plan.documents.map((d) => (
          <tr key={d.id}>
            <td className="font-mono">{d.doc_type}</td>
            <td className="font-mono text-xs">{d.file_name}</td>
            <td className="text-xs">{(d.size_bytes / 1024).toFixed(1)} KB</td>
            <td className="text-xs">{formatIso(d.created_at)}</td>
            <td>
              <a
                href={`/api/v1/flight-plans/${plan.id}/documents/${d.id}/download`}
                className="text-accent hover:underline text-xs"
                target="_blank"
                rel="noreferrer"
              >
                Download
              </a>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
