import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
} from 'lucide-react';
import { fetchCohortDistributions, fetchEntityZScores } from '../api/services';
import { CohortDistribution, EntityZScoreData } from '../types';
import { CohortDistributionChart } from '../components/charts/CohortDistributionChart';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

export const PeerBenchmarksPage: React.FC = () => {
  const [cohorts, setCohorts] = useState<CohortDistribution[]>([]);
  const [zscores, setZscores] = useState<EntityZScoreData[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSector, setSelectedSector] = useState('Banking');

  const loadData = async () => {
    setLoading(true);
    try {
      const [cohData, zData] = await Promise.all([
        fetchCohortDistributions(),
        fetchEntityZScores(selectedSector !== 'ALL' ? selectedSector : undefined),
      ]);
      setCohorts(cohData);
      setZscores(zData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedSector]);

  const activeCohort = cohorts.find((c) => c.sector === selectedSector) || cohorts[0];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Peer Cohort Benchmarks & Z-Score Analysis</h1>
          <p className="text-xs text-surface-muted mt-1">
            Statistical sector baselines, distribution bell curves, and entity standard deviation deviation metrics.
          </p>
        </div>

        {/* Sector Selector */}
        <div className="flex items-center gap-2">
          <select
            value={selectedSector}
            onChange={(e) => setSelectedSector(e.target.value)}
            className="bg-slate-950 border border-surface-border rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-brand-500"
          >
            <option value="Banking">Banking Sector</option>
            <option value="Energy">Energy Sector</option>
            <option value="Healthcare">Healthcare Sector</option>
            <option value="Telecom">Telecom Sector</option>
            <option value="Government">Government Sector</option>
            <option value="Fintech">Fintech Sector</option>
            <option value="Defense">Defense Sector</option>
          </select>
        </div>
      </div>

      {/* Low Cohort Size Warning Banner (N < 3) */}
      {activeCohort?.is_low_confidence && (
        <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-800/80 text-amber-200 text-xs flex items-start gap-3 shadow-lg">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <div className="font-bold text-sm text-amber-300">Sparse Peer Cohort (N &lt; 3) : Low Statistical Confidence</div>
            <div className="mt-1 text-slate-300">
              The {activeCohort.sector} cohort contains only {activeCohort.peer_group_size} registered entity/entities.
              Statistical Z-scores may exhibit elevated variance. Falling back to multi-tier macro sector baseline.
            </div>
          </div>
        </div>
      )}

      {/* Grid: Cohort Distribution & Summary Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Distribution Chart (2 cols) */}
        <div className="lg:col-span-2 bg-surface-card border border-surface-border rounded-xl p-6 shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-base font-bold text-white tracking-tight">
                {selectedSector} Sector Risk Score Distribution
              </h2>
              <span className="text-xs font-mono text-slate-400">
                Mean: <strong className="text-brand-300">{activeCohort?.mean_risk_score || 0}</strong>
              </span>
            </div>
            <p className="text-xs text-surface-muted mb-4">
              Histogram of composite scores across peer group members
            </p>

            {loading || !activeCohort ? (
              <LoadingSpinner size="md" />
            ) : (
              <CohortDistributionChart
                data={activeCohort.entities}
                meanScore={activeCohort.mean_risk_score}
                height={220}
              />
            )}
          </div>

          <div className="mt-4 pt-3 border-t border-surface-border flex justify-between text-xs text-slate-400 font-mono">
            <span>25th Percentile: {activeCohort?.p25 || 0}</span>
            <span>Median (50th): {activeCohort?.p50 || 0}</span>
            <span>75th Percentile: {activeCohort?.p75 || 0}</span>
            <span>90th Percentile: {activeCohort?.p90 || 0}</span>
          </div>
        </div>

        {/* Cohort Statistical Summary Card (1 col) */}
        <div className="bg-surface-card border border-surface-border rounded-xl p-6 shadow-xl flex flex-col justify-between">
          <div>
            <h2 className="text-base font-bold text-white tracking-tight">Cohort Baseline KPIs</h2>
            <p className="text-xs text-surface-muted mb-4">Calculated sector normalization reference metrics</p>

            <div className="space-y-3 font-mono text-xs">
              <div className="p-3 rounded-lg bg-slate-950 border border-surface-border flex justify-between items-center">
                <span className="text-slate-400">Peer Group Size (N)</span>
                <span className="font-bold text-slate-100">{activeCohort?.peer_group_size || 0} entities</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-950 border border-surface-border flex justify-between items-center">
                <span className="text-slate-400">Sector Mean Risk</span>
                <span className="font-bold text-brand-400">{activeCohort?.mean_risk_score || 0} / 100</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-950 border border-surface-border flex justify-between items-center">
                <span className="text-slate-400">Confidence Tier</span>
                <span className={`font-bold ${activeCohort?.is_low_confidence ? 'text-amber-400' : 'text-emerald-400'}`}>
                  {activeCohort?.is_low_confidence ? 'LOW (Sparse)' : 'HIGH (Sufficient)'}
                </span>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-surface-border text-[11px] text-surface-muted">
            Formula: Z = (EntityScore - CohortMean) / CohortStdDev
          </div>
        </div>
      </div>

      {/* Entity Z-Scores Table */}
      <div className="bg-surface-card border border-surface-border rounded-xl p-6 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-bold text-white tracking-tight">Entity Z-Score Deviation Rankings</h2>
            <p className="text-xs text-surface-muted">
              Standard deviations from sector mean. Outliers exceeding +2.0σ indicate elevated anomalous posture.
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-surface-border text-surface-muted uppercase text-[10px] tracking-wider">
                <th className="pb-3 font-semibold">Entity</th>
                <th className="pb-3 font-semibold">Sector / Tier</th>
                <th className="pb-3 font-semibold">Risk Score</th>
                <th className="pb-3 font-semibold">Cohort Mean</th>
                <th className="pb-3 font-semibold">Z-Score (σ)</th>
                <th className="pb-3 font-semibold text-right">Outlier Classification</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border/60">
              {zscores.map((z) => (
                <tr key={z.entity_id} className="hover:bg-slate-900/50 transition">
                  <td className="py-3.5">
                    <div className="font-semibold text-slate-100">{z.name}</div>
                    <div className="text-[11px] font-mono text-slate-400">{z.entity_code}</div>
                  </td>
                  <td className="py-3.5 text-slate-300">
                    {z.sector} • {z.size_tier}
                  </td>
                  <td className="py-3.5 font-mono font-bold text-slate-100">{z.risk_score}</td>
                  <td className="py-3.5 font-mono text-slate-400">{z.sector_mean}</td>
                  <td className="py-3.5 font-mono">
                    <span
                      className={`font-bold ${
                        z.z_score >= 2.0
                          ? 'text-red-400'
                          : z.z_score >= 1.0
                          ? 'text-amber-400'
                          : 'text-emerald-400'
                      }`}
                    >
                      {z.z_score > 0 ? `+${z.z_score}` : z.z_score} σ
                    </span>
                  </td>
                  <td className="py-3.5 text-right">
                    {z.is_outlier ? (
                      <span className="px-2.5 py-1 rounded text-[10px] font-bold font-mono bg-red-950 border border-red-800 text-red-400">
                        ANOMALOUS OUTLIER (&gt;2.0σ)
                      </span>
                    ) : (
                      <span className="px-2.5 py-1 rounded text-[10px] font-mono bg-slate-900 border border-slate-800 text-slate-400">
                        WITHIN NORMAL BAND
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
