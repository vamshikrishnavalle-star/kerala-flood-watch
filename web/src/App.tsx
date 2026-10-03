import React, { useState, useEffect, useCallback } from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import type { SystemStatus, ZoneItem, ZonePrediction, HistoryRecord } from './types/api.ts';
import { api } from './services/api.ts';
import { Header } from './components/Header.tsx';
import { Footer } from './components/Footer.tsx';
import { ErrorBoundary } from './components/ErrorBoundary.tsx';
import { OperationsPage } from './pages/OperationsPage.tsx';
import { SensitivityPage } from './pages/SensitivityPage.tsx';
import { PerformancePage } from './pages/PerformancePage.tsx';
import { HistoryPage } from './pages/HistoryPage.tsx';

export const App: React.FC = () => {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [zones, setZones] = useState<ZoneItem[]>([]);
  const [predictions, setPredictions] = useState<Record<string, ZonePrediction>>({});
  const [historyLogs, setHistoryLogs] = useState<HistoryRecord[]>([]);
  const [selectedZoneSlug, setSelectedZoneSlug] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'operations' | 'whatif' | 'performance' | 'history'>('operations');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [initialLoading, setInitialLoading] = useState<boolean>(true);
  const [apiError, setApiError] = useState<string | null>(null);

  const fetchAllData = useCallback(async () => {
    try {
      setApiError(null);
      const [statusRes, zonesRes, historyRes] = await Promise.all([
        api.getStatus(),
        api.getZones(),
        api.getHistory(undefined, 100),
      ]);

      setStatus(statusRes);
      setZones(zonesRes);
      setHistoryLogs(historyRes);

      setSelectedZoneSlug((prev) => prev || (zonesRes.length > 0 ? zonesRes[0].slug : ''));

      // Fetch predictions for all zones concurrently
      const predsMap: Record<string, ZonePrediction> = {};
      await Promise.all(
        zonesRes.map(async (zone) => {
          try {
            const pred = await api.getPrediction(zone.slug);
            predsMap[zone.slug] = pred;
          } catch (pErr) {
            console.warn(`Failed prediction for ${zone.slug}:`, pErr);
          }
        })
      );
      setPredictions(predsMap);
    } catch (err: any) {
      console.error('API Error:', err);
      setApiError(
        'Backend service connecting... If on Render free tier, server may take up to 45 seconds to wake up from inactivity.'
      );
    } finally {
      setInitialLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAllData();
    const interval = setInterval(fetchAllData, 30000); // 30s background poll
    return () => clearInterval(interval);
  }, [fetchAllData]);

  // Filtered zones by search query
  const filteredZones = zones.filter((z) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      z.name.toLowerCase().includes(q) ||
      z.district.toLowerCase().includes(q) ||
      z.river_basin.toLowerCase().includes(q)
    );
  });

  return (
    <ErrorBoundary>
      <div className="flex min-h-screen flex-col bg-slate-50 text-slate-800">
        {/* Top Header & Navigation */}
        <Header
          status={status}
          zones={filteredZones}
          predictions={predictions}
          selectedZoneSlug={selectedZoneSlug}
          onSelectZone={(slug) => setSelectedZoneSlug(slug)}
          activeTab={activeTab}
          onSelectTab={(tab) => setActiveTab(tab)}
          searchQuery={searchQuery}
          onSearchChange={(q) => setSearchQuery(q)}
          onRefresh={fetchAllData}
        />

        {/* Main Content Area */}
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-3 sm:px-6 sm:py-4">
          {apiError && (
            <div className="mb-4 flex items-center justify-between rounded-xl border border-amber-200 bg-amber-50/90 p-3 text-xs text-amber-900 shadow-sm">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0 text-amber-600" />
                <span>{apiError}</span>
              </div>
              <button
                onClick={fetchAllData}
                className="ml-3 rounded-lg bg-white px-2.5 py-1 text-xs font-semibold text-amber-900 shadow-sm border border-amber-200 hover:bg-amber-100"
              >
                Reconnect
              </button>
            </div>
          )}

          {zones.length === 0 ? (
            <div className="flex h-96 flex-col items-center justify-center text-center">
              <div className="max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-card">
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-sky-50 text-sky-600">
                  <RefreshCw className={`h-6 w-6 ${initialLoading ? 'animate-spin' : ''}`} />
                </div>
                <h3 className="mt-4 text-sm font-bold text-slate-900">
                  {initialLoading ? 'Connecting to Decision Engine...' : 'Waiting for Telemetry Service'}
                </h3>
                <p className="mt-2 text-xs leading-relaxed text-slate-500">
                  {initialLoading
                    ? 'Fetching live river basin configurations and ERA5 meteorological observations.'
                    : 'The cloud service may take 30 to 45 seconds to wake up from free-tier inactivity.'}
                </p>
                <button
                  onClick={fetchAllData}
                  className="mt-5 flex w-full items-center justify-center gap-1.5 rounded-xl bg-sky-600 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-sky-700"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  <span>Retry Connection</span>
                </button>
              </div>
            </div>
          ) : (
            <>
              {activeTab === 'operations' && (
                <OperationsPage
                  zones={filteredZones}
                  predictions={predictions}
                  selectedZoneSlug={selectedZoneSlug}
                  onSelectZone={(slug) => setSelectedZoneSlug(slug)}
                  onNavigateToWhatIf={() => setActiveTab('whatif')}
                  historyLogs={historyLogs}
                />
              )}

              {activeTab === 'whatif' && (
                <SensitivityPage
                  zones={zones}
                  selectedZoneSlug={selectedZoneSlug}
                  onSelectZone={(slug) => setSelectedZoneSlug(slug)}
                />
              )}

              {activeTab === 'performance' && <PerformancePage />}

              {activeTab === 'history' && (
                <HistoryPage
                  zones={zones}
                  historyLogs={historyLogs}
                />
              )}
            </>
          )}
        </main>

        {/* Persistent Public Disclaimer Footer */}
        <Footer />
      </div>
    </ErrorBoundary>
  );
};

export default App;
