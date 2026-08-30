import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import {
  useAirports,
  useProcedures,
  useRegistrations,
  useCreateFlightPlan,
  useCalculateFlightPlan,
  useDispatchFlightPlan,
  useGenerateDocuments,
  useFlightPlan,
} from '../lib/queries';
import { extractError } from '../lib/api';
import { formatKg, formatNm, formatDuration } from '../lib/format';
import { LiveSummary } from '../components/LiveSummary';
import { RouteEditor } from '../components/RouteEditor';

const schema = z.object({
  departure_icao: z.string().min(3),
  arrival_icao: z.string().min(3),
  alternate_icaos: z.array(z.string()).default([]),
  aircraft_registration_id: z.string().nullable().optional(),
  passengers: z.coerce.number().int().min(0).default(0),
  cargo_kg: z.coerce.number().min(0).default(0),
  cruise_altitude_ft: z.coerce.number().int().min(5000).max(50000).default(35000),
  cost_index: z.coerce.number().int().min(0).default(30),
  route_text: z.string().default(''),
  departure_runway_ident: z.string().nullable().optional(),
  arrival_runway_ident: z.string().nullable().optional(),
  sid_id: z.string().nullable().optional(),
  star_id: z.string().nullable().optional(),
  approach_id: z.string().nullable().optional(),
  callsign: z.string().optional(),
  scheduled_off_block: z.string().optional(),
});
type FormData = z.input<typeof schema>;

