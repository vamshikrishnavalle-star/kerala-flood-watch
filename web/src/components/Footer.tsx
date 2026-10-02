import React from 'react';

export const Footer: React.FC = () => {
  return (
    <footer className="mt-12 border-t border-slate-200/80 bg-white/60 py-6 text-center backdrop-blur-sm">
      <div className="mx-auto max-w-7xl px-4">
        <p className="text-xs font-medium text-slate-500 md:text-sm">
          <strong className="text-slate-700">Illustrative, not official guidance</strong> | State and
          district disaster management authorities issue official alerts.
        </p>
        <p className="mt-1 text-xs text-slate-400">
          Kerala River Basin Flood Early Warning System (Kerala FEWS) • CWC Telemetry & Open-Meteo ERA5 Reanalysis
        </p>
      </div>
    </footer>
  );
};
