import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  ArrowRight,
} from 'lucide-react';
import { fetchFindings } from '../api/services';
import { UnifiedFinding } from '../types';
import { RiskBadge } from '../components/common/RiskBadge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

export const FindingsListPage: React.FC = () => {
  const [findings, setFindings] = useState<UnifiedFinding[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [engineFilter, setEngineFilter] = useState('ALL');
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');

  const navigate = useNavigate();

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await fetchFindings();
      setFindings(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filteredFindings = findings.filter((f) => {
    const matchesSearch =
      search === '' ||
      f.title.toLowerCase().includes(search.toLowerCase()) ||
      f.rule_or_check_id.toLowerCase().includes(search.toLowerCase()) ||
      f.entity_name.toLowerCase().includes(search.toLowerCase()) ||
      f.description.toLowerCase().includes(search.toLowerCase());

    const matchesEngine = engineFilter === 'ALL' || f.engine === engineFilter;
    const matchesSeverity = severityFilter === 'ALL' || f.severity === severityFilter;
    const matchesStatus = statusFilter === 'ALL' || f.status === statusFilter;

    return matchesSearch && matchesEngine && matchesSeverity && matchesStatus;
  });

  // Group by rule+title — one card per violation type, not per alert
  type Group = { key: string; findings: UnifiedFinding[] };
  const grouped: Group[] = Object.values(
    filteredFindings.reduce<Record<string, Group>>((acc, f) => {
      const key = `${f.rule_or_check_id}::${f.title}`;
      if (!acc[key]) acc[key] = { key, findings: [] };
      acc[key].findings.push(f);
      return acc;
    }, {})
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Supervisory Findings & Evidence Center</h1>
          <p className="text-xs text-surface-muted mt-1">
            Aggregated catalog of execution gap violations, sensor silence alerts, and correlation anomalies.
          </p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-surface-card border border-surface-border rounded-xl p-4 shadow-lg flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="relative flex-1 w-full md:max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search findings by rule, entity, or keyword..."
            className="w-full bg-slate-950 border border-surface-border rounded-lg pl-10 pr-4 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-brand-500"
          />
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto overflow-x-auto">
          <select
            value={engineFilter}
            onChange={(e) => setEngineFilter(e.target.value)}
            className="bg-slate-950 border border-surface-border rounded-lg px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-brand-500"
          >
            <option value="ALL">All Engines</option>
            <option value="EXECUTION_GAP">Execution Gap Engine</option>
            <option value="NEGATIVE_SPACE">Negative Space Engine</option>
          </select>

          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="bg-slate-950 border border-surface-border rounded-lg px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-brand-500"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-950 border border-surface-border rounded-lg px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-brand-500"
          >
            <option value="ALL">All Statuses</option>
            <option value="OPEN">Open</option>
            <option value="ACKNOWLEDGED">Acknowledged</option>
          </select>
        </div>
      </div>

      {/* Grouped Findings */}
      <div className="space-y-4">
        {loading ? (
          <div className="py-16">
            <LoadingSpinner size="lg" text="Loading Findings..." />
          </div>
        ) : grouped.length === 0 ? (
          <div className="py-16 text-center text-slate-400 text-xs bg-surface-card border border-surface-border rounded-xl">
            No supervisory findings match the current filter selection.
          </div>
        ) : (
          grouped.map((group) => (
            <GroupCard
              key={group.key}
              findings={group.findings}
              onInspect={(id) => navigate(`/findings/${id}`)}
            />
          ))
        )}
      </div>
    </div>
  );
};

// Each card owns its expand state — no lift needed
const GroupCard: React.FC<{
  findings: UnifiedFinding[];
  onInspect: (id: string) => void;
}> = ({ findings, onInspect }) => {
  const [expanded, setExpanded] = useState(false);
  const rep = findings[0];
  const count = findings.length;
  const totalEvidence = findings.reduce((s, f) => s + f.evidence_record_ids.length, 0);

  return (
    <div className="bg-surface-card border border-surface-border rounded-xl shadow-lg hover:border-slate-600 transition">
      {/* Group header */}
      <div className="p-5 flex flex-col md:flex-row md:items-start justify-between gap-5">
        <div className="space-y-2.5 flex-1">
          <div className="flex flex-wrap items-center gap-2.5">
            <RiskBadge level={rep.severity} size="md" />
            <h3 className="text-base font-bold text-white tracking-tight">{rep.title}</h3>
            <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-md bg-slate-900 border border-slate-800 text-slate-300">
              {rep.rule_or_check_id}
            </span>
            <span className="text-[11px] px-2.5 py-0.5 rounded-md bg-brand-950/60 border border-brand-800/60 text-brand-400 font-mono">
              {rep.engine}
            </span>
            {count > 1 && (
              <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-md bg-red-900/50 border border-red-700/60 text-red-300">
                ×{count} instances
              </span>
            )}
          </div>

          <p className="text-xs text-slate-300 leading-relaxed">{rep.description}</p>

          <div className="p-3 rounded-lg bg-slate-950/70 border border-surface-border/80 text-xs text-slate-300">
            <span className="font-semibold text-slate-100">Supervisory Rationale: </span>
            {rep.rationale}
          </div>

          <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-slate-400 pt-1">
            <span>Entity: <strong className="text-slate-200">{rep.entity_name}</strong></span>
            <span>•</span>
            <span>Category: <strong className="text-slate-200">{rep.category}</strong></span>
            <span>•</span>
            <span>Evidence: <strong className="text-brand-400">{totalEvidence} records</strong></span>
            <span>•</span>
            <span>Status: <strong className="text-slate-200">{rep.status}</strong></span>
          </div>
        </div>

        <div className="shrink-0 flex md:flex-col items-end justify-between gap-3 pt-2 md:pt-0">
          {count === 1 ? (
            <button
              onClick={() => onInspect(rep.finding_id)}
              className="px-4 py-2 bg-brand-600 hover:bg-brand-500 rounded-lg text-xs font-semibold text-white shadow-lg shadow-brand-600/30 flex items-center gap-1.5 transition"
            >
              <span>Inspect Case</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={() => setExpanded((v) => !v)}
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-xs font-semibold text-white flex items-center gap-1.5 transition"
            >
              <span>{expanded ? 'Collapse' : `Show ${count} cases`}</span>
              <ArrowRight className={`w-4 h-4 transition-transform ${expanded ? 'rotate-90' : ''}`} />
            </button>
          )}
        </div>
      </div>

      {/* Expanded case rows */}
      {expanded && (
        <div className="border-t border-surface-border divide-y divide-surface-border/60">
          {findings.map((f) => (
            <div key={f.finding_id} className="px-5 py-3 flex items-center gap-4 hover:bg-slate-900/40">
              <p className="text-xs text-slate-300 flex-1 leading-relaxed">{f.description}</p>
              <span className="text-[11px] text-slate-500 font-mono shrink-0">{f.evidence_record_ids.length} evidence</span>
              <button
                onClick={() => onInspect(f.finding_id)}
                className="shrink-0 px-3 py-1.5 bg-brand-600 hover:bg-brand-500 rounded-lg text-[11px] font-semibold text-white flex items-center gap-1 transition"
              >
                Inspect <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
