import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from 'recharts';
import { CloudRain, Droplets } from 'lucide-react';
import type { WeatherObservations } from '../types/api.ts';

interface PrecipitationOverviewProps {
  weather: WeatherObservations | null | undefined;
}

export const PrecipitationOverview: React.FC<PrecipitationOverviewProps> = ({
  weather,
}) => {
  if (!weather) {
    return (
      <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-card">
        <h3 className="text-sm font-semibold tracking-tight text-slate-900">
          Precipitation & Moisture Overview
        </h3>
        <p className="mt-4 text-center text-xs text-slate-400">
          Live antecedent precipitation data loading...
        </p>
      </div>
    );
  }

  const chartData = [
    { name: '1-Day (t-1)', value: weather.rain_yesterday_mm, category: 'rain' },
    { name: '3-Day Sum', value: weather.rain_3d_sum_mm, category: 'rain' },
    { name: '7-Day Sum', value: weather.rain_7d_sum_mm, category: 'rain' },
  ];

  return (
    <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-card transition-all hover:shadow-elevated">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <CloudRain className="h-4 w-4 text-sky-600" />
          <h3 className="text-sm font-semibold tracking-tight text-slate-900">
            Precipitation Overview
          </h3>
        </div>
        <span className="text-[10px] font-semibold text-slate-400 font-mono">
          Causal Lag (t-1)
        </span>
      </div>

      {/* Headline Metric */}
      <div className="mt-3 flex items-baseline justify-between">
        <div>
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
            Antecedent Rainfall Yesterday
          </span>
          <div className="flex items-baseline gap-1.5">
            <span className="font-mono text-2xl font-extrabold text-slate-900">
              {weather.rain_yesterday_mm.toFixed(1)}
            </span>
            <span className="text-xs font-semibold text-slate-500">mm</span>
          </div>
        </div>

        <div className="text-right">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
            Topsoil Moisture
          </span>
          <div className="flex items-center justify-end gap-1 text-slate-700">
            <Droplets className="h-3.5 w-3.5 text-blue-500" />
            <span className="font-mono text-sm font-bold">
              {weather.soil_moisture_0_7cm.toFixed(3)}
            </span>
            <span className="text-[10px] text-slate-400">m³/m³</span>
          </div>
        </div>
      </div>

      {/* Bar Chart */}
      <div className="mt-3 h-36 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 8, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10, fill: '#64748b' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 10, fill: '#94a3b8' }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              formatter={(val: number) => [`${val.toFixed(1)} mm`, 'Rainfall']}
              contentStyle={{
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                borderRadius: '8px',
                border: '1px solid #e2e8f0',
                fontSize: '11px',
                boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
              }}
            />
            <Bar dataKey="value" radius={[6, 6, 0, 0]}>
              {chartData.map((_, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={index === 0 ? '#0284c7' : index === 1 ? '#0ea5e9' : '#38bdf8'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-2 flex items-center justify-between text-[10px] text-slate-400 border-t border-slate-100 pt-2">
        <span>Deep Soil (7-28cm): {weather.soil_moisture_7_28cm.toFixed(3)} m³/m³</span>
        <span className="font-medium text-slate-500">ERA5 Reanalysis</span>
      </div>
    </div>
  );
};
