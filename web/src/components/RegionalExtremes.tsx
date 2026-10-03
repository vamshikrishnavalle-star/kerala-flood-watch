import React from 'react';
import { AlertCircle, ArrowUpRight, Gauge, ShieldCheck } from 'lucide-react';
import type { ZoneItem, ZonePrediction } from '../types/api.ts';

interface RegionalExtremesProps {
  zone: ZoneItem;
  prediction: ZonePrediction | null;
  onLaunchSensitivity?: () => void;
}

export const RegionalExtremes: React.FC<RegionalExtremesProps> = ({
  zone,
  prediction,
  onLaunchSensitivity,
}) => {
  if (!zone) return null;
  const isAlert = prediction?.alert_level === 'ALERT';

  return (
    <div className="rounded-2xl border border-slate-200/90 bg-white p-4 shadow-card transition-all hover:shadow-elevated">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
        <div className="flex items-center gap-2">
          <Gauge className="h-4 w-4 text-sky-600" />
          <h3 className="text-sm font-semibold tracking-tight text-slate-900">
            Regional Hydrology & Extremes
          </h3>
        </div>
        <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">
          {zone.district}
        </span>
      </div>

      {/* Advisory Banner */}
      <div
        className={`mt-3 rounded-xl border p-2.5 text-xs ${
          isAlert
            ? 'border-amber-200 bg-amber-50/80 text-amber-900'
            : 'border-emerald-100 bg-emerald-50/50 text-emerald-900'
        }`}
      >
        <div className="flex items-start gap-2">
          {isAlert ? (
            <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600" />
          ) : (
            <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" />
          )}
          <p className="text-[11px] leading-relaxed">
            {isAlert
              ? 'Hydrological warning threshold reached. Elevated streamflow detected in basin catchment. Monitor stage telemetry.'
              : 'Hydrological conditions nominal. Catchment storage and soil moisture within non-exceedance historical baseline.'}
          </p>
        </div>
      </div>

      {/* Stats Summary */}
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-xl border border-slate-100 bg-slate-50/60 p-2.5">
          <span className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
            Hydrological Type
          </span>
          <p className="mt-0.5 font-semibold text-slate-800 capitalize text-xs">
            {zone.hydrological_type.replace(/_/g, ' ')}
          </p>
        </div>

        <div className="rounded-xl border border-slate-100 bg-slate-50/60 p-2.5">
          <span className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
            Coordinates
          </span>
          <p className="mt-0.5 font-mono font-semibold text-slate-800 text-xs">
            {zone.latitude.toFixed(3)}°N, {zone.longitude.toFixed(3)}°E
          </p>
        </div>
      </div>

      {/* Action Button */}
      {onLaunchSensitivity && (
        <button
          onClick={onLaunchSensitivity}
          className="mt-3 flex w-full items-center justify-between rounded-xl border border-slate-200 bg-slate-50/80 px-3 py-2 text-xs font-semibold text-slate-700 transition-all hover:bg-slate-100 hover:text-slate-900"
        >
          <span>Simulate Extreme Rainfall Event</span>
          <ArrowUpRight className="h-3.5 w-3.5 text-slate-500" />
        </button>
      )}
    </div>
  );
};
