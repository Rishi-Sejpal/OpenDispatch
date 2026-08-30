import { useState } from 'react';
import { useAirports } from '../lib/queries';

export default function Airports() {
  const [q, setQ] = useState('');
  const airports = useAirports(q);

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-semibold mb-4">Airports</h1>
      <input
        className="input mb-4 max-w-md"
        placeholder="Search by ICAO, IATA, name, city…"
        value={q}
        onChange={(e) => setQ(e.target.value.toUpperCase())}
      />
      <div className="bg-bg-panel border border-bg-line rounded-md">
        <table className="w-full od-table">
          <thead>
            <tr>
              <th>ICAO</th>
              <th>IATA</th>
              <th>Name</th>
              <th>City</th>
              <th>Country</th>
              <th>Lat</th>
              <th>Lon</th>
              <th>Elev</th>
            </tr>
          </thead>
          <tbody>
            {airports.data?.map((a) => (
              <tr key={a.id}>
                <td className="font-mono font-semibold">{a.icao}</td>
                <td className="font-mono">{a.iata || '—'}</td>
                <td>{a.name}</td>
                <td>{a.city}</td>
                <td>{a.country}</td>
                <td className="text-xs">{a.latitude.toFixed(2)}</td>
                <td className="text-xs">{a.longitude.toFixed(2)}</td>
                <td className="text-xs">{a.elevation_ft.toFixed(0)} ft</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
