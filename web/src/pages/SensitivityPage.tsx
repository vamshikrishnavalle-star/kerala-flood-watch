import React, { useState, useEffect } from 'react';
import {
  CloudRain,
  Info,
  RotateCcw,
  Sliders,
} from 'lucide-react';
import type { ZoneItem, WhatIfResponse } from '../types/api.ts';
import { api } from '../services/api.ts';
import { StatusBadge } from '../components/StatusBadge.tsx';

interface SensitivityPageProps {
  zones: ZoneItem[];
  selectedZoneSlug: string;
  onSelectZone: (slug: string) => void;
}

export const SensitivityPage: React.FC<SensitivityPageProps> = ({
  zones,
  selectedZoneSlug,
  onSelectZone,
}) => {
  // Only validated or provisional basins have models for what-if
  const validZones = zones.filter((z) => z.zone_status !== 'no_validated_model');
  const activeSlug = validZones.some((z) => z.slug === selectedZoneSlug)
    ? selectedZoneSlug
    : validZones[0]?.slug || selectedZoneSlug;

  const currentZone = zones.find((z) => z.slug === activeSlug);

  const [extraRain, setExtraRain] = useState<number>(0);
  const [result, setResult] = useState<WhatIfResponse | null>(null);
  const [sliderMax, setSliderMax] = useState<number>(100);

  // Load initial simulation at extraRain = 0 to get the runtime upper bound
  useEffect(() => {
    let isMounted = true;
    async function initBound() {
      if (!activeSlug) return;
      try {
        const initRes = await api.getWhatIf(activeSlug, 0);
        if (isMounted) {
          setResult(initRes);
          setSliderMax(initRes.slider_max_bound_mm);
          setExtraRain(0);
        }
      } catch (err) {
        console.error('Failed to load initial what-if bound', err);
      }
    }
    initBound();
    return () => {
      isMounted = false;
    };
  }, [activeSlug]);

  // Recalculate whenever extraRain changes
  useEffect(() => {
    let isMounted = true;
    async function runSim() {
      if (!activeSlug) return;
      try {
        const res = await api.getWhatIf(activeSlug, extraRain);
        if (isMounted) {
          setResult(res);
        }
      } catch (err) {
        console.error('Failed to run what-if simulation', err);
      }
    }
    const timer = setTimeout(runSim, 80);
    return () => {
      isMounted = false;
      clearTimeout(timer);
    };
  }, [activeSlug, extraRain]);

  const deltaScore = result ? result.simulated_risk_score - result.base_risk_score : 0;
  const isSimAlert = result?.simulated_alert_level === 'ALERT';

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      {/* Title & Guidance Header */}
      <div className="rounded-2xl border border-slate-200/90 bg-white p-6 shadow-card">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-sky-100 text-sky-700">
                <Sliders className="h-5 w-5" />
              </div>
              <h2 className="text-lg font-bold tracking-tight text-slate-900">
                Sensitivity Analysis (What-If Simulation)
              </h2>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              Simulate hypothetical rainfall scenarios to evaluate catchment sensitivity and threshold triggers.
            </p>
          </div>

          {/* Basin Selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-slate-500">Target Basin:</span>
            <select
              value={activeSlug}
              onChange={(e) => onSelectZone(e.target.value)}
              className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-800 shadow-sm focus:border-sky-500 focus:outline-none"
            >
              {validZones.map((z) => (
                <option key={z.slug} value={z.slug}>
                  {z.name} ({z.river_basin} Basin)
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Sensitivity Methodological Rule Callout */}
        <div className="mt-4 rounded-xl border border-sky-100 bg-sky-50/60 p-3.5 text-xs text-slate-700">
          <p className="leading-relaxed">
            <strong>Methodology</strong>: <em>Sensitivity analysis: extra rainfall is added to yesterday's observation (rain_1d, rain_3d, rain_7d, rain_14d, and rain_30d all rise by that amount); soil moisture is unchanged.</em>
          </p>
          <p className="mt-1 text-[11px] text-slate-500">
            Runtime Upper Bound for {currentZone?.name}: <strong className="font-mono text-slate-800">{sliderMax.toFixed(1)} mm</strong> (minimum of observed basin daily max and training clip range).
          </p>
        </div>

        {/* Dynamic Clamped Slider */}
        <div className="mt-6 rounded-xl border border-slate-100 bg-slate-50/70 p-5">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-1.5 font-semibold text-slate-700">
              <CloudRain className="h-4 w-4 text-sky-600" />
              <span>Hypothetical Additional Rainfall Yesterday</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-lg font-bold text-sky-700">
                +{extraRain.toFixed(1)} mm
              </span>
              <button
                onClick={() => setExtraRain(0)}
                title="Reset to 0 mm"
                className="flex h-7 w-7 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-400 hover:text-slate-700"
              >
                <RotateCcw className="h-3 w-3" />
              </button>
            </div>
          </div>

          <input
            type="range"
            min={0}
            max={sliderMax}
            step={0.5}
            value={extraRain}
            onChange={(e) => setExtraRain(parseFloat(e.target.value))}
            className="mt-4 h-2 w-full cursor-pointer appearance-none rounded-lg bg-slate-200 accent-sky-600 focus:outline-none"
          />

          <div className="mt-2 flex justify-between font-mono text-[10px] text-slate-400">
            <span>0.0 mm (Current Observed)</span>
            <span>Clamped Bound: {sliderMax.toFixed(1)} mm</span>
          </div>
        </div>
      </div>

      {/* Simulation Result Comparison Cards */}
      {result && (
        <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
          {/* Base Score */}
          <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-card">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
              Base Risk Score (Observed)
            </span>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="font-mono text-3xl font-extrabold text-slate-800">
                {result.base_risk_score.toFixed(4)}
              </span>
            </div>
            <p className="mt-1 text-[11px] text-slate-500">
              Evaluated strictly on recorded weather prior to today.
            </p>
          </div>

          {/* Simulated Score */}
          <div
            className={`rounded-2xl border p-5 shadow-card ${
              isSimAlert
                ? 'border-rose-300 bg-gradient-to-br from-rose-50/60 to-white'
                : 'border-sky-200 bg-gradient-to-br from-sky-50/50 to-white'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                Simulated Risk Score
              </span>
              <span
                className={`font-mono text-xs font-bold ${
                  deltaScore > 0 ? 'text-rose-600' : 'text-slate-400'
                }`}
              >
                {deltaScore >= 0 ? `+${deltaScore.toFixed(4)}` : deltaScore.toFixed(4)}
              </span>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span
                className={`font-mono text-3xl font-extrabold ${
                  isSimAlert ? 'text-rose-700' : 'text-sky-900'
                }`}
              >
                {result.simulated_risk_score.toFixed(4)}
              </span>
            </div>
            <div className="mt-1.5 flex items-center gap-1.5">
              <span className="text-xs text-slate-500">Simulated State:</span>
              <StatusBadge status={result.simulated_alert_level} size="sm" />
            </div>
          </div>

          {/* Simulated Threshold Triggers */}
          <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-card">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
              Simulated Internal Thresholds
            </span>
            <div className="mt-3 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-600">Warning Flag:</span>
                <span
                  className={`rounded px-2 py-0.5 font-mono text-[11px] font-bold ${
                    result.simulated_warning_flag
                      ? 'bg-amber-100 text-amber-800'
                      : 'bg-slate-100 text-slate-500'
                  }`}
                >
                  {result.simulated_warning_flag ? 'TRIGGERED' : 'INACTIVE'}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-600">Danger Flag:</span>
                <span
                  className={`rounded px-2 py-0.5 font-mono text-[11px] font-bold ${
                    result.simulated_danger_flag
                      ? 'bg-rose-100 text-rose-800'
                      : 'bg-slate-100 text-slate-500'
                  }`}
                >
                  {result.simulated_danger_flag ? 'TRIGGERED' : 'INACTIVE'}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Saturation Note Callout */}
      {result?.saturation_note && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50/80 p-4 shadow-sm">
          <div className="flex items-start gap-2 text-xs text-amber-900">
            <Info className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
            <div>
              <strong className="block font-semibold">Model Saturation Behavior:</strong>
              <p className="mt-0.5 leading-relaxed text-amber-800">
                {result.saturation_note} Feature values above empirical training bounds are clamped to prevent unbounded logistic extrapolation.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
