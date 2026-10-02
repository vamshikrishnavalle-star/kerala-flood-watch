import React, { useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { Filter, History } from 'lucide-react';
import type { ZoneItem, HistoryRecord } from '../types/api.ts';
import { StatusBadge } from '../components/StatusBadge.tsx';

interface HistoryPageProps {
  zones: ZoneItem[];
  historyLogs: HistoryRecord[];
}

export const HistoryPage: React.FC<HistoryPageProps> = ({
  zones,
  historyLogs,
}) => {
  const [filterSlug, setFilterSlug] = useState<string>('all');

  const filteredLogs = historyLogs.filter((log) => {
    if (filterSlug === 'all') return true;
    return log.zone_slug === filterSlug;
  });

  const chartData = filteredLogs
    .filter((l) => l.risk_score !== null)
    .slice(-40)
    .map((l) => ({
      time: l.timestamp ? new Date(l.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : `ID ${l.id}`,
      score: l.risk_score,
      alert: l.alert_level || 'NORMAL',
    }));

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* Header */}
      <div className="rounded-2xl border border-slate-200/90 bg-white p-6 shadow-card">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-100 text-sky-700">
              <History className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold tracking-tight text-slate-900">
                Inference Logs & Prediction History
              </h2>
              <p className="text-xs text-slate-500">
                Persistent historical inference log recorded in SQLite (data/processed/predictions_log.db).
              </p>
            </div>
          </div>

          {/* Filter Bar */}
          <div className="flex items-center gap-2">
            <Filter className="h-3.5 w-3.5 text-slate-400" />
            <select
              value={filterSlug}
              onChange={(e) => setFilterSlug(e.target.value)}
              className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-800 shadow-sm focus:border-sky-500 focus:outline-none"
            >
              <option value="all">All River Basins</option>
              {zones.map((z) => (
                <option key={z.slug} value={z.slug}>
                  {z.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Time-Series Trajectory Chart */}
        {chartData.length > 0 && (
          <div className="mt-5">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Historical Risk Score Trajectory
            </span>
            <div className="mt-2 h-48 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 8, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis
                    dataKey="time"
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
                  <Line
                    type="monotone"
                    dataKey="score"
                    stroke="#0284c7"
                    strokeWidth={2.5}
                    dot={{ r: 3, fill: '#0284c7' }}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>

      {/* Historical Records Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-card">
        <div className="border-b border-slate-100 bg-slate-50/80 px-5 py-3">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
            Raw Inference Stream ({filteredLogs.length} Records)
          </span>
        </div>

        {filteredLogs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="border-b border-slate-200 bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500 font-semibold font-sans">
                <tr>
                  <th className="px-4 py-2.5">ID</th>
                  <th className="px-4 py-2.5">Timestamp (UTC)</th>
                  <th className="px-4 py-2.5">Basin Slug</th>
                  <th className="px-4 py-2.5">Risk Score</th>
                  <th className="px-4 py-2.5">Alert Level</th>
                  <th className="px-4 py-2.5">Warning Flag</th>
                  <th className="px-4 py-2.5">Danger Flag</th>
                  <th className="px-4 py-2.5">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-2.5 text-slate-500">{log.id}</td>
                    <td className="px-4 py-2.5 text-slate-600 font-sans">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="px-4 py-2.5 text-slate-800 font-sans font-medium">
                      {log.zone_slug}
                    </td>
                    <td className="px-4 py-2.5 font-bold text-slate-900">
                      {log.risk_score !== null ? log.risk_score.toFixed(4) : 'null'}
                    </td>
                    <td className="px-4 py-2.5 font-sans">
                      {log.alert_level ? (
                        <StatusBadge status={log.alert_level as any} size="sm" />
                      ) : (
                        <span className="text-slate-400">N/A</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5">
                      {log.warning_flag === 1 ? (
                        <span className="text-amber-600 font-bold">1</span>
                      ) : (
                        <span className="text-slate-400">0</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5">
                      {log.danger_flag === 1 ? (
                        <span className="text-rose-600 font-bold">1</span>
                      ) : (
                        <span className="text-slate-400">0</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 font-sans text-slate-600">
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px]">
                        {log.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-8 text-center text-xs text-slate-400">
            No historical logs recorded for the selected basin filter.
          </div>
        )}
      </div>
    </div>
  );
};
