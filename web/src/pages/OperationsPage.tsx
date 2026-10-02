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
  const pred = predictions[selectedZoneSlug] || null;

  // Prepare data for the mini risk trajectory chart
  const basinHistory = historyLogs
    .filter((h) => h.zone_slug === selectedZoneSlug && h.risk_score !== null)
    .slice(-10)
    .map((h, i) => ({
      step: `T-${10 - i}`,
      score: h.risk_score,
    }));

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

            {/* Risk Score Dynamics Card */}
            <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-card transition-all hover:shadow-elevated">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-sky-600" />
                  <h3 className="text-sm font-semibold tracking-tight text-slate-900">
                    Risk Score Trajectory
                  </h3>
                </div>
                <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">
                  Logged Inferences
                </span>
              </div>

              {basinHistory.length > 0 ? (
                <div className="mt-3.5 h-44 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                      data={basinHistory}
                      margin={{ top: 8, right: 10, left: -25, bottom: 0 }}
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
                        tick={{ fontSize: 10, fill: '#64748b' }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <YAxis
                        domain={[0, 1]}
                        tick={{ fontSize: 10, fill: '#94a3b8' }}
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
                <div className="flex h-44 flex-col items-center justify-center text-center text-xs text-slate-400">
                  <p>Continuous inference logging active.</p>
                  <p className="mt-1 text-[11px] text-slate-400">
                    Live risk score trajectory will chart as inferences stream in.
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
