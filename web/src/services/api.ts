import axios from 'axios';
import type {
  SystemStatus,
  ZoneItem,
  ZonePrediction,
  WhatIfResponse,
  MetricsResponse,
  HistoryRecord,
} from '../types/api.ts';

const API_BASE_URL =
  (import.meta as unknown as { env: Record<string, string> }).env?.VITE_API_BASE_URL || '/api';

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60s to accommodate cloud cold starts
});

export const api = {
  async getStatus(): Promise<SystemStatus> {
    const res = await client.get<SystemStatus>('/status');
    return res.data;
  },

  async getZones(): Promise<ZoneItem[]> {
    const res = await client.get<ZoneItem[]>('/zones');
    return res.data;
  },

  async getPrediction(zoneSlug: string): Promise<ZonePrediction> {
    const res = await client.get<ZonePrediction>(`/predict/${zoneSlug}`);
    return res.data;
  },

  async getWhatIf(zoneSlug: string, extraRainMm: number): Promise<WhatIfResponse> {
    const res = await client.get<WhatIfResponse>('/whatif', {
      params: {
        zone_slug: zoneSlug,
        extra_rain_mm: extraRainMm,
      },
    });
    return res.data;
  },

  async getMetrics(): Promise<MetricsResponse> {
    const res = await client.get<MetricsResponse>('/metrics');
    return res.data;
  },

  async getHistory(zoneSlug?: string, limit = 100): Promise<HistoryRecord[]> {
    const res = await client.get<HistoryRecord[]>('/history', {
      params: {
        zone_slug: zoneSlug || undefined,
        limit,
      },
    });
    return res.data;
  },
};
