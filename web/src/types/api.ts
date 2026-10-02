/**
 * Strict TypeScript models for Kerala River Basin Flood Early Warning API.
 * Strict empirical governance: continuous risk scores [0.0, 1.0].
 */

export interface SystemStatus {
  status: string;
  uptime_seconds: number;
  model_version: string;
  last_refresh: string;
  freshness_status: string;
}

export interface ZoneItem {
  slug: string;
  name: string;
  district: string;
  latitude: number;
  longitude: number;
  river_basin: string;
  hydrological_type: string;
  zone_status: 'validated' | 'provisional' | 'no_validated_model';
  has_validated_model: boolean;
}

export interface WeatherObservations {
  rain_yesterday_mm: number;
  rain_3d_sum_mm: number;
  rain_7d_sum_mm: number;
  soil_moisture_0_7cm: number;
  soil_moisture_7_28cm: number;
}

export interface ExperimentalLeadDay {
  lead_day: number;
  forecast_rainfall_mm: number;
  projected_risk_score: number;
  projected_alert_level: 'ALERT' | 'NORMAL';
}

export interface ZonePrediction {
  zone_slug: string;
  zone_name: string;
  zone_status: 'validated' | 'provisional' | 'no_validated_model';
  status: 'ok' | 'insufficient_data' | 'unvalidated_zone';
  risk_score: number | null;
  warning_flag: boolean | null;
  danger_flag: boolean | null;
  alert_level: 'ALERT' | 'NORMAL' | null;
  weather?: WeatherObservations | null;
  reliability_note?: string | null;
  data_as_of: string;
  model_version: string;
  experimental_outlook_days_1_to_3?: ExperimentalLeadDay[];
}

export interface WhatIfResponse {
  zone_slug: string;
  extra_rain_mm_requested: number;
  extra_rain_mm_applied: number;
  slider_max_bound_mm: number;
  base_risk_score: number;
  simulated_risk_score: number;
  simulated_warning_flag: boolean;
  simulated_danger_flag: boolean;
  simulated_alert_level: 'ALERT' | 'NORMAL';
  saturation_note?: string | null;
}

export interface PrecisionRecallAuditRow {
  dataset: string;
  zone: string;
  target: string;
  threshold: number;
  total_samples: number;
  positives: number;
  caught_events: number;
  total_events: number;
  event_rec: number;
  tp_days: number;
  fp_days: number;
  total_alert_episodes: number;
  ep_prec: number;
  day_prec: number;
  day_rec: number;
  f1: number;
}

export interface ZoneYearRecord {
  zone: string;
  year: number;
  total_days: number;
  warning_exceedances: number;
  danger_exceedances: number;
}

export interface MetricsResponse {
  precision_recall_audit: PrecisionRecallAuditRow[];
  dataset_per_zone_year: ZoneYearRecord[];
}

export interface HistoryRecord {
  id: number;
  timestamp: string;
  zone_slug: string;
  risk_score: number | null;
  warning_flag: number | null;
  danger_flag: number | null;
  alert_level: string | null;
  is_stale: number;
  status: string;
}
