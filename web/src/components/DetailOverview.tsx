import React from 'react';
import {
  AlertTriangle,
  Info,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react';
import type { ZoneItem, ZonePrediction } from '../types/api.ts';
import { StatusBadge } from './StatusBadge.tsx';

interface DetailOverviewProps {
  zone: ZoneItem;
  prediction: ZonePrediction | null;
  currentTimeString?: string;
}

export const DetailOverview: React.FC<DetailOverviewProps> = ({
  zone,
  prediction,
  currentTimeString = '14:45 IST',
}) => {
  const isAlert = prediction?.alert_level === 'ALERT';
  const hasScore = prediction && prediction.risk_score !== null;

  return (
    <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-card transition-all hover:shadow-elevated">
      {/* Card Header */}
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold tracking-tight text-slate-900">
              Detail Overview
            </h3>
            <StatusBadge status={zone.zone_status} size="sm" />
          </div>
          <p className="text-xs text-slate-500">
            {zone.name} • {zone.river_basin} Basin
          </p>
        </div>
        <div className="text-right">
          <span className="text-[11px] font-medium text-slate-400">Local Time</span>
          <p className="text-xs font-semibold text-slate-700 font-mono">{currentTimeString}</p>
        </div>
      </div>

      {/* Provisional Model Warning Banner */}
      {zone.zone_status === 'provisional' && (
        <div className="mt-3.5 rounded-xl border border-amber-200 bg-amber-50/80 p-3 text-xs text-amber-900">
          <div className="flex items-start gap-2">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
            <div>
              <strong className="block font-semibold">
                PROVISIONAL STATUS, LOW RELIABILITY
              </strong>
              <p className="mt-0.5 text-[11px] leading-relaxed text-amber-800">
                {prediction?.reliability_note ||
                  'Ground-truth CWC telemetry began only in June 2015. Low sample reliability; evaluate counts beside percentages.'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Insufficient Data Banner */}
      {prediction?.status === 'insufficient_data' && (
        <div className="mt-3.5 rounded-xl border border-rose-200 bg-rose-50/80 p-3 text-xs text-rose-900">
          <div className="flex items-start gap-2">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
            <div>
              <strong className="block font-semibold">INSUFFICIENT DATA</strong>
              <p className="mt-0.5 text-[11px] text-rose-800">
                Missing or corrupt weather observations through yesterday (t-1). Risk score calculation suppressed.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Weather Only Banner */}
      {zone.zone_status === 'no_validated_model' && (
        <div className="mt-3.5 rounded-xl border border-slate-200 bg-slate-50/90 p-3 text-xs text-slate-700">
          <div className="flex items-start gap-2">
            <Info className="mt-0.5 h-4 w-4 shrink-0 text-slate-500" />
            <div>
              <strong className="block font-semibold text-slate-800">
                NO VALIDATED MODEL
              </strong>
              <p className="mt-0.5 text-[11px] leading-relaxed text-slate-600">
                Ground-truth hydrological gauge data is unvalidated for operational flood risk modeling in this basin. Live weather monitoring only.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Primary Status & Risk Score Section (Validated or Provisional) */}
      {hasScore && (
        <div className="mt-4 space-y-3.5">
          {/* Main Score Display */}
          <div
            className={`rounded-xl border p-4 transition-all ${
              isAlert
                ? 'border-rose-300 bg-gradient-to-br from-rose-50 via-white to-rose-50/30 text-rose-950 shadow-sm'
                : 'border-emerald-200 bg-gradient-to-br from-emerald-50/70 via-white to-emerald-50/20 text-emerald-950 shadow-sm'
            }`}
          >
            <div className="flex items-center justify-between">
              <div>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                  Current Hydrological Status
                </span>
                <div className="mt-1 flex items-baseline gap-2">
                  <span className="font-mono text-3xl font-extrabold tracking-tight">
                    {prediction.risk_score?.toFixed(4)}
                  </span>
                  <span className="text-xs font-semibold text-slate-500">Risk Score</span>
                </div>
              </div>
              <div>
                {isAlert ? (
                  <div className="flex items-center gap-1.5 rounded-full bg-rose-600 px-3 py-1 text-xs font-bold text-white shadow-md shadow-rose-500/30">
                    <ShieldAlert className="h-4 w-4 animate-pulse" />
                    <span>ALERT STATE</span>
                  </div>
                ) : (
                  <div className="flex items-center gap-1.5 rounded-full bg-emerald-600 px-3 py-1 text-xs font-bold text-white shadow-md shadow-emerald-500/20">
                    <ShieldCheck className="h-4 w-4" />
                    <span>NORMAL STATE</span>
                  </div>
                )}
              </div>
            </div>

            {/* Trigger Hierarchy Breakdown */}
            <div className="mt-3.5 border-t border-slate-200/60 pt-2.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Hydrological Trigger Hierarchy
              </span>
              <div className="mt-1.5 flex flex-wrap items-center gap-2">
                <span
                  className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium ${
                    prediction.warning_flag
                      ? 'bg-amber-100 text-amber-800 border border-amber-300'
                      : 'bg-slate-100 text-slate-600'
                  }`}
                >
                  Warning Flag:{' '}
                  <strong>{prediction.warning_flag ? 'TRIGGERED' : 'INACTIVE'}</strong>
                </span>

                <span
                  className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium ${
                    prediction.danger_flag
                      ? 'bg-rose-100 text-rose-800 border border-rose-300'
                      : 'bg-slate-100 text-slate-600'
                  }`}
                >
                  Danger Flag:{' '}
                  <strong>{prediction.danger_flag ? 'TRIGGERED' : 'INACTIVE'}</strong>
                </span>
              </div>
              <p className="mt-1 text-[10px] text-slate-400">
                Danger strictly implies Warning. Single ALERT state is active if either threshold is reached.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Causal Weather Feeds (Compact) */}
      {prediction?.weather && (
        <div className="mt-3 border-t border-slate-100 pt-2.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
              Observed Weather (t-1)
            </span>
            <span className="text-[10px] text-slate-400 font-mono">ERA5 Reanalysis</span>
          </div>
          <div className="mt-1.5 grid grid-cols-3 gap-2 text-xs">
            <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-2 text-center">
              <span className="text-[9px] uppercase text-slate-400 block">Rain 1d (t-1)</span>
              <p className="mt-0.5 font-mono text-sm font-bold text-slate-900">
                {prediction.weather.rain_yesterday_mm.toFixed(1)} <span className="text-[9px] font-normal text-slate-500">mm</span>
              </p>
            </div>

            <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-2 text-center">
              <span className="text-[9px] uppercase text-slate-400 block">Rain 7-Day</span>
              <p className="mt-0.5 font-mono text-sm font-bold text-slate-900">
                {prediction.weather.rain_7d_sum_mm.toFixed(1)} <span className="text-[9px] font-normal text-slate-500">mm</span>
              </p>
            </div>

            <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-2 text-center">
              <span className="text-[9px] uppercase text-slate-400 block">Topsoil Sat.</span>
              <p className="mt-0.5 font-mono text-sm font-bold text-slate-900">
                {prediction.weather.soil_moisture_0_7cm.toFixed(3)}
              </p>
            </div>
          </div>
          {zone.zone_status === 'no_validated_model' && (
            <p className="mt-1.5 text-[10px] italic text-slate-400">
              No risk score or alert color computed for unvalidated basins.
            </p>
          )}
        </div>
      )}
    </div>
  );
};
