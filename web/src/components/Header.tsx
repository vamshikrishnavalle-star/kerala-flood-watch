import React from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  MapPin,
  RefreshCw,
  Search,
  Waves,
} from 'lucide-react';
import type { SystemStatus, ZoneItem, ZonePrediction } from '../types/api.ts';

interface HeaderProps {
  status: SystemStatus | null;
  zones: ZoneItem[];
  predictions: Record<string, ZonePrediction>;
  selectedZoneSlug: string;
  onSelectZone: (slug: string) => void;
  activeTab: 'operations' | 'whatif' | 'performance' | 'history';
  onSelectTab: (tab: 'operations' | 'whatif' | 'performance' | 'history') => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onRefresh?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  status,
  zones,
  predictions,
  selectedZoneSlug,
  onSelectZone,
  activeTab,
  onSelectTab,
  searchQuery,
  onSearchChange,
  onRefresh,
}) => {
  // Check for any active alerts across all zones
  const activeAlerts = Object.values(predictions).filter(
    (p) => p.alert_level === 'ALERT'
  );

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/90 backdrop-blur-md">
      {/* Top Navbar */}
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        {/* Brand / Logo */}
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-sky-600 to-sky-400 text-white shadow-md shadow-sky-500/20">
            <Waves className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold tracking-tight text-slate-900">
                Kerala <span className="text-sky-600">FEWS</span>
              </span>
              <span className="rounded bg-sky-100 px-1.5 py-0.5 text-[10px] font-semibold text-sky-800">
                v2.0
              </span>
            </div>
            <p className="hidden text-[11px] font-medium text-slate-500 sm:block">
              Operational Hydrological Decision Support System
            </p>
          </div>
        </div>

        {/* Global Navigation Tabs */}
        <nav className="hidden items-center gap-1 md:flex">
          <button
            onClick={() => onSelectTab('operations')}
            className={`rounded-lg px-3.5 py-2 text-xs font-semibold transition-all ${
              activeTab === 'operations'
                ? 'bg-sky-50 text-sky-700 shadow-sm ring-1 ring-sky-200'
                : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
            }`}
          >
            Operations Overview
          </button>
          <button
            onClick={() => onSelectTab('whatif')}
            className={`rounded-lg px-3.5 py-2 text-xs font-semibold transition-all ${
              activeTab === 'whatif'
                ? 'bg-sky-50 text-sky-700 shadow-sm ring-1 ring-sky-200'
                : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
            }`}
          >
            Sensitivity Analysis
          </button>
          <button
            onClick={() => onSelectTab('performance')}
            className={`rounded-lg px-3.5 py-2 text-xs font-semibold transition-all ${
              activeTab === 'performance'
                ? 'bg-sky-50 text-sky-700 shadow-sm ring-1 ring-sky-200'
                : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
            }`}
          >
            Performance & Limitations
          </button>
          <button
            onClick={() => onSelectTab('history')}
            className={`rounded-lg px-3.5 py-2 text-xs font-semibold transition-all ${
              activeTab === 'history'
                ? 'bg-sky-50 text-sky-700 shadow-sm ring-1 ring-sky-200'
                : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
            }`}
          >
            Prediction History
          </button>
        </nav>

        {/* Search & System Indicators */}
        <div className="flex items-center gap-3">
          <div className="relative hidden w-48 lg:block">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Search basins..."
              className="w-full rounded-full border border-slate-200 bg-slate-50/70 py-1.5 pl-8 pr-3 text-xs text-slate-700 placeholder-slate-400 transition-all focus:border-sky-500 focus:bg-white focus:outline-none focus:ring-1 focus:ring-sky-500"
            />
          </div>

          {/* Sync Pill */}
          <div className="flex items-center gap-2 rounded-full border border-slate-200/80 bg-slate-50/80 px-3 py-1.5 text-xs text-slate-600">
            <span
              className={`h-2 w-2 rounded-full ${
                status?.status === 'healthy' ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'
              }`}
            />
            <span className="hidden font-mono font-medium sm:inline">
              {status?.status === 'healthy' ? 'LIVE CWC & ERA5' : 'OFFLINE'}
            </span>
            {onRefresh && (
              <button
                onClick={onRefresh}
                title="Refresh live observations"
                className="ml-0.5 text-slate-400 hover:text-slate-700"
              >
                <RefreshCw className="h-3 w-3" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Sub-Header Live Notification / Ribbon Bar */}
      <div className="border-t border-slate-100 bg-gradient-to-r from-sky-50/60 via-slate-50 to-blue-50/40 px-4 py-2 sm:px-6">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 text-xs">
          {/* Live Alert Status Bar */}
          <div className="flex items-center gap-2">
            {activeAlerts.length > 0 ? (
              <div className="flex items-center gap-2 font-medium text-rose-700">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-rose-100">
                  <AlertTriangle className="h-3 w-3 text-rose-600" />
                </span>
                <span>
                  <strong>LIVE ALERT:</strong> {activeAlerts.length} basin(s) currently in ALERT state (
                  {activeAlerts.map((a) => a.zone_name).join(', ')})
                </span>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-slate-600">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
                  <CheckCircle2 className="h-3 w-3" />
                </span>
                <span>
                  <strong>OPERATIONAL STATUS:</strong> Antecedent rainfall and river stage within nominal bounds across all basins.
                </span>
              </div>
            )}
          </div>

          {/* Basin Quick Dropdown & Export Controls */}
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-slate-700 shadow-sm">
              <MapPin className="h-3.5 w-3.5 text-sky-600" />
              <select
                value={selectedZoneSlug}
                onChange={(e) => onSelectZone(e.target.value)}
                className="bg-transparent font-medium text-slate-800 focus:outline-none"
              >
                {zones.map((z) => (
                  <option key={z.slug} value={z.slug}>
                    {z.name} ({z.district})
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={() => window.print()}
              className="hidden items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 font-medium text-slate-700 shadow-sm hover:bg-slate-50 sm:flex"
            >
              <Download className="h-3.5 w-3.5 text-slate-500" />
              <span>Export</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
