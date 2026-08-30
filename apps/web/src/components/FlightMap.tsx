import { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import type { Airport, FlightPlanLeg } from '../lib/types';

export function FlightMap({
  legs,
  dep,
  arr,
  alternates,
}: {
  legs: FlightPlanLeg[];
  dep: Airport | null;
  arr: Airport | null;
  alternates: string[];
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: 'raster',
            tiles: [
              'https://a.tile.openstreetmap.org/{z}/{x}/{y}.png',
              'https://b.tile.openstreetmap.org/{z}/{x}/{y}.png',
            ],
            tileSize: 256,
            attribution: '© OpenStreetMap',
          },
        },
        layers: [{ id: 'osm', type: 'raster', source: 'osm' }],
      } as any,
      center: [75, 22],
      zoom: 4,
    });
    map.addControl(new maplibregl.NavigationControl(), 'top-right');
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = () => {
      const points: [number, number][] = [];
      const markers: maplibregl.Marker[] = [];
      const addPoint = (lat: number, lon: number, color: string, label: string) => {
        points.push([lon, lat]);
        const el = document.createElement('div');
        el.style.cssText = `width:14px;height:14px;border-radius:50%;background:${color};border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,.5);font-size:10px;color:white;display:flex;align-items:center;justify-content:center;`;
        el.title = label;
        markers.push(new maplibregl.Marker({ element: el }).setLngLat([lon, lat]).addTo(map));
      };
      if (dep) addPoint(dep.latitude, dep.longitude, '#3ec28f', `Dep ${dep.icao}`);
      if (arr) addPoint(arr.latitude, arr.longitude, '#e25c5c', `Arr ${arr.icao}`);
      legs.forEach((l) => {
        if (l.latitude != null && l.longitude != null) points.push([l.longitude, l.latitude]);
      });

      // draw route line
      if (points.length >= 2) {
        const data: GeoJSON.Feature = {
          type: 'Feature',
          properties: {},
          geometry: { type: 'LineString', coordinates: points },
        };
        const src = map.getSource('route') as maplibregl.GeoJSONSource | undefined;
        if (src) {
          src.setData(data);
        } else {
          map.addSource('route', { type: 'geojson', data });
          map.addLayer({
            id: 'route-line',
            type: 'line',
            source: 'route',
            paint: { 'line-color': '#4f9cff', 'line-width': 3, 'line-opacity': 0.8 },
          });
        }
      }
      if (points.length > 0) {
        const bounds = new maplibregl.LngLatBounds();
        points.forEach((p) => bounds.extend(p));
        map.fitBounds(bounds, { padding: 40, duration: 800 });
      }
    };
    if (map.loaded()) apply();
    else map.once('load', apply);
  }, [legs, dep, arr, alternates]);

  return <div ref={containerRef} style={{ height: 360, width: '100%' }} />;
}
