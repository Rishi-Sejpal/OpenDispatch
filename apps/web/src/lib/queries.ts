import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from './api';
import type {
  Airport,
  Procedure,
  AiracCycle,
  AircraftType,
  AircraftRegistration,
  FlightPlan,
  FlightPlanSummary,
  Organization,
  Fix,
} from './types';

// Navigation
export function useAirports(query: string) {
  return useQuery({
    queryKey: ['airports', query],
    queryFn: async () => {
      const r = await api.get<Airport[]>('/airports', { params: { q: query, limit: 20 } });
      return r.data;
    },
  });
}

export function useAirport(icao: string | null) {
  return useQuery({
    queryKey: ['airport', icao],
    queryFn: async () => {
      const r = await api.get<Airport>(`/airports/${icao}`);
      return r.data;
    },
    enabled: !!icao,
  });
}

export function useFixes(query: string) {
  return useQuery({
    queryKey: ['fixes', query],
    queryFn: async () => {
      const r = await api.get<Fix[]>('/navigation/fixes', { params: { q: query, limit: 20 } });
      return r.data;
    },
  });
}

export function useProcedures(airport: string | null, kind?: string) {
  return useQuery({
    queryKey: ['procedures', airport, kind],
    queryFn: async () => {
      const r = await api.get<Procedure[]>('/navigation/procedures', { params: { airport, kind } });
      return r.data;
    },
    enabled: !!airport,
  });
}

// AIRAC
export function useActiveCycle() {
  return useQuery({
    queryKey: ['airac', 'active'],
    queryFn: async () => {
      const r = await api.get<AiracCycle>('/airac/cycles/active');
      return r.data;
    },
  });
}

// Aircraft
export function useAircraftTypes() {
  return useQuery({
    queryKey: ['aircraft', 'types'],
    queryFn: async () => {
      const r = await api.get<AircraftType[]>('/aircraft/types');
      return r.data;
    },
  });
}

export function useAircraftType(icao: string | null) {
  return useQuery({
    queryKey: ['aircraft', 'type', icao],
    queryFn: async () => {
      const r = await api.get<AircraftType>(`/aircraft/types/${icao}`);
      return r.data;
    },
    enabled: !!icao,
  });
}

export function useRegistrations() {
  return useQuery({
    queryKey: ['aircraft', 'registrations'],
    queryFn: async () => {
      const r = await api.get<AircraftRegistration[]>('/aircraft/registrations');
      return r.data;
    },
  });
}

// Organizations
export function useOrganizations() {
  return useQuery({
    queryKey: ['organizations'],
    queryFn: async () => {
      const r = await api.get<Organization[]>('/organizations');
      return r.data;
    },
  });
}

// Flight plans
export function useFlightPlans() {
  return useQuery({
    queryKey: ['flight-plans'],
    queryFn: async () => {
      const r = await api.get<FlightPlanSummary[]>('/flight-plans');
      return r.data;
    },
  });
}

export function useFlightPlan(id: string | null) {
  return useQuery({
    queryKey: ['flight-plan', id],
    queryFn: async () => {
      const r = await api.get<FlightPlan>(`/flight-plans/${id}`);
      return r.data;
    },
    enabled: !!id,
    refetchOnMount: 'always',
  });
}

export function useCreateFlightPlan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const r = await api.post<FlightPlan>('/flight-plans', payload);
      return r.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['flight-plans'] }),
  });
}

export function useUpdateFlightPlan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: Record<string, unknown> }) => {
      const r = await api.patch<FlightPlan>(`/flight-plans/${id}`, payload);
      return r.data;
    },
    onSuccess: (d) => qc.invalidateQueries({ queryKey: ['flight-plan', d.id] }),
  });
}

export function useCalculateFlightPlan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const r = await api.post<FlightPlan>(`/flight-plans/${id}/calculate`, {});
      return r.data;
    },
    onSuccess: (d) => qc.invalidateQueries({ queryKey: ['flight-plan', d.id] }),
  });
}

export function useDispatchFlightPlan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const r = await api.post<FlightPlan>(`/flight-plans/${id}/dispatch`, { confirm: true });
      return r.data;
    },
    onSuccess: (d) => qc.invalidateQueries({ queryKey: ['flight-plan', d.id] }),
  });
}

export function useGenerateDocuments() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const r = await api.post<{ documents: { id: string; doc_type: string; file_name: string; size_bytes: number }[] }>(
        `/flight-plans/${id}/documents`,
        {}
      );
      return r.data;
    },
    onSuccess: (d, id) => qc.invalidateQueries({ queryKey: ['flight-plan', id] }),
  });
}

// Weather
export function useWeather(icao: string | null) {
  return useQuery({
    queryKey: ['weather', icao],
    queryFn: async () => {
      const r = await api.get(`/weather/${icao}/metar`);
      return r.data;
    },
    enabled: !!icao,
  });
}

// Route
export function useParseRoute() {
  return useMutation({
    mutationFn: async (route: string) => {
      const r = await api.post<{ legs: unknown[]; total_distance_nm: number; errors: string[] }>(
        '/routes/geometry',
        { route }
      );
      return r.data;
    },
  });
}
