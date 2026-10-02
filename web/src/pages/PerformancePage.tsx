import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  Award,
  Calendar,
  FileText,
  Info,
  Table,
} from 'lucide-react';
import type { MetricsResponse } from '../types/api.ts';
import { api } from '../services/api.ts';

export const PerformancePage: React.FC = () => {
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [activeTab, setActiveTab] = useState<'audit' | 'coverage' | 'limitations'>('audit');

  useEffect(() => {
    let isMounted = true;
    async function load() {
      try {
        const data = await api.getMetrics();
        if (isMounted) setMetrics(data);
      } catch (err) {
        console.error('Failed to load metrics', err);
      }
    }
    load();
    return () => {
      isMounted = false;
    };
  }, []);

  const auditRows = metrics?.precision_recall_audit || [];
  const kottayamDanger = auditRows.find(
    (r) => r.zone.toLowerCase() === 'kottayam' && r.target.toLowerCase() === 'danger'
  );

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* Page Title & Methodological Notice */}
      <div className="rounded-2xl border border-slate-200/90 bg-white p-6 shadow-card">
        <div className="flex items-center gap-3 border-b border-slate-100 pb-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-100 text-sky-700">
            <Award className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold tracking-tight text-slate-900">
              Model Performance Audit & Empirical Limitations
            </h2>
            <p className="text-xs text-slate-500">
              Authoritative Step 0 / Stage 2 empirical evaluation using single-pass holdout test set (2019–2024).
            </p>
          </div>
        </div>

        {/* Methodological Callout */}
        <div className="mt-4 rounded-xl border border-blue-100 bg-blue-50/60 p-3.5 text-xs text-blue-950">
          <div className="flex items-start gap-2">
            <Info className="mt-0.5 h-4 w-4 shrink-0 text-blue-600" />
            <div>
              <strong className="block font-semibold">Methodological Note:</strong>
              <p className="mt-0.5 leading-relaxed text-blue-900">
                The 5-date test is a deterministic regression check against stored offline model output, not holdout validation. Date 2018-08-16 is strictly in-sample (training period 2000–2018).
              </p>
            </div>
          </div>
        </div>

        {/* Sub-Tabs */}
        <div className="mt-6 flex border-b border-slate-200">
          <button
            onClick={() => setActiveTab('audit')}
            className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-xs font-semibold transition-all ${
              activeTab === 'audit'
                ? 'border-sky-600 text-sky-700'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Table className="h-4 w-4" />
            <span>Precision-Recall Audit</span>
          </button>

          <button
            onClick={() => setActiveTab('coverage')}
            className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-xs font-semibold transition-all ${
              activeTab === 'coverage'
                ? 'border-sky-600 text-sky-700'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Calendar className="h-4 w-4" />
            <span>Annual Data Coverage</span>
          </button>

          <button
            onClick={() => setActiveTab('limitations')}
            className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-xs font-semibold transition-all ${
              activeTab === 'limitations'
                ? 'border-sky-600 text-sky-700'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <FileText className="h-4 w-4" />
            <span>Empirical Limitations</span>
          </button>
        </div>
      </div>

      {/* Tab 1: Precision-Recall Audit Table */}
      {activeTab === 'audit' && (
        <div className="space-y-5">
          {/* Kottayam Holdout Highlight Banner */}
          {kottayamDanger && (
            <div className="rounded-2xl border border-amber-200 bg-amber-50/80 p-5 shadow-sm">
              <div className="flex items-start gap-3">
                <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
                <div className="text-xs text-amber-900">
                  <h4 className="font-bold text-sm text-amber-950">
                    Kottayam Holdout Sample Reliability Notice
                  </h4>
                  <p className="mt-1 leading-relaxed">
                    With {kottayamDanger.caught_events} true danger events (
                    {(kottayamDanger.event_rec * 100).toFixed(1)}% caught of {kottayamDanger.total_events}), there are{' '}
                    {kottayamDanger.total_alert_episodes} total alert episodes ({kottayamDanger.caught_events} of{' '}
                    {kottayamDanger.total_alert_episodes} real, {(kottayamDanger.ep_prec * 100).toFixed(2)}% episode precision) and{' '}
                    {kottayamDanger.fp_days / 6} false-alarm days/year.
                  </p>
                  <p className="mt-1.5 font-medium text-[11px] text-amber-800">
                    Rule: Counts must be evaluated alongside percentages across all basin evaluations.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Table Container */}
          <div className="overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-card">
            <div className="border-b border-slate-100 bg-slate-50/80 px-5 py-3">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Authoritative Precision-Recall Benchmark (Holdout 2019–2024 & OOF 2000–2018)
              </span>
              <p className="text-[11px] text-slate-500">
                Precision, event counts, alert episodes, and false alarms displayed beside every recall figure.
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-slate-200 bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500 font-semibold">
                  <tr>
                    <th className="px-4 py-3">Split</th>
                    <th className="px-4 py-3">Basin</th>
                    <th className="px-4 py-3">Target</th>
                    <th className="px-4 py-3">Threshold</th>
                    <th className="px-4 py-3">Event Recall</th>
                    <th className="px-4 py-3">Day Recall</th>
                    <th className="px-4 py-3">Day Precision</th>
                    <th className="px-4 py-3">Episode Precision</th>
                    <th className="px-4 py-3">False-Alarm Days</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {auditRows.map((r, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/80 transition-colors">
                      <td className="px-4 py-3 font-sans font-medium text-slate-800">{r.dataset}</td>
                      <td className="px-4 py-3 font-sans font-semibold text-slate-900 capitalize">{r.zone}</td>
                      <td className="px-4 py-3 font-sans capitalize">
                        <span
                          className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                            r.target === 'warning'
                              ? 'bg-amber-100 text-amber-800'
                              : 'bg-rose-100 text-rose-800'
                          }`}
                        >
                          {r.target}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-600">{r.threshold.toFixed(4)}</td>
                      <td className="px-4 py-3 font-bold text-slate-900 font-sans">
                        {r.caught_events} / {r.total_events} ({(r.event_rec * 100).toFixed(1)}%)
                      </td>
                      <td className="px-4 py-3 text-slate-700">{(r.day_rec * 100).toFixed(1)}%</td>
                      <td className="px-4 py-3 font-semibold text-emerald-700">{(r.day_prec * 100).toFixed(2)}%</td>
                      <td className="px-4 py-3 text-slate-800 font-sans">
                        {(r.ep_prec * 100).toFixed(2)}% ({r.total_alert_episodes} eps)
                      </td>
                      <td className="px-4 py-3 text-slate-500 font-sans">{r.fp_days} days</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Annual Ground-Truth Availability */}
      {activeTab === 'coverage' && (
        <div className="overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-card">
          <div className="border-b border-slate-100 bg-slate-50/80 px-5 py-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
              Annual Ground-Truth Station Telemetry Availability (2000–2024)
            </span>
            <p className="text-[11px] text-slate-500">
              CWC gauge data availability by station and year. Highlights Kidangoor telemetry starting only in June 2015.
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-200 bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500 font-semibold">
                <tr>
                  <th className="px-4 py-2.5">Basin</th>
                  <th className="px-4 py-2.5">Year</th>
                  <th className="px-4 py-2.5">Total Days</th>
                  <th className="px-4 py-2.5">Warning Exceedances</th>
                  <th className="px-4 py-2.5">Danger Exceedances</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {(metrics?.dataset_per_zone_year || []).map((zy, idx) => (
                  <tr key={idx} className="hover:bg-slate-50">
                    <td className="px-4 py-2 font-sans font-medium text-slate-800">{zy.zone}</td>
                    <td className="px-4 py-2 text-slate-700">{zy.year}</td>
                    <td className="px-4 py-2 text-slate-600">{zy.total_days}</td>
                    <td className="px-4 py-2 text-amber-700 font-semibold">{zy.warning_exceedances}</td>
                    <td className="px-4 py-2 text-rose-700 font-semibold">{zy.danger_exceedances}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 3: Empirical System Limitations */}
      {activeTab === 'limitations' && (
        <div className="rounded-2xl border border-slate-200/90 bg-white p-6 shadow-card space-y-4 text-xs leading-relaxed text-slate-700">
          <div className="border-b border-slate-100 pb-3">
            <h3 className="text-sm font-bold text-slate-900">
              Empirical System Limitations (docs/step0/limitations.md)
            </h3>
            <p className="text-[11px] text-slate-500">
              Mandatory operational and data limitations governing deployment.
            </p>
          </div>

          <div className="space-y-3 font-sans">
            <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
              <strong className="block text-slate-900">1. Spatial Generalisation Boundary</strong>
              <p className="mt-1 text-slate-600">
                Models are validated exclusively on Kallooppara (Manimala Basin). Kottayam (Meenachil Basin) has provisional status due to short ground-truth records (2015–2024). The remaining 5 Kerala basins have no validated hydrological model; live inference suppresses risk scores and outputs read-only weather feeds.
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
              <strong className="block text-slate-900">2. Causal Observation Horizon & Lead Time</strong>
              <p className="mt-1 text-slate-600">
                Validated scores are computed strictly from rainfall through yesterday (t-1). Projections for Days 1–3 are experimental numerical weather prediction outlooks and are not validated against stage telemetry.
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
              <strong className="block text-slate-900">3. Telemetry Thinning & 2026 Alert Verification</strong>
              <p className="mt-1 text-slate-600">
                Telemetry thinning explains only part of the 1.79% vs 3.75% rate difference and the rest is unexplained. Most 2026 alert blocks are unverified because 2026 CWC data was unavailable.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
