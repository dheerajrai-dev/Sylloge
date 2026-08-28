import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Building2,
  AlertOctagon,
  ShieldAlert,
  Radio,
  ArrowRight,
  RefreshCw,
  Layers,
} from 'lucide-react';
import { fetchDashboardSummary, fetchWorklist, fetchRecentJobs } from '../api/services';
import { DashboardSummaryData, WorklistItem } from '../types';
import { ScoreCard } from '../components/common/ScoreCard';
import { RiskBadge } from '../components/common/RiskBadge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { RiskMatrixScatter } from '../components/charts/RiskMatrixScatter';

export const DashboardPage: React.FC = () => {
  const [summary, setSummary] = useState<DashboardSummaryData | null>(null);
  const [worklist, setWorklist] = useState<WorklistItem[]>([]);
  const [recentJobs, setRecentJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [sectorFilter, setSectorFilter] = useState<string>('ALL');

  const navigate = useNavigate();

  const loadData = async () => {
    setLoading(true);
    try {
      const [sumData, wlData, jobsData] = await Promise.all([
        fetchDashboardSummary(),
        fetchWorklist(sectorFilter !== 'ALL' ? { sector: sectorFilter } : undefined),
        fetchRecentJobs(),
      ]);
      setSummary(sumData);
      setWorklist(wlData);
      setRecentJobs(jobsData);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [sectorFilter]);

  if (loading && !summary) {
    return (
      <div className="py-20 flex justify-center">
        <LoadingSpinner size="lg" text="Loading Supervisory Intelligence Dashboard..." />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Supervisory Worklist & Platform Overview</h1>
          <p className="text-xs text-surface-muted mt-1">
            Real-time cross-entity supervisory intelligence, execution gaps & sensor silence detections.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
            className="flex items-center gap-2 px-3 py-2 bg-surface-card hover:bg-surface-hover border border-surface-border rounded-lg text-xs font-medium text-slate-300 transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh Telemetry</span>
          </button>
          <button
            onClick={() => navigate('/upload')}
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-500 rounded-lg text-xs font-semibold text-white shadow-lg shadow-brand-600/30 transition"
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Ingest Telemetry</span>
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <ScoreCard
          title="Monitored Entities"
          value={summary?.total_entities || 0}
          subtitle="Across 5 Critical Sectors"
          icon={Building2}
          color="brand"
        />
        <ScoreCard
          title="Critical Risk Entities"
          value={summary?.critical_risk_entities || 0}
          subtitle="Score ≥ 75.0 / 100"
          icon={AlertOctagon}
          color="red"
          badge="ACTION REQUIRED"
        />
        <ScoreCard
          title="Active Execution Gaps"
          value={summary?.active_gap_findings || 0}
          subtitle="SLA & Triage Violations"
          icon={ShieldAlert}
          color="amber"
        />
        <ScoreCard
          title="Active Sensor Silence"
          value={summary?.active_silence_findings || 0}
          subtitle="Telemetry Outages & Cliffs"
          icon={Radio}
          color="slate"
        />
      </div>

      {/* Main Content Grid: Ranked Worklist & Risk Matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Ranked Worklist Table (2 cols) */}
        <div className="lg:col-span-2 bg-surface-card border border-surface-border rounded-xl p-6 shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-base font-bold text-white tracking-tight">Prioritized Supervisory Worklist</h2>
                <p className="text-xs text-surface-muted">Entities ranked by composite risk score (highest risk first)</p>
              </div>

              {/* Sector Filter */}
              <div className="flex items-center gap-2">
                <select
                  value={sectorFilter}
                  onChange={(e) => setSectorFilter(e.target.value)}
                  className="bg-slate-950 border border-surface-border rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-brand-500"
                >
                  <option value="ALL">All Sectors</option>
                  <option value="Banking">Banking</option>
                  <option value="Energy">Energy</option>
                  <option value="Healthcare">Healthcare</option>
                  <option value="Telecom">Telecom</option>
                  <option value="Government">Government</option>
                  <option value="Fintech">Fintech</option>
                  <option value="Defense">Defense</option>
                </select>
              </div>
            </div>

            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-surface-border text-surface-muted uppercase text-[10px] tracking-wider">
                    <th className="pb-3 font-semibold">Rank</th>
                    <th className="pb-3 font-semibold">Entity</th>
                    <th className="pb-3 font-semibold">Sector / Tier</th>
                    <th className="pb-3 font-semibold">Composite Score</th>
                    <th className="pb-3 font-semibold">Subscores (45/35/20)</th>
                    <th className="pb-3 font-semibold">Findings</th>
                    <th className="pb-3 font-semibold text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border/60">
                  {worklist.map((item, index) => (
                    <tr key={item.entity_id} className="hover:bg-slate-900/50 transition">
                      <td className="py-3.5 font-mono text-slate-400 font-bold">#{index + 1}</td>
                      <td className="py-3.5">
                        <div className="font-semibold text-slate-100">{item.name}</div>
                        <div className="text-[11px] font-mono text-slate-400">{item.entity_code}</div>
                      </td>
                      <td className="py-3.5">
                        <span className="px-2 py-0.5 rounded text-[11px] bg-slate-900 border border-slate-800 text-slate-300">
                          {item.sector} • {item.size_tier}
                        </span>
                      </td>
                      <td className="py-3.5">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-sm text-slate-100">{item.composite_risk_score}</span>
                          <RiskBadge level={item.risk_tier} size="sm" showDot={false} />
                        </div>
                      </td>
                      <td className="py-3.5">
                        <div className="flex items-center gap-1.5 w-28">
                          <div className="flex-1 bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800 flex">
                            <div className="bg-red-500 h-full" style={{ width: `${(item.execution_gap_score || 0) * 0.45}%` }} title={`Execution Gap (45%): ${item.execution_gap_score}`} />
                            <div className="bg-amber-500 h-full" style={{ width: `${(item.negative_space_score || 0) * 0.35}%` }} title={`Negative Space (35%): ${item.negative_space_score}`} />
                            <div className="bg-sky-500 h-full" style={{ width: `${(item.peer_deviation_score || 0) * 0.20}%` }} title={`Peer Dev (20%): ${item.peer_deviation_score}`} />
                          </div>
                        </div>
                      </td>
                      <td className="py-3.5">
                        <span className="font-mono font-medium text-slate-300">
                          {item.open_findings_count} open
                        </span>
                      </td>
                      <td className="py-3.5 text-right">
                        <button
                          onClick={() => navigate(`/entities/${item.entity_id}`)}
                          className="px-2.5 py-1.5 rounded-lg bg-slate-900 hover:bg-brand-600 hover:text-white border border-slate-700 text-slate-300 text-xs font-medium inline-flex items-center gap-1 transition"
                        >
                          <span>Drilldown</span>
                          <ArrowRight className="w-3 h-3" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-surface-border flex justify-between items-center text-xs text-slate-400">
            <span>Showing {worklist.length} prioritized entities</span>
            <button
              onClick={() => navigate('/entities')}
              className="text-brand-400 hover:text-brand-300 font-medium inline-flex items-center gap-1"
            >
              View Full Entity Registry &rarr;
            </button>
          </div>
        </div>

        {/* Risk Matrix Quadrant (1 col) */}
        <div className="bg-surface-card border border-surface-border rounded-xl p-6 shadow-xl flex flex-col justify-between">
          <div>
            <h2 className="text-base font-bold text-white tracking-tight">Risk Matrix Quadrant</h2>
            <p className="text-xs text-surface-muted mb-4">Execution Gap vs. Negative Space Anomaly distribution</p>
            <RiskMatrixScatter
              entities={worklist}
              height={260}
              onSelectEntity={(id) => navigate(`/entities/${id}`)}
            />
          </div>

          <div className="mt-4 pt-3 border-t border-surface-border text-[11px] text-surface-muted flex items-center justify-between">
            <span className="text-red-400 font-medium">Top-Right: Critical Dual Risk</span>
            <span>Click dot to inspect</span>
          </div>
        </div>
      </div>

      {/* Recent Telemetry Ingestion Activity */}
      <div className="bg-surface-card border border-surface-border rounded-xl p-6 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-bold text-white tracking-tight">Recent Ingestion Batches & Telemetry Feeds</h2>
            <p className="text-xs text-surface-muted">Live status of uploaded datasets across supervised entities</p>
          </div>
          <button
            onClick={() => navigate('/upload')}
            className="text-xs text-brand-400 hover:text-brand-300 font-medium"
          >
            Upload New Batch &rarr;
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {recentJobs.slice(0, 4).map((job) => (
            <div
              key={job.submission_id || job.job_id}
              className="p-4 rounded-lg bg-slate-950/80 border border-surface-border flex flex-col justify-between hover:border-slate-700 transition"
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-semibold text-slate-200">{job.dataset_type}</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 border border-emerald-800 text-emerald-400">
                    {job.status}
                  </span>
                </div>
                <div className="text-xs text-slate-400 truncate">{job.file_name}</div>
              </div>

              <div className="mt-3 pt-2 border-slate-900 flex justify-between text-[11px] text-slate-400">
                <span>{job.valid_rows || 0} valid rows</span>
                {job.quarantined_rows > 0 ? (
                  <span className="text-amber-400 font-medium">{job.quarantined_rows} quarantined</span>
                ) : (
                  <span className="text-slate-400">0 quarantined</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
