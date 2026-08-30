import { useState } from 'react';
import toast from 'react-hot-toast';
import { useParseRoute } from '../lib/queries';
import { extractError } from '../lib/api';
import { formatNm } from '../lib/format';

interface RouteLeg {
  sequence: number;
  ident: string;
  leg_type: string;
  airway?: string;
  latitude?: number;
  longitude?: number;
  course_deg?: number;
  segment_distance_nm?: number;
  cumulative_distance_nm?: number;
}

interface RouteParseResult {
  legs: RouteLeg[];
  total_distance_nm: number;
  errors: string[];
}

type ValidationState =
  | { kind: 'ok'; data: RouteParseResult }
  | { kind: 'error'; data: ReturnType<typeof extractError> }
  | null;

export default function Routes() {
  const [route, setRoute] = useState('VABB DCT BOM A466 GADIN A466 DEL DCT VIDP');
  const [validation, setValidation] = useState<ValidationState>(null);
  const [submitting, setSubmitting] = useState(false);
  const parse = useParseRoute();

  const onValidate = async () => {
    setSubmitting(true);
    try {
      const r = (await parse.mutateAsync(route)) as RouteParseResult;
      setValidation({ kind: 'ok', data: r });
    } catch (e) {
      const err = extractError(e);
      toast.error(err.message);
      setValidation({ kind: 'error', data: err });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-semibold mb-4">Route Tools</h1>
      <p className="text-sm text-slate-400 mb-4">
        Parse and validate ICAO route strings against the active AIRAC cycle. Use the parser to test
        fix and airway existence and compute geometry.
      </p>
      <div className="bg-bg-panel border border-bg-line rounded-md p-4 space-y-3">
        <label className="label">Route string</label>
        <textarea
          className="input font-mono"
          rows={3}
          value={route}
          onChange={(e) => setRoute(e.target.value.toUpperCase())}
        />
        <div className="flex gap-2">
          <button onClick={onValidate} disabled={submitting} className="btn-primary">
            {submitting ? 'Parsing…' : 'Parse & validate'}
          </button>
        </div>
        {validation && (
          <div>
            {validation.kind === 'ok' && (
              <>
                <div className="text-sm text-slate-300 mb-2">
                  Total distance:{' '}
                  <span className="font-mono">{formatNm(validation.data.total_distance_nm)}</span> ·{' '}
                  {validation.data.legs.length} legs · {validation.data.errors.length} parse errors
                </div>
                <table className="w-full od-table text-xs">
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
                    {validation.data.legs.map((l: RouteLeg, i: number) => (
                      <tr key={i}>
                        <td>{l.sequence}</td>
                        <td className="font-mono">{l.ident}</td>
                        <td>{l.leg_type}</td>
                        <td>{l.airway || '—'}</td>
                        <td>{l.latitude?.toFixed(2) ?? '—'}</td>
                        <td>{l.longitude?.toFixed(2) ?? '—'}</td>
                        <td>{l.course_deg?.toFixed(0) ?? '—'}</td>
                        <td>{l.segment_distance_nm?.toFixed(1) ?? '—'}</td>
                        <td>{l.cumulative_distance_nm?.toFixed(1) ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {validation.data.errors.length > 0 && (
                  <div className="mt-3 space-y-1">
                    {validation.data.errors.map((e: string, i: number) => (
                      <div key={i} className="bann-warn text-xs">
                        {e}
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