export default function NewFlightPlan() {
  const nav = useNavigate();
  const [depQuery, setDepQuery] = useState('VABB');
  const [arrQuery, setArrQuery] = useState('VIDP');
  const [depIcao, setDepIcao] = useState<string | null>('VABB');
  const [arrIcao, setArrIcao] = useState<string | null>('VIDP');
  const [planId, setPlanId] = useState<string | null>(null);

  const depAirports = useAirports(depQuery);
  const arrAirports = useAirports(arrQuery);
  const depAirport = useAirportSafe(depIcao);
  const arrAirport = useAirportSafe(arrIcao);
  const depProcedures = useProcedures(depIcao, 'SID');
  const arrProcedures = useProcedures(arrIcao, 'STAR');
  const arrApproaches = useProcedures(arrIcao, 'APPROACH');
  const registrations = useRegistrations();
  const plan = useFlightPlan(planId);
  const create = useCreateFlightPlan();
  const calculate = useCalculateFlightPlan();
  const dispatch = useDispatchFlightPlan();
  const genDocs = useGenerateDocuments();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      departure_icao: 'VABB',
      arrival_icao: 'VIDP',
      cruise_altitude_ft: 35000,
      cost_index: 30,
      passengers: 150,
      cargo_kg: 1200,
      route_text: 'VABB DCT BOM A466 GADIN A466 DEL DCT VIDP',
    },
  });

  const v = watch();

  const onCreate = async (data: FormData) => {
    try {
      const p = await create.mutateAsync({
        departure_icao: data.departure_icao,
        arrival_icao: data.arrival_icao,
        alternate_icaos: data.alternate_icaos,
        aircraft_registration_id: data.aircraft_registration_id || null,
        passengers: data.passengers,
        cargo_kg: data.cargo_kg,
        cruise_altitude_ft: data.cruise_altitude_ft,
        cost_index: data.cost_index,
        route_text: data.route_text,
        departure_runway_ident: data.departure_runway_ident || null,
        arrival_runway_ident: data.arrival_runway_ident || null,
        sid_id: data.sid_id || null,
        star_id: data.star_id || null,
        approach_id: data.approach_id || null,
        callsign: data.callsign || null,
        scheduled_off_block: data.scheduled_off_block || null,
      });
      setPlanId(p.id);
      toast.success('Flight plan created');
    } catch (e) {
      toast.error(extractError(e).message);
    }
  };

  const onCalculate = async () => {
    if (!planId) return;
    try {
      await calculate.mutateAsync(planId);
      toast.success('Calculated');
    } catch (e) {
      toast.error(extractError(e).message);
    }
  };

  const onDispatch = async () => {
    if (!planId) return;
    if (!confirm('Dispatch this flight plan? Dispatched plans are immutable.')) return;
    try {
      await dispatch.mutateAsync(planId);
      toast.success('Dispatched');
    } catch (e) {
      toast.error(extractError(e).message);
    }
  };

  const onGenerate = async () => {
    if (!planId) return;
    try {
      await genDocs.mutateAsync(planId);
      toast.success('Documents generated');
    } catch (e) {
      toast.error(extractError(e).message);
    }
  };

  const onView = () => {
    if (planId) nav(`/flight-plans/${planId}`);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-4 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold">New Flight Plan</h1>
          <div className="text-sm text-slate-400">
            Fill the sections, calculate, then dispatch.
          </div>
        </div>
        <div className="text-xs text-slate-500">
          {plan.data && (
            <>
              <span className="font-mono">{plan.data.id.slice(0, 8)}</span> ·{' '}
              <span className="chip-info">{plan.data.status}</span>
            </>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <form onSubmit={handleSubmit(onCreate)} className="col-span-2 space-y-4">
          {/* Flight */}
          <Section title="Flight">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Callsign</label>
                <input className="input" placeholder="e.g. AIC119" {...register('callsign')} />
              </div>
              <div>
                <label className="label">Scheduled off-block (UTC)</label>
                <input className="input" type="datetime-local" {...register('scheduled_off_block')} />
              </div>
            </div>
          </Section>

          {/* Aircraft */}
          <Section title="Aircraft">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Registration</label>
                <select className="input" {...register('aircraft_registration_id')}>
                  <option value="">— None —</option>
                  {registrations.data?.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.registration} ({r.aircraft_type.icao_type})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">Cost Index</label>
                <input className="input" type="number" {...register('cost_index')} />
              </div>
            </div>
          </Section>

          {/* Payload */}
          <Section title="Payload">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Passengers</label>
                <input className="input" type="number" {...register('passengers')} />
              </div>
              <div>
                <label className="label">Cargo (kg)</label>
                <input className="input" type="number" {...register('cargo_kg')} />
              </div>
            </div>
          </Section>

          {/* Departure / Destination / Alternate */}
          <Section title="Departure / Destination / Alternate">
            <div className="grid grid-cols-2 gap-3">
              <AirportPicker
                label="Departure"
                value={v.departure_icao}
                onChange={(icao) => {
                  setValue('departure_icao', icao);
                  setDepIcao(icao);
                }}
                query={depQuery}
                setQuery={setDepQuery}
                options={depAirports.data || []}
              />
              <AirportPicker
                label="Destination"
                value={v.arrival_icao}
                onChange={(icao) => {
                  setValue('arrival_icao', icao);
                  setArrIcao(icao);
                }}
                query={arrQuery}
                setQuery={setArrQuery}
                options={arrAirports.data || []}
              />
            </div>
            <div className="grid grid-cols-2 gap-3 mt-3">
              <RunwayPicker
                label="Departure runway"
                value={v.departure_runway_ident || ''}
                onChange={(v) => setValue('departure_runway_ident', v || null)}
                runways={depAirport.data?.runways || []}
              />
              <RunwayPicker
                label="Arrival runway"
                value={v.arrival_runway_ident || ''}
                onChange={(v) => setValue('arrival_runway_ident', v || null)}
                runways={arrAirport.data?.runways || []}
              />
            </div>
            <div className="mt-3">
              <label className="label">Alternate ICAOs (comma-separated)</label>
              <input
                className="input"
                placeholder="VABP, VABB"
                defaultValue={v.alternate_icaos?.join(', ') || ''}
                onChange={(e) =>
                  setValue(
                    'alternate_icaos',
                    e.target.value
                      .split(',')
                      .map((s) => s.trim().toUpperCase())
                      .filter(Boolean)
                  )
                }
              />
            </div>
          </Section>

          {/* Procedures */}
          <Section title="Procedures">
            <div className="grid grid-cols-3 gap-3">
              <ProcedurePicker
                label="SID"
                value={v.sid_id || ''}
                onChange={(v) => setValue('sid_id', v || null)}
                options={depProcedures.data || []}
              />
              <ProcedurePicker
                label="STAR"
                value={v.star_id || ''}
                onChange={(v) => setValue('star_id', v || null)}
                options={arrProcedures.data || []}
              />
              <ProcedurePicker
                label="Approach"
                value={v.approach_id || ''}
                onChange={(v) => setValue('approach_id', v || null)}
                options={arrApproaches.data || []}
              />
            </div>
          </Section>

          {/* Route */}
          <Section title="Route">
            <RouteEditor
              value={v.route_text || ''}
              onChange={(r) => setValue('route_text', r)}
            />
          </Section>

          {/* Cruise */}
          <Section title="Cruise">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Cruise altitude (ft)</label>
                <input className="input" type="number" step={1000} {...register('cruise_altitude_ft')} />
              </div>
            </div>
          </Section>

          {/* Actions */}
          <div className="flex gap-2">
            {!planId ? (
              <button type="submit" disabled={create.isPending} className="btn-primary">
                {create.isPending ? 'Creating…' : 'Create draft'}
              </button>
            ) : (
              <>
                <button type="button" onClick={onCalculate} disabled={calculate.isPending} className="btn-primary">
                  {calculate.isPending ? 'Calculating…' : 'Calculate'}
                </button>
                <button type="button" onClick={onGenerate} disabled={genDocs.isPending} className="btn-secondary">
                  {genDocs.isPending ? 'Generating…' : 'Generate documents'}
                </button>
                <button
                  type="button"
                  onClick={onDispatch}
                  disabled={dispatch.isPending || plan.data?.status === 'DISPATCHED'}
                  className="btn-secondary"
                >
                  {plan.data?.status === 'DISPATCHED' ? 'Dispatched ✓' : 'Dispatch'}
                </button>
                <button type="button" onClick={onView} className="btn-ghost">
                  Open detail →
                </button>
              </>
            )}
          </div>
        </form>

        <div className="space-y-3">
          <LiveSummary plan={plan.data ?? null} cycle="2401" />
          {plan.data?.warnings && plan.data.warnings.length > 0 && (
            <div className="bg-bg-panel border border-bg-line rounded-md p-3">
              <div className="text-[10px] uppercase text-slate-400 tracking-wider mb-2">
                Warnings ({plan.data.warnings.length})
              </div>
              <div className="space-y-1">
                {plan.data.warnings.map((w, i) => (
                  <div key={i} className={`bann-${w.severity.toLowerCase()}`}>
                    <div className="font-mono text-[10px]">{w.severity} · {w.code}</div>
                    <div className="text-xs">{w.message}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-bg-panel border border-bg-line rounded-md p-4">
      <h2 className="text-sm font-semibold mb-3 text-slate-200">{title}</h2>
      {children}
    </div>
  );
}

function AirportPicker(props: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  query: string;
  setQuery: (q: string) => void;
  options: { icao: string; name: string; city: string | null }[];
}) {
  return (
    <div>
      <label className="label">{props.label}</label>
      <input
        className="input"
        value={props.query}
        onChange={(e) => {
          props.setQuery(e.target.value.toUpperCase());
          props.onChange(e.target.value.toUpperCase());
        }}
        placeholder="ICAO"
      />
      {props.options.length > 0 && props.query !== props.value && (
        <div className="mt-1 max-h-40 overflow-auto bg-bg-card border border-bg-line rounded text-xs">
          {props.options.slice(0, 5).map((a) => (
            <div
              key={a.icao}
              className="px-2 py-1 cursor-pointer hover:bg-bg-line/40"
              onClick={() => {
                props.setQuery(a.icao);
                props.onChange(a.icao);
              }}
            >
              <span className="font-mono font-semibold">{a.icao}</span> {a.name}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function RunwayPicker(props: {
  label: string;
  value: string;
  onChange: (v: string | null) => void;
  runways: { ident: string; length_ft: number }[];
}) {
  return (
    <div>
      <label className="label">{props.label}</label>
      <select className="input" value={props.value} onChange={(e) => props.onChange(e.target.value || null)}>
        <option value="">— Auto —</option>
        {props.runways.map((r) => (
          <option key={r.ident} value={r.ident}>
            {r.ident} ({Math.round(r.length_ft)} ft)
          </option>
        ))}
      </select>
    </div>
  );
}

function ProcedurePicker(props: {
  label: string;
  value: string;
  onChange: (v: string | null) => void;
  options: { id: string; name: string; runway_ident: string | null }[];
}) {
  return (
    <div>
      <label className="label">{props.label}</label>
      <select className="input" value={props.value} onChange={(e) => props.onChange(e.target.value || null)}>
        <option value="">— None —</option>
        {props.options.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
            {p.runway_ident ? ` (RWY ${p.runway_ident})` : ''}
          </option>
        ))}
      </select>
    </div>
  );
}

function useAirportSafe(icao: string | null) {
  const q = useAirports(icao || '');
  return { data: q.data?.find((a) => a.icao === icao) };
}
