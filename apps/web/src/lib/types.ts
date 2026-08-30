export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  is_email_verified: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  role: 'OWNER' | 'ADMIN' | 'DISPATCHER' | 'PILOT' | 'VIEWER';
  icao_code: string | null;
  iata_code: string | null;
}

export interface Airport {
  id: string;
  icao: string;
  iata: string | null;
  name: string;
  city: string | null;
  country: string | null;
  latitude: number;
  longitude: number;
  elevation_ft: number;
  has_procedures: boolean;
  magnetic_variation?: number;
  timezone?: string;
  runways?: Runway[];
}

export interface Runway {
  id: string;
  ident: string;
  reciprocal_ident: string | null;
  length_ft: number;
  width_ft: number;
  heading_deg: number;
  surface: string;
  elevation_ft: number;
  ils_available: boolean;
  ils_category: string | null;
  lighting: boolean;
}

export interface Procedure {
  id: string;
  airport_icao: string | null;
  name: string;
  kind: 'SID' | 'STAR' | 'APPROACH';
  runway_ident: string | null;
}

export interface Fix {
  id: string;
  ident: string;
  name: string | null;
  role: string;
  latitude: number;
  longitude: number;
}

export interface AiracCycle {
  id: string;
  cycle: string;
  effective_from: string;
  effective_to: string;
  source: string;
  version: string;
  import_status: string;
  is_active: boolean;
  notes: string | null;
}

export interface AircraftType {
  id: string;
  icao_type: string;
  manufacturer: string;
  model: string;
  variant: string | null;
  wake_category: string;
  engine_type: string;
  engines: number;
  mtow_kg: number;
  passenger_capacity: number;
  mlw_kg?: number;
  mzfw_kg?: number;
  oew_kg?: number;
  fuel_capacity_kg?: number;
  cargo_capacity_kg?: number;
  max_altitude_ft?: number;
  cruise_mach?: number;
  cruise_tas_kts?: number;
  approach_speed_kts?: number;
  initial_climb_alt_ft?: number;
  initial_cruise_alt_ft?: number;
  notes?: string | null;
}

export interface AircraftRegistration {
  id: string;
  registration: string;
  nickname: string | null;
  aircraft_type: AircraftType;
  organization_id: string;
  active: boolean;
}

export interface FlightPlanSummary {
  id: string;
  status: 'DRAFT' | 'VALIDATED' | 'CALCULATED' | 'GENERATED' | 'DISPATCHED' | 'ARCHIVED';
  departure_icao: string;
  arrival_icao: string;
  alternate_icaos: string[];
  aircraft_registration: string | null;
  aircraft_type_icao: string | null;
  callsign: string | null;
  scheduled_off_block: string | null;
  created_at: string;
  updated_at: string;
}

export interface Warning {
  severity: 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
  code: string;
  message: string;
  details: Record<string, unknown>;
}

export interface FlightPlan {
  id: string;
  status: FlightPlanSummary['status'];
  departure_icao: string;
  arrival_icao: string;
  alternate_icaos: string[];
  aircraft_registration: string | null;
  aircraft_type_icao: string | null;
  callsign: string | null;
  scheduled_off_block: string | null;
  created_at: string;
  updated_at: string;
  route_text: string;
  departure_runway_ident: string | null;
  arrival_runway_ident: string | null;
  sid_id: string | null;
  star_id: string | null;
  approach_id: string | null;
  passengers: number;
  cargo_kg: number;
  payload_kg: number;
  cruise_altitude_ft: number;
  cost_index: number;
  fuel_policy: Record<string, unknown>;
  airac_cycle: string;
  calculation_engine_version: string;
  aircraft_performance_version: string | null;
  dispatched_at: string | null;
  legs: FlightPlanLeg[];
  calculation: FlightPlanCalculation | null;
  fuel: FlightPlanFuel | null;
  weights: FlightPlanWeights | null;
  warnings: Warning[];
  documents: Document[];
}

export interface FlightPlanLeg {
  id: string;
  sequence: number;
  ident: string;
  leg_type: string;
  airway: string | null;
  latitude: number | null;
  longitude: number | null;
  course_deg: number | null;
  distance_nm: number | null;
  cumulative_distance_nm: number;
  altitude_ft: number | null;
  speed_kts: number | null;
  wind_direction_deg: number | null;
  wind_speed_kts: number | null;
  true_air_speed_kts: number | null;
  ground_speed_kts: number | null;
  eta_seconds: number | null;
  fuel_used_kg: number | null;
  fuel_remaining_kg: number | null;
}

export interface FlightPlanCalculation {
  total_distance_nm: number;
  estimated_time_enroute_seconds: number;
  average_ground_speed_kts: number;
  cruise_ground_speed_kts: number;
  climb_fuel_kg: number;
  cruise_fuel_kg: number;
  descent_fuel_kg: number;
}

export interface FlightPlanFuel {
  taxi_kg: number;
  trip_kg: number;
  contingency_kg: number;
  alternate_kg: number;
  final_reserve_kg: number;
  additional_kg: number;
  extra_kg: number;
  block_kg: number;
}

export interface FlightPlanWeights {
  oew_kg: number;
  payload_kg: number;
  zfw_kg: number;
  takeoff_fuel_kg: number;
  tow_kg: number;
  landing_fuel_kg: number;
  lw_kg: number;
}

export interface Document {
  id: string;
  doc_type: 'OFP' | 'NAV_LOG' | 'FUEL' | 'WEIGHT';
  file_name: string;
  size_bytes: number;
  created_at: string;
}
