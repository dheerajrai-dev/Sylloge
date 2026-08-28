import React from 'react';
import { LucideIcon, TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface ScoreCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: 'IMPROVING' | 'STABLE' | 'DETERIORATING' | 'up' | 'down' | 'neutral';
  color?: 'brand' | 'red' | 'amber' | 'emerald' | 'slate';
  badge?: string;
}

export const ScoreCard: React.FC<ScoreCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  color = 'brand',
  badge,
}) => {
  const iconColors = {
    brand: 'text-brand-500 bg-brand-950/40 border-brand-800/40',
    red: 'text-red-400 bg-red-950/40 border-red-800/40',
    amber: 'text-amber-400 bg-amber-950/40 border-amber-800/40',
    emerald: 'text-emerald-400 bg-emerald-950/40 border-emerald-800/40',
    slate: 'text-slate-400 bg-slate-900 border-slate-800',
  }[color];

  return (
    <div className="bg-surface-card border border-surface-border rounded-xl p-5 shadow-lg relative overflow-hidden flex flex-col justify-between hover:border-slate-600 transition-all duration-200">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs font-semibold text-surface-muted uppercase tracking-wider">{title}</div>
          <div className="text-2xl font-bold text-slate-50 mt-2 tracking-tight">{value}</div>
        </div>
        <div className={`p-2.5 rounded-lg border ${iconColors}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between text-xs">
        {subtitle && <span className="text-slate-400">{subtitle}</span>}
        {badge && (
          <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-800 text-slate-300 border border-slate-700">
            {badge}
          </span>
        )}
        {trend && (
          <div className="flex items-center gap-1 font-medium">
            {trend === 'DETERIORATING' || trend === 'up' ? (
              <span className="flex items-center text-red-400">
                <TrendingUp className="w-3.5 h-3.5 mr-0.5" /> High Risk Trend
              </span>
            ) : trend === 'IMPROVING' || trend === 'down' ? (
              <span className="flex items-center text-emerald-400">
                <TrendingDown className="w-3.5 h-3.5 mr-0.5" /> Improving
              </span>
            ) : (
              <span className="flex items-center text-slate-400">
                <Minus className="w-3.5 h-3.5 mr-0.5" /> Stable
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
