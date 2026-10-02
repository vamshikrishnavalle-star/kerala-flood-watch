import React from 'react';

interface StatusBadgeProps {
  status: 'validated' | 'provisional' | 'no_validated_model' | 'ALERT' | 'NORMAL';
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = 'md',
  showIcon = true,
}) => {
  let badgeClasses = '';
  let label = '';
  let icon = '';

  switch (status) {
    case 'validated':
      badgeClasses = 'bg-emerald-50 text-emerald-700 border-emerald-200';
      label = '[VALIDATED]';
      icon = '🛡️';
      break;
    case 'provisional':
      badgeClasses = 'bg-amber-50 text-amber-700 border-amber-200';
      label = '[PROVISIONAL]';
      icon = '⚠️';
      break;
    case 'no_validated_model':
      badgeClasses = 'bg-slate-100 text-slate-600 border-slate-200';
      label = '[WEATHER ONLY]';
      icon = '🌦️';
      break;
    case 'ALERT':
      badgeClasses = 'bg-rose-50 text-rose-700 border-rose-200 ring-2 ring-rose-400/20';
      label = '[ALERT]';
      icon = '🚨';
      break;
    case 'NORMAL':
      badgeClasses = 'bg-emerald-50 text-emerald-700 border-emerald-200';
      label = '[NORMAL]';
      icon = '🟢';
      break;
    default:
      badgeClasses = 'bg-slate-100 text-slate-600 border-slate-200';
      label = status;
  }

  const sizeClasses =
    size === 'sm'
      ? 'px-2 py-0.5 text-xs'
      : size === 'lg'
      ? 'px-3.5 py-1.5 text-sm font-semibold'
      : 'px-2.5 py-1 text-xs font-medium';

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border shadow-sm tracking-wide ${sizeClasses} ${badgeClasses}`}
    >
      {showIcon && <span>{icon}</span>}
      <span className="font-mono">{label}</span>
    </span>
  );
};
