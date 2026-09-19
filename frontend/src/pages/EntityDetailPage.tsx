import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Building2,
  FileText,
  Play,
  ArrowLeft,
  Mail,
  ArrowRight,
  TrendingUp,
} from 'lucide-react';
import {
  fetchEntityDetail,
  fetchEntityHistory,
  fetchEntityRadar,
  fetchFindings,
  runPipeline,
} from '../api/services';
import { EntityDetail, UnifiedFinding } from '../types';
import { CompositeScoreGauge } from '../components/charts/CompositeScoreGauge';
import { TrendLineChart } from '../components/charts/TrendLineChart';
import { EngineRadarChart } from '../components/charts/EngineRadarChart';
import { RiskBadge } from '../components/common/RiskBadge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { useNotification } from '../context/NotificationContext';

export const EntityDetailPage: React.FC = () => {
  const { entityId } = useParams<{ entityId: string }>();
  const [detail, setDetail] = useState<EntityDetail | null>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [radar, setRadar] = useState<any[]>([]);
  const [findings, setFindings] = useState<UnifiedFinding[]>([]);
  const [loading, setLoading] = useState(true);
  const [runningAnalysis, setRunningAnalysis] = useState(false);

  const navigate = useNavigate();
  const { notify } = useNotification();

  const loadAll = async () => {
    if (!entityId) return;
    setLoading(true);
    try {
      const [detData, histData, radarData, findData] = await Promise.all([
        fetchEntityDetail(entityId),
        fetchEntityHistory(entityId),
        fetchEntityRadar(entityId),
        fetchFindings({ entity_id: entityId }),
      ]);
      setDetail(detData);
      setHistory(histData);
      setRadar(radarData);
      setFindings(findData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, [entityId]);

  const handleRunAnalysis = async () => {
    if (!entityId) return;
    setRunningAnalysis(true);
    try {
      await runPipeline(entityId);
      notify('success', 'Pipeline Execution Triggered', 'Analytics, Risk Scoring, and Merkle Manifest generated');
      await loadAll();
    } catch (err: any) {
      notify('error', 'Execution Failed', err.message || 'Pipeline error');
    } finally {
      setRunningAnalysis(false);
    }
  };

  if (loading || !detail) {
    return (
      <div className="py-20 flex justify-center">
        <LoadingSpinner size="lg" text="Loading Entity Profile & Risk Telemetry..." />
      </div>
    );
  }

  // Group findings by rule+title to collapse repetitive alerts
  type FindingGroup = { key: string; findings: UnifiedFinding[] };
  const groupedFindings: FindingGroup[] = Object.values(
    findings.reduce<Record<string, FindingGroup>>((acc, f) => {
      const key = `${f.rule_or_check_id}::${f.title}`;
      if (!acc[key]) acc[key] = { key, findings: [] };
      acc[key].findings.push(f);
      return acc;
    }, {})
  );

  return (
    <div className="space-y-6">
      {/* Top Bar Navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/entities')}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Entity Registry</span>
        </button>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRunAnalysis}
            disabled={runningAnalysis}
            className="flex items-center gap-2 px-3.5 py-2 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-lg text-xs font-semibold text-slate-200 shadow-md transition disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5 text-brand-400" />
            <span>{runningAnalysis ? 'Executing...' : 'Re-Run Analytics Pipeline'}</span>
          </button>

          <button
            onClick={() => navigate(`/reports/${entityId}`)}
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-500 rounded-lg text-xs font-semibold text-white shadow-lg shadow-brand-600/30 transition"
          >
            <FileText className="w-4 h-4" />
            <span>Generate Supervisory Report</span>
          </button>
        </div>
      </div>

      {/* Entity Profile Banner */}
      <div className="bg-surface-card border border-surface-border rounded-xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="flex items-start gap-4">
          <div className="w-14 h-14 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center text-brand-400 shadow-inner shrink-0">
            <Building2 className="w-7 h-7" />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-white tracking-tight">{detail.entity.name}</h1>
              <RiskBadge level={detail.risk_tier} size="md" />
            </div>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs text-slate-400 font-mono">
              <span>Code: <strong className="text-slate-200">{detail.entity.entity_code}</strong></span>
              <span>•</span>
              <span>Sector: <strong className="text-slate-200">{detail.entity.sector}</strong></span>
              <span>•</span>
              <span>Scale: <strong className="text-slate-200">{detail.entity.size_tier}</strong></span>
              {detail.entity.contact_email && (
                <>
                  <span>•</span>
                  <span className="flex items-center gap-1">
                    <Mail className="w-3.5 h-3.5" />
                    {detail.entity.contact_email}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-6 border-t md:border-t-0 md:border-l border-surface-border pt-4 md:pt-0 md:pl-6">
          <div className="text-center">
            <div className="text-xs text-surface-muted uppercase tracking-wider font-semibold">Active Gaps</div>
            <div className="text-2xl font-bold text-red-400 mt-1">{detail.open_findings_count}</div>
          </div>
          <div className="text-center">
            <div className="text-xs text-surface-muted uppercase tracking-wider font-semibold">Trend</div>
            <div className="text-sm font-semibold text-amber-400 mt-2 flex items-center gap-1">
              <TrendingUp className="w-4 h-4" />
              {detail.trend_direction}
            </div>
          </div>
        </div>
      </div>

      {/* Grid: 45/35/20 Formula Dial & 6-Engine Radar */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <CompositeScoreGauge
          score={detail.latest_risk_score || 0}
          gapSubscore={detail.execution_gap_score || 0}
          negativeSubscore={detail.negative_space_score || 0}
          peerSubscore={detail.peer_deviation_score || 0}
          riskTier={detail.risk_tier || 'LOW'}
        />

        <div className="bg-surface-card border border-surface-border rounded-xl p-6 shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-slate-200">Engine Multi-Axis Radar Profile</h3>
              <span className="text-xs font-mono text-slate-400">vs Sector Mean</span>
            </div>
            <p className="text-xs text-surface-muted mb-4">
              Evaluation across 6 engines: Gap, Negative Space, Note Plagiarism, SLA Breach, Sensor Silence, Peer Dev.
            </p>
            <EngineRadarChart data={radar} height={260} />
          </div>
        </div>
      </div>

      {/* Historical Trend Chart */}
      <div className="bg-surface-card border border-surface-border rounded-xl p-6 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-bold text-white tracking-tight">Historical Risk Trajectory & Scoring Waves</h3>
            <p className="text-xs text-surface-muted">Time-series tracking of composite and subscore components</p>
          </div>
        </div>
        <TrendLineChart data={history} height={260} />
      </div>

      {/* Active Supervisory Findings */}
      <div className="bg-surface-card border border-surface-border rounded-xl p-6 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-bold text-white tracking-tight">Active Supervisory Findings for {detail.entity.name}</h3>
            <p className="text-xs text-surface-muted">Detailed gap, omission, and correlation findings requiring supervisory review</p>
          </div>
          <span className="text-xs text-slate-400 font-mono">{findings.length} findings recorded ({groupedFindings.length} violation types)</span>
        </div>

        {findings.length === 0 ? (
          <div className="py-12 text-center text-slate-400 text-xs">
            No active compliance violations or negative space anomalies detected.
          </div>
        ) : (
          <div className="space-y-3">
            {groupedFindings.map((group) => (
              <EntityFindingGroupRow
                key={group.key}
                findings={group.findings}
                onInspect={(id) => navigate(`/findings/${id}`)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// Collapsible group row for EntityDetailPage
const EntityFindingGroupRow: React.FC<{
  findings: UnifiedFinding[];
  onInspect: (id: string) => void;
}> = ({ findings, onInspect }) => {
  const [expanded, setExpanded] = useState(false);
  const rep = findings[0];
  const count = findings.length;
  const totalEvidence = findings.reduce((s, f) => s + f.evidence_record_ids.length, 0);

  return (
    <div className="rounded-xl bg-slate-950/80 border border-surface-border hover:border-slate-700 transition overflow-hidden">
      <div className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1 flex-1">
          <div className="flex flex-wrap items-center gap-2.5">
            <RiskBadge level={rep.severity} size="sm" />
            <span className="font-bold text-slate-100 text-sm">{rep.title}</span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
              {rep.rule_or_check_id}
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-brand-950/60 border border-brand-800/60 text-brand-400">
              {rep.engine}
            </span>
            {count > 1 && (
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-red-900/50 border border-red-700/60 text-red-300 font-mono">
                ×{count} instances
              </span>
            )}
          </div>
          <p className="text-xs text-slate-300 line-clamp-2">{rep.description}</p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <span className="text-[11px] font-mono text-slate-400">
            {totalEvidence} evidence rows
          </span>
          {count === 1 ? (
            <button
              onClick={() => onInspect(rep.finding_id)}
              className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-brand-600 hover:text-white border border-slate-700 text-slate-300 text-xs font-medium inline-flex items-center gap-1 transition"
            >
              <span>Inspect Case</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          ) : (
            <button
              onClick={() => setExpanded((v) => !v)}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium inline-flex items-center gap-1.5 transition"
            >
              <span>{expanded ? 'Collapse' : `Show ${count} cases`}</span>
              <ArrowRight className={`w-3.5 h-3.5 transition-transform ${expanded ? 'rotate-90' : ''}`} />
            </button>
          )}
        </div>
      </div>

      {/* Expanded case rows */}
      {expanded && count > 1 && (
        <div className="border-t border-surface-border divide-y divide-surface-border/50 bg-slate-950/40">
          {findings.map((f) => (
            <div key={f.finding_id} className="px-4 py-2.5 flex items-center justify-between gap-4 hover:bg-slate-900/50 text-xs">
              <p className="text-slate-300 flex-1">{f.description}</p>
              <div className="flex items-center gap-3 shrink-0">
                <span className="text-[11px] font-mono text-slate-500">{f.evidence_record_ids.length} ev.</span>
                <button
                  onClick={() => onInspect(f.finding_id)}
                  className="px-2.5 py-1 rounded bg-slate-900 hover:bg-brand-600 hover:text-white border border-slate-700 text-slate-300 text-[11px] font-medium inline-flex items-center gap-1 transition"
                >
                  <span>Inspect</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
