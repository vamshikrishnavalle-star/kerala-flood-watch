import React from 'react';
import { ArrowRight, Calendar, CloudDrizzle, CloudRain, Sparkles } from 'lucide-react';
import type { ZonePrediction } from '../types/api.ts';

interface TimeHorizonOutlookProps {
  prediction: ZonePrediction | null;
  onNavigateToWhatIf?: () => void;
}

export const TimeHorizonOutlook: React.FC<TimeHorizonOutlookProps> = ({
  prediction,
  onNavigateToWhatIf,
}) => {
  const outlook = prediction?.experimental_outlook_days_1_to_3 || [];
  const hasValidatedScore = prediction && prediction.risk_score !== null;

  return (
    <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-card transition-all hover:shadow-elevated">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4 text-sky-600" />
          <h3 className="text-sm font-semibold tracking-tight text-slate-900">
            Operational Time Horizon
          </h3>
        </div>
        <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">
          Causal Split
        </span>
      </div>

      {/* Day 0 Validated Assessment */}
      <div className="mt-3.5 rounded-xl border border-sky-100 bg-gradient-to-r from-sky-50/50 via-white to-blue-50/30 p-3.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-sky-600 text-xs font-bold text-white">
              0
            </span>
            <div>
              <span className="text-xs font-bold text-slate-900">
                Day 0 (Validated)
              </span>
              <p className="text-[11px] font-medium text-slate-600">
                risk today given rainfall through yesterday (t-1)
              </p>
            </div>
          </div>
          {hasValidatedScore && (
            <span className="font-mono text-sm font-bold text-slate-900">
              Score: {prediction.risk_score?.toFixed(4)}
            </span>
          )}
        </div>
        <p className="mt-1.5 text-[10px] text-slate-400">
          Evaluated using causal observations strictly prior to today (ERA5 reanalysis lag).
        </p>
      </div>

      {/* Days 1-3 Experimental Outlook */}
      <div className="mt-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5 text-amber-500" />
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
              Experimental Outlook (Days 1–3)
            </h4>
          </div>
          <span className="text-[10px] font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
            experimental, not validated
          </span>
        </div>
        <p className="mt-1 text-[11px] text-slate-500">
          Numerical weather prediction (NWP) lead-day projections. Experimental guidance only.
        </p>

        {outlook.length > 0 ? (
          <div className="mt-3 grid grid-cols-3 gap-2.5">
            {outlook.map((lead) => {
              const isLeadAlert = lead.projected_alert_level === 'ALERT';
              return (
                <div
                  key={lead.lead_day}
                  className={`rounded-xl border p-3 text-center transition-all ${
                    isLeadAlert
                      ? 'border-rose-200 bg-rose-50/50'
                      : 'border-slate-200/80 bg-slate-50/60 hover:bg-white'
                  }`}
                >
                  <span className="text-[11px] font-bold text-slate-500">
                    Day +{lead.lead_day}
                  </span>
                  <div className="my-1 flex justify-center text-sky-600">
                    {lead.forecast_rainfall_mm > 20 ? (
                      <CloudRain className="h-5 w-5" />
                    ) : (
                      <CloudDrizzle className="h-5 w-5" />
                    )}
                  </div>
                  <div className="text-[10px] text-slate-500">
                    Rain: <strong className="text-slate-700">{lead.forecast_rainfall_mm.toFixed(1)} mm</strong>
                  </div>
                  <div className="mt-1 font-mono text-xs font-bold text-slate-900">
                    {lead.projected_risk_score.toFixed(4)}
                  </div>
                  <span
                    className={`mt-1.5 inline-block rounded-full px-2 py-0.5 text-[9px] font-bold ${
                      isLeadAlert
                        ? 'bg-rose-100 text-rose-700'
                        : 'bg-emerald-100 text-emerald-700'
                    }`}
                  >
                    {lead.projected_alert_level}
                  </span>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="mt-3 rounded-xl border border-dashed border-slate-200 p-4 text-center text-xs text-slate-400">
            NWP experimental projections currently unavailable for this basin.
          </div>
        )}
      </div>

      {/* Action Footer */}
      {onNavigateToWhatIf && (
        <button
          onClick={onNavigateToWhatIf}
          className="mt-4 flex w-full items-center justify-center gap-1.5 rounded-xl border border-sky-200 bg-sky-50/80 py-2.5 text-xs font-semibold text-sky-700 shadow-sm transition-all hover:bg-sky-100 hover:shadow"
        >
          <span>Run Sensitivity Analysis (What-If Simulation)</span>
          <ArrowRight className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
};
