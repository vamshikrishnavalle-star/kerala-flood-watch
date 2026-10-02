import React from 'react';
import { MapContainer, TileLayer, CircleMarker, Tooltip, Popup, useMap } from 'react-leaflet';
import { AlertCircle, Layers } from 'lucide-react';
import type { ZoneItem, ZonePrediction } from '../types/api.ts';
import { StatusBadge } from './StatusBadge.tsx';

interface BasinMapProps {
  zones: ZoneItem[];
  predictions: Record<string, ZonePrediction>;
  selectedZoneSlug: string;
  onSelectZone: (slug: string) => void;
}

// Helper component to center map when selected basin changes
const MapRecenter: React.FC<{ lat: number; lng: number }> = ({ lat, lng }) => {
  const map = useMap();
  React.useEffect(() => {
    map.setView([lat, lng], 8, { animate: true });
  }, [lat, lng, map]);
  return null;
};

export const BasinMap: React.FC<BasinMapProps> = ({
  zones,
  predictions,
  selectedZoneSlug,
  onSelectZone,
}) => {
  const [basemap, setBasemap] = React.useState<'canvas' | 'osm'>('canvas');
  const [showLayerMenu, setShowLayerMenu] = React.useState(false);

  const selectedZone = zones.find((z) => z.slug === selectedZoneSlug) || zones[0];
  const activeAlertsCount = Object.values(predictions).filter(
    (p) => p.alert_level === 'ALERT'
  ).length;

  const cartoKey = (import.meta as unknown as { env: Record<string, string> }).env?.VITE_CARTO_API_KEY;

  let tileUrl = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}';
  let attribution = 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ';

  if (cartoKey) {
    tileUrl = `https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png?api_key=${cartoKey}`;
    attribution = '&copy; <a href="https://carto.com/">CARTO</a>';
  } else if (basemap === 'osm') {
    tileUrl = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
    attribution = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
  }

  return (
    <div className="relative h-[400px] xl:h-[420px] w-full overflow-hidden rounded-2xl border border-slate-200/90 bg-slate-100 shadow-card">
      {/* Floating Map Controls & Alert Pill */}
      <div className="absolute left-3 top-3 z-[1000] flex items-center gap-2">
        <div className="flex items-center gap-1.5 rounded-full border border-amber-200/80 bg-white/95 px-3 py-1 text-xs font-semibold text-amber-800 shadow-md backdrop-blur-md">
          <AlertCircle className="h-3.5 w-3.5 text-amber-600" />
          <span>
            {activeAlertsCount > 0
              ? `${activeAlertsCount} Active Basin Alerts`
              : '0 Active Basin Alerts'}
          </span>
        </div>
      </div>

      <div className="absolute right-3 top-3 z-[1000] flex flex-col items-end gap-1">
        <button
          onClick={() => setShowLayerMenu(!showLayerMenu)}
          title="Switch Basemap"
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200/80 bg-white/95 text-slate-700 shadow-md backdrop-blur-md transition-all hover:bg-slate-50"
        >
          <Layers className="h-4 w-4" />
        </button>

        {showLayerMenu && (
          <div className="mt-1 rounded-xl border border-slate-200 bg-white/95 p-1.5 text-xs shadow-lg backdrop-blur-md">
            <button
              onClick={() => {
                setBasemap('canvas');
                setShowLayerMenu(false);
              }}
              className={`block w-full rounded-md px-2.5 py-1 text-left ${
                basemap === 'canvas' ? 'bg-sky-50 font-bold text-sky-700' : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              Light Canvas (Clean)
            </button>
            <button
              onClick={() => {
                setBasemap('osm');
                setShowLayerMenu(false);
              }}
              className={`block w-full rounded-md px-2.5 py-1 text-left ${
                basemap === 'osm' ? 'bg-sky-50 font-bold text-sky-700' : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              OpenStreetMap (Detailed)
            </button>
          </div>
        )}
      </div>

      <MapContainer
        center={[10.15, 76.6]}
        zoom={7.2}
        scrollWheelZoom={true}
        className="h-full w-full"
      >
        <TileLayer
          key={tileUrl}
          attribution={attribution}
          url={tileUrl}
        />

        {selectedZone && (
          <MapRecenter lat={selectedZone.latitude} lng={selectedZone.longitude} />
        )}

        {zones.map((zone) => {
          const pred = predictions[zone.slug];
          const isSelected = zone.slug === selectedZoneSlug;
          const isAlert = pred?.alert_level === 'ALERT';

          // Visual styles by status
          let fillColor = '#64748b'; // Weather only
          let strokeColor = '#475569';
          let radius = 10;

          if (zone.zone_status === 'validated') {
            fillColor = isAlert ? '#e11d48' : '#059669';
            strokeColor = isAlert ? '#9f1239' : '#047857';
            radius = isSelected ? 14 : 12;
          } else if (zone.zone_status === 'provisional') {
            fillColor = isAlert ? '#e11d48' : '#d97706';
            strokeColor = isAlert ? '#9f1239' : '#b45309';
            radius = isSelected ? 14 : 12;
          } else {
            radius = isSelected ? 11 : 9;
          }

          // Dual-cue non-color tag
          const statusTag =
            zone.zone_status === 'validated'
              ? '[VALIDATED]'
              : zone.zone_status === 'provisional'
              ? '[PROVISIONAL]'
              : '[WEATHER ONLY]';

          const alertTag =
            pred && pred.risk_score !== null
              ? `[${pred.alert_level || 'NORMAL'}]`
              : '';

          return (
            <React.Fragment key={zone.slug}>
              {/* Pulsing ring for alerts or selection */}
              {(isAlert || isSelected) && (
                <CircleMarker
                  center={[zone.latitude, zone.longitude]}
                  radius={radius + 8}
                  pathOptions={{
                    color: isAlert ? '#f43f5e' : '#38bdf8',
                    fillColor: isAlert ? '#fda4af' : '#bae6fd',
                    fillOpacity: 0.25,
                    weight: 1.5,
                  }}
                />
              )}

              <CircleMarker
                center={[zone.latitude, zone.longitude]}
                radius={radius}
                eventHandlers={{
                  click: () => onSelectZone(zone.slug),
                }}
                pathOptions={{
                  color: strokeColor,
                  fillColor: fillColor,
                  fillOpacity: 0.9,
                  weight: isSelected ? 3 : 1.5,
                }}
              >
                {/* Permanent clean text tooltip satisfying dual-cue requirement */}
                <Tooltip
                  permanent={true}
                  direction="right"
                  offset={[14, 0]}
                  className="rounded-md border border-slate-200/90 bg-white/95 px-2 py-0.5 text-[11px] font-medium text-slate-800 shadow-sm"
                >
                  <span className="font-semibold">{zone.name.split(' ')[0]}</span>{' '}
                  <span className="text-[10px] text-slate-500 font-mono">{statusTag}</span>{' '}
                  {alertTag && (
                    <span
                      className={`text-[10px] font-bold ${
                        isAlert ? 'text-rose-600' : 'text-emerald-600'
                      }`}
                    >
                      {alertTag}
                    </span>
                  )}
                </Tooltip>

                <Popup>
                  <div className="p-1 text-xs">
                    <div className="flex items-center justify-between gap-2 border-b pb-1.5">
                      <strong className="text-slate-900">{zone.name}</strong>
                      <StatusBadge status={zone.zone_status} size="sm" />
                    </div>
                    <div className="mt-2 space-y-1 text-slate-600">
                      <div>
                        District: <strong className="text-slate-800">{zone.district}</strong>
                      </div>
                      <div>
                        Basin: <strong className="text-slate-800">{zone.river_basin}</strong>
                      </div>
                      {pred && pred.risk_score !== null ? (
                        <div className="pt-1">
                          Risk Score: <strong className="text-slate-900 font-mono">{pred.risk_score.toFixed(4)}</strong>
                          <div className="mt-1">
                            Status: <StatusBadge status={pred.alert_level || 'NORMAL'} size="sm" />
                          </div>
                        </div>
                      ) : (
                        <div className="italic text-slate-500 pt-1">
                          Weather monitoring only. No risk score computed.
                        </div>
                      )}
                    </div>
                    <button
                      onClick={() => onSelectZone(zone.slug)}
                      className="mt-2.5 w-full rounded bg-sky-600 py-1 text-center font-medium text-white hover:bg-sky-700"
                    >
                      Select Basin
                    </button>
                  </div>
                </Popup>
              </CircleMarker>
            </React.Fragment>
          );
        })}
      </MapContainer>

      {/* Map Legend Footer Bar */}
      <div className="absolute bottom-2 left-3 right-3 z-[1000] flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200/90 bg-white/95 px-3 py-1.5 text-[11px] text-slate-600 shadow-md backdrop-blur-md">
        <div className="flex flex-wrap items-center gap-3">
          <span className="font-semibold text-slate-800">Legend:</span>
          <span className="inline-flex items-center gap-1">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-600" />
            <span>Validated Model</span>
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="h-2.5 w-2.5 rounded-full bg-amber-500" />
            <span>Provisional Model</span>
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="h-2.5 w-2.5 rounded-full bg-slate-500" />
            <span>Weather Only</span>
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="h-2.5 w-2.5 rounded-full bg-rose-600 ring-2 ring-rose-300" />
            <span>Active ALERT</span>
          </span>
        </div>
        <div className="text-[10px] text-slate-400">
          Non-color text labels float beside all stations
        </div>
      </div>
    </div>
  );
};
