import React, { useState, useEffect, useCallback } from 'react';
import type { SystemStatus, ZoneItem, ZonePrediction, HistoryRecord } from './types/api.ts';
import { api } from './services/api.ts';
import { Header } from './components/Header.tsx';
import { Footer } from './components/Footer.tsx';
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

      if (zonesRes.length > 0 && !selectedZoneSlug) {
        setSelectedZoneSlug(zonesRes[0].slug);
      }

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
        'Backend API unavailable at http://127.0.0.1:8000. Please ensure the FastAPI server is running.'
      );
    } finally {
      setInitialLoading(false);
    }
  }, [selectedZoneSlug]);

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
          <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50/90 p-4 text-xs font-semibold text-rose-800 shadow-sm">
            🚨 {apiError}
          </div>
        )}

        {initialLoading ? (
          <div className="flex h-96 flex-col items-center justify-center gap-3 text-slate-400">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-sky-600 border-t-transparent" />
            <p className="text-xs font-medium">Connecting to Kerala FEWS decision engine...</p>
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
  );
};

export default App;
