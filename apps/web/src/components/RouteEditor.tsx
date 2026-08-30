import { useEffect, useState } from 'react';
import { useDebounce } from '../hooks/useDebounce';
import { useFixes } from '../lib/queries';

export function RouteEditor({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [tokens, setTokens] = useState<string[]>(value.split(/\s+/).filter(Boolean));
  useEffect(() => {
    setTokens(value.split(/\s+/).filter(Boolean));
  }, [value]);
  const debounced = useDebounce(value, 300);
  const fixes = useFixes(debounced.slice(-5) || '');

  const addToken = (t: string) => {
    if (!t.trim()) return;
    const next = [...tokens, t.trim().toUpperCase()];
    setTokens(next);
    onChange(next.join(' '));
  };
  const removeAt = (i: number) => {
    const next = tokens.filter((_, idx) => idx !== i);
    setTokens(next);
    onChange(next.join(' '));
  };
  const updateAt = (i: number, t: string) => {
    const next = [...tokens];
    next[i] = t.toUpperCase();
    setTokens(next);
    onChange(next.join(' '));
  };
  const move = (i: number, dir: -1 | 1) => {
    const j = i + dir;
    if (j < 0 || j >= tokens.length) return;
    const next = [...tokens];
    [next[i], next[j]] = [next[j], next[i]];
    setTokens(next);
    onChange(next.join(' '));
  };
  const setAll = (txt: string) => {
    onChange(txt);
  };

  return (
    <div className="space-y-2">
      <textarea
        className="input font-mono text-sm"
        rows={2}
        value={value}
        onChange={(e) => setAll(e.target.value)}
        placeholder="VABB DCT BOM A466 GADIN A466 DEL DCT VIDP"
      />
      <div className="flex flex-wrap items-center gap-1">
        {tokens.map((t, i) => (
          <div
            key={i}
            className="flex items-center gap-1 bg-bg-card border border-bg-line rounded px-2 py-1"
          >
            <span className="text-[10px] text-slate-500">{i + 1}</span>
            <input
              className="bg-transparent font-mono text-sm w-24 outline-none"
              value={t}
              onChange={(e) => updateAt(i, e.target.value)}
            />
            <button
              type="button"
              onClick={() => move(i, -1)}
              className="text-slate-500 hover:text-white text-xs"
              title="Move up"
            >
              ↑
            </button>
            <button
              type="button"
              onClick={() => move(i, 1)}
              className="text-slate-500 hover:text-white text-xs"
              title="Move down"
            >
              ↓
            </button>
            <button
              type="button"
              onClick={() => removeAt(i)}
              className="text-rose-400 hover:text-rose-200 text-xs"
              title="Remove"
            >
              ✕
            </button>
          </div>
        ))}
        <button
          type="button"
          onClick={() => addToken('DCT')}
          className="text-xs text-slate-400 hover:text-white border border-dashed border-bg-line rounded px-2 py-1"
        >
          + DCT
        </button>
      </div>
      {fixes.data && fixes.data.length > 0 && (
        <div className="text-xs text-slate-500">
          Suggestions:
          {fixes.data.slice(0, 5).map((f) => (
            <button
              key={f.id}
              type="button"
              onClick={() => addToken(f.ident)}
              className="ml-2 font-mono text-accent hover:underline"
            >
              {f.ident}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
