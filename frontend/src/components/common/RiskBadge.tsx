import React from 'react';
import { RiskTier, SeverityLevel } from '../../types';

interface RiskBadgeProps {
  level: RiskTier | SeverityLevel | string;
  size?: 'sm' | 'md' | 'lg';
  showDot?: boolean;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ level, size = 'md', showDot = true }) => {
  const normLevel = (level || 'LOW').toUpperCase();

  let colorClasses = 'bg-emerald-950/60 text-emerald-400 border-emerald-700/60';
  let dotColor = 'bg-emerald-400';

  if (normLevel === 'CRITICAL') {
    colorClasses = 'bg-red-950/80 text-red-400 border-red-700/80';
    dotColor = 'bg-red-400 animate-pulse';
  } else if (normLevel === 'ELEVATED' || normLevel === 'HIGH') {
    colorClasses = 'bg-amber-950/70 text-amber-400 border-amber-700/70';
    dotColor = 'bg-amber-400';
  } else if (normLevel === 'GUARDED' || normLevel === 'MEDIUM') {
    colorClasses = 'bg-sky-950/60 text-sky-400 border-sky-700/60';
    dotColor = 'bg-sky-400';
  } else if (normLevel === 'INFORMATIONAL' || normLevel === 'INFO') {
    colorClasses = 'bg-slate-900 text-slate-400 border-slate-700';
    dotColor = 'bg-slate-400';
  }

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-xs font-semibold px-2.5 py-1',
    lg: 'text-sm font-bold px-3.5 py-1.5',
  }[size];

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border shadow-sm ${colorClasses} ${sizeClasses}`}>
      {showDot && <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />}
      {normLevel}
    </span>
  );
};
