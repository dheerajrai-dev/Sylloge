import React from 'react';
import { RiskBadge } from '../common/RiskBadge';

interface CompositeScoreGaugeProps {
  score: number;
  gapSubscore: number;
  negativeSubscore: number;
  peerSubscore: number;
  riskTier: string;
}

export const CompositeScoreGauge: React.FC<CompositeScoreGaugeProps> = ({
  score,
  gapSubscore,
  negativeSubscore,
  peerSubscore,
  riskTier,
}) => {
  const roundedScore = Math.round(score * 10) / 10;

  // Compute gauge color
  let scoreColor = 'text-emerald-400';
  let progressColor = 'bg-emerald-500';

  if (roundedScore >= 75) {
    scoreColor = 'text-red-400';
    progressColor = 'bg-red-500';
  } else if (roundedScore >= 50) {
    scoreColor = 'text-amber-400';
    progressColor = 'bg-amber-500';
  } else if (roundedScore >= 25) {
    scoreColor = 'text-sky-400';
    progressColor = 'bg-sky-500';
  }

  return (
    <div className="bg-surface-card border border-surface-border rounded-xl p-6 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-200">Composite Risk Score</h3>
          <p className="text-xs text-surface-muted">Tripartite Weighted Analytics Formula (45 / 35 / 20)</p>
        </div>
        <RiskBadge level={riskTier} size="lg" />
      </div>

      {/* Main Score Dial & Bar */}
      <div className="flex items-baseline gap-2 mb-3">
        <span className={`text-4xl font-extrabold tracking-tight ${scoreColor}`}>{roundedScore}</span>
        <span className="text-sm font-medium text-slate-400">/ 100.0</span>
      </div>

      <div className="w-full bg-slate-950 h-3 rounded-full overflow-hidden border border-slate-800 mb-6">
        <div
          className={`h-full rounded-full transition-all duration-500 ${progressColor}`}
          style={{ width: `${Math.min(100, Math.max(0, roundedScore))}%` }}
        />
      </div>

      {/* 45/35/20 Subscore Component Bars */}
      <div className="space-y-3.5 pt-2 border-t border-surface-border">
        {/* Execution Gap - 45% */}
        <div>
          <div className="flex justify-between text-xs font-medium mb-1">
            <span className="text-slate-300">
              Execution Gap <span className="text-slate-400 font-mono">(45% weight)</span>
            </span>
            <span className="text-slate-200 font-mono font-semibold">{Math.round(gapSubscore * 10) / 10}</span>
          </div>
          <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden border border-slate-800">
            <div
              className="bg-red-500 h-full rounded-full transition-all duration-300"
              style={{ width: `${Math.min(100, Math.max(0, gapSubscore))}%` }}
            />
          </div>
        </div>

        {/* Negative Space - 35% */}
        <div>
          <div className="flex justify-between text-xs font-medium mb-1">
            <span className="text-slate-300">
              Negative Space & Silence <span className="text-slate-400 font-mono">(35% weight)</span>
            </span>
            <span className="text-slate-200 font-mono font-semibold">{Math.round(negativeSubscore * 10) / 10}</span>
          </div>
          <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden border border-slate-800">
            <div
              className="bg-amber-500 h-full rounded-full transition-all duration-300"
              style={{ width: `${Math.min(100, Math.max(0, negativeSubscore))}%` }}
            />
          </div>
        </div>

        {/* Peer Deviation - 20% */}
        <div>
          <div className="flex justify-between text-xs font-medium mb-1">
            <span className="text-slate-300">
              Peer Cohort Deviation <span className="text-slate-400 font-mono">(20% weight)</span>
            </span>
            <span className="text-slate-200 font-mono font-semibold">{Math.round(peerSubscore * 10) / 10}</span>
          </div>
          <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden border border-slate-800">
            <div
              className="bg-sky-500 h-full rounded-full transition-all duration-300"
              style={{ width: `${Math.min(100, Math.max(0, peerSubscore))}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
