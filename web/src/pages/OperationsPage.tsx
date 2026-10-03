import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { TrendingUp } from 'lucide-react';
import type { ZoneItem, ZonePrediction, HistoryRecord } from '../types/api.ts';
import { BasinMap } from '../components/BasinMap.tsx';
import { DetailOverview } from '../components/DetailOverview.tsx';
import { TimeHorizonOutlook } from '../components/TimeHorizonOutlook.tsx';
import { PrecipitationOverview } from '../components/PrecipitationOverview.tsx';
import { RegionalExtremes } from '../components/RegionalExtremes.tsx';

interface OperationsPageProps {
  zones: ZoneItem[];
  predictions: Record<string, ZonePrediction>;
  selectedZoneSlug: string;
  onSelectZone: (slug: string) => void;
  onNavigateToWhatIf: () => void;
  historyLogs: HistoryRecord[];
}

export const OperationsPage: React.FC<OperationsPageProps> = ({
  zones,
  predictions,
  selectedZoneSlug,
  onSelectZone,
  onNavigateToWhatIf,
  historyLogs,
}) => {
  const selectedZone = zones.find((z) => z.slug === selectedZoneSlug) || zones[0];
  const pred = selectedZone ? (predictions[selectedZone.slug] || null) : null;

  // Prepare data for the mini risk trajectory chart
  const basinHistory = historyLogs
    .filter((h) => selectedZone && h.zone_slug === selectedZone.slug && h.risk_score !== null)
    .slice(-10)
    .map((h, i) => ({
      step: `T-${10 - i}`,
      score: h.risk_score,
    }));

  if (!selectedZone || zones.length === 0) {
    return (
      <div className="flex h-64 flex-col items-center justify-center rounded-2xl border border-slate-200 bg-white p-6 text-center text-slate-500">
        <div className="h-7 w-7 animate-spin rounded-full border-2 border-sky-600 border-t-transparent" />
        <p className="mt-3 font-semibold text-sm text-slate-700">Connecting to telemetry network...</p>
        <p className="mt-1 text-xs text-slate-400">Initializing monitored Kerala river basins.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 2-Column Responsive Layout Matching GeoAether */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Left Column: Interactive Map + Lower Widgets (approx 65%) */}
        <div className="space-y-6 lg:col-span-7 xl:col-span-8">
          {/* Main Leaflet Map Card */}
          <BasinMap
            zones={zones}
            predictions={predictions}
            selectedZoneSlug={selectedZoneSlug}
            onSelectZone={onSelectZone}
          />

          {/* Lower Grid: Regional Extremes + Risk Score Trend */}
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <RegionalExtremes
              zone={selectedZone}
              prediction={pred}
              onLaunchSensitivity={onNavigateToWhatIf}
            />

            {/* Risk Score Dynamics or Basin Telemetry Profile */}
            <div className="rounded-2xl border border-slate-200/90 bg-white p-4 shadow-card transition-all hover:shadow-elevated">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-sky-600" />
                  <h3 className="text-sm font-semibold tracking-tight text-slate-900">
                    {selectedZone.zone_status === 'no_validated_model'
                      ? 'Basin Telemetry Profile'
                      : 'Risk Score Trajectory'}
                  </h3>
                </div>
                <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">
                  {selectedZone.zone_status === 'no_validated_model' ? 'ERA5 + CWC Station' : 'Logged Inferences'}
                </span>
              </div>

              {selectedZone.zone_status === 'no_validated_model' ? (
                /* Rich Telemetry & Catchment Profile for Unvalidated Basins */
                <div className="mt-3 space-y-2.5 text-xs">
                  <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-2.5">
                    <div className="flex items-center justify-between text-slate-600">
                      <span className="text-[10px] font-semibold uppercase text-slate-400">River Basin</span>
                      <strong className="text-slate-800">{selectedZone.river_basin}</strong>
                    </div>
                    <div className="mt-1 flex items-center justify-between text-slate-600">
                      <span className="text-[10px] font-semibold uppercase text-slate-400">Monitoring Station</span>
                      <strong className="text-slate-800 font-mono text-[11px]">{selectedZone.name}</strong>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-center">
                    <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-2">
                      <span className="text-[9px] font-semibold uppercase text-slate-400 block">Operational Tier</span>
                      <span className="font-bold text-slate-700 text-xs mt-0.5 inline-block">Weather Only</span>
                    </div>
                    <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-2">
                      <span className="text-[9px] font-semibold uppercase text-slate-400 block">ERA5 Grid</span>
                      <span className="font-mono text-xs font-semibold text-slate-700 mt-0.5 inline-block">
                        {selectedZone.latitude.toFixed(2)}°N, {selectedZone.longitude.toFixed(2)}°E
                      </span>
                    </div>
                  </div>

                  <div className="rounded-lg bg-amber-50/80 border border-amber-200/80 px-2.5 py-1.5 text-[10px] text-amber-800">
                    Continuous weather monitoring active. Risk scoring suppressed per pre-registered validation protocol.
                  </div>
                </div>
              ) : basinHistory.length > 0 ? (
                <div className="mt-2.5 h-40 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                      data={basinHistory}
                      margin={{ top: 6, right: 10, left: -25, bottom: 0 }}
                    >
                      <defs>
                        <linearGradient id="scoreGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.35} />
                          <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0.0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                      <XAxis
                        dataKey="step"
                        tick={{ fontSize: 9, fill: '#64748b' }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <YAxis
                        domain={[0, 1]}
                        tick={{ fontSize: 9, fill: '#94a3b8' }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Tooltip
                        formatter={(val: number) => [val.toFixed(4), 'Risk Score']}
                        contentStyle={{
                          backgroundColor: 'rgba(255, 255, 255, 0.95)',
                          borderRadius: '8px',
                          border: '1px solid #e2e8f0',
                          fontSize: '11px',
                          boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
                        }}
                      />
                      <Area
                        type="monotone"
                        dataKey="score"
                        stroke="#0284c7"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#scoreGrad)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="flex h-40 flex-col items-center justify-center text-center text-xs text-slate-400">
                  <p>Inference logging initialized.</p>
                  <p className="mt-1 text-[11px] text-slate-400">
                    Live risk trajectory will chart as inferences stream in.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Analytical Sidebar (approx 35%) */}
        <div className="space-y-6 lg:col-span-5 xl:col-span-4">
          <DetailOverview zone={selectedZone} prediction={pred} />
          <TimeHorizonOutlook
            prediction={pred}
            onNavigateToWhatIf={onNavigateToWhatIf}
          />
          <PrecipitationOverview weather={pred?.weather} />
        </div>
      </div>
    </div>
  );
};
