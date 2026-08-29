import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  ShieldAlert,
  CheckCircle,
  MessageSquarePlus,
  Download,
  Layers,
  Code2,
} from 'lucide-react';
import {
  fetchFindingDetail,
  fetchFindingEvidence,
  fetchFindingRawDiff,
  acknowledgeFinding,
  addFindingNote,
} from '../api/services';
import { FindingDetailData, NormalizedEventRecord, RawDiffData } from '../types';
import { RiskBadge } from '../components/common/RiskBadge';
import { Modal } from '../components/common/Modal';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { useNotification } from '../context/NotificationContext';

export const CaseDrillDownPage: React.FC = () => {
  const { findingId } = useParams<{ findingId: string }>();
  const [detail, setDetail] = useState<FindingDetailData | null>(null);
  const [evidence, setEvidence] = useState<NormalizedEventRecord[]>([]);
  const [rawDiff, setRawDiff] = useState<RawDiffData | null>(null);
  const [loading, setLoading] = useState(true);

  // Note Modal
  const [isNoteModalOpen, setIsNoteModalOpen] = useState(false);
  const [noteText, setNoteText] = useState('');
  const [isSubmittingNote, setIsSubmittingNote] = useState(false);

  const navigate = useNavigate();
  const { notify } = useNotification();

  const loadData = async () => {
    if (!findingId) return;
    setLoading(true);
    try {
      const [detData, evData, diffData] = await Promise.all([
        fetchFindingDetail(findingId),
        fetchFindingEvidence(findingId),
        fetchFindingRawDiff(findingId),
      ]);
      setDetail(detData);
      setEvidence(evData);
      setRawDiff(diffData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [findingId]);

  const handleAcknowledge = async () => {
    if (!findingId) return;
    try {
      await acknowledgeFinding(findingId);
      notify('success', 'Finding Acknowledged', 'Status updated to ACKNOWLEDGED');
      loadData();
    } catch (err: any) {
      notify('error', 'Action Failed', err.message);
    }
  };

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!findingId || !noteText) return;
    setIsSubmittingNote(true);
    try {
      await addFindingNote(findingId, noteText);
      notify('success', 'Note Appended', 'Supervisory note recorded on audit trail');
      setIsNoteModalOpen(false);
      setNoteText('');
      loadData();
    } catch (err: any) {
      notify('error', 'Failed to Add Note', err.message);
    } finally {
      setIsSubmittingNote(false);
    }
  };

  const handleExportJson = () => {
    if (!detail) return;
    const blob = new Blob([JSON.stringify({ detail, evidence, rawDiff }, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `evidence_case_${findingId}.json`;
    a.click();
    URL.revokeObjectURL(url);
    notify('info', 'Export Complete', 'Case evidence JSON downloaded');
  };

  if (loading || !detail) {
    return (
      <div className="py-20 flex justify-center">
        <LoadingSpinner size="lg" text="Loading Case Evidence & Rationale Card..." />
      </div>
    );
  }

  const { finding, rationale_card } = detail;

  return (
    <div className="space-y-6">
      {/* Back Button & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition w-fit"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Findings</span>
        </button>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleExportJson}
            className="flex items-center gap-2 px-3 py-2 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-lg text-xs font-medium text-slate-200 transition"
          >
            <Download className="w-3.5 h-3.5 text-brand-400" />
            <span>Export Evidence JSON</span>
          </button>

          <button
            onClick={() => setIsNoteModalOpen(true)}
            className="flex items-center gap-2 px-3 py-2 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-lg text-xs font-medium text-slate-200 transition"
          >
            <MessageSquarePlus className="w-3.5 h-3.5 text-amber-400" />
            <span>Add Audit Note</span>
          </button>

          <button
            onClick={handleAcknowledge}
            disabled={finding.status === 'ACKNOWLEDGED'}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-950/60 disabled:text-emerald-500 rounded-lg text-xs font-semibold text-white shadow-lg shadow-emerald-600/20 transition"
          >
            <CheckCircle className="w-4 h-4" />
            <span>{finding.status === 'ACKNOWLEDGED' ? 'Acknowledged' : 'Acknowledge Case'}</span>
          </button>
        </div>
      </div>

      {/* Rationale Card (Explainability Engine Output — 7-Part Structure) */}
      <div className="bg-surface-card border border-brand-800/40 rounded-xl p-6 shadow-2xl relative overflow-hidden bg-gradient-to-br from-slate-900 via-surface-card to-slate-950 space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-surface-border pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-brand-950 border border-brand-700/60 text-brand-400 shadow-md">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="text-xl font-bold text-white tracking-tight">{rationale_card.title}</h1>
                <RiskBadge level={rationale_card.severity} size="sm" />
                <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded bg-brand-950 text-brand-300 border border-brand-800">
                  {finding.engine}
                </span>
              </div>
              <p className="text-xs font-mono text-slate-400 mt-1">
                Rule ID: <strong className="text-brand-300">{finding.rule_or_check_id}</strong> • Entity: <strong className="text-slate-200">{finding.entity_name}</strong> • Category: <strong className="text-slate-200">{finding.category}</strong>
              </p>
            </div>
          </div>

          <div className="text-right">
            <span className="text-[11px] font-mono px-3 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
              Status: <strong className="text-emerald-400">{finding.status}</strong>
            </span>
          </div>
        </div>

        {/* 7-Part Plain-Language Supervisory Rationale */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* 1. What Happened */}
          <div className="p-4 rounded-xl bg-slate-950/90 border border-slate-800 space-y-1">
            <div className="text-[11px] font-bold uppercase tracking-wider text-brand-400 font-mono">1. What Happened</div>
            <p className="text-xs text-slate-200 leading-relaxed">{finding.description || rationale_card.title}</p>
          </div>

          {/* 2. Why SAT-SA Flagged It */}
          <div className="p-4 rounded-xl bg-slate-950/90 border border-slate-800 space-y-1">
            <div className="text-[11px] font-bold uppercase tracking-wider text-amber-400 font-mono">2. Why SAT-SA Flagged It</div>
            <p className="text-xs text-slate-200 leading-relaxed">{rationale_card.rationale_text}</p>
          </div>

          {/* 3. Source Files Used */}
          <div className="p-4 rounded-xl bg-slate-950/90 border border-slate-800 space-y-1">
            <div className="text-[11px] font-bold uppercase tracking-wider text-sky-400 font-mono">3. Source Dataset & Files</div>
            <div className="text-xs text-slate-200 font-mono space-y-1">
              <div>Dataset: <strong className="text-sky-300">{finding.category || 'Telemetry Submission'}</strong></div>
              <div>Source Files: <strong className="text-slate-100">{
                finding.engine === 'EXECUTION_GAP'
                  ? '04_escalation_records.csv / 02_case_management.csv'
                  : '05_asset_inventory.csv / 01_alert_metadata.csv / 07_coverage_reports.csv'
              }</strong></div>
            </div>
          </div>

          {/* 4. Related Records */}
          <div className="p-4 rounded-xl bg-slate-950/90 border border-slate-800 space-y-1">
            <div className="text-[11px] font-bold uppercase tracking-wider text-emerald-400 font-mono">4. Related Record IDs</div>
            <div className="text-xs text-slate-200 font-mono space-y-1">
              <div>Evidence Records: <strong className="text-emerald-300">{rationale_card.evidence_record_ids?.length || 0} items linked</strong></div>
              {rationale_card.raw_evidence_refs && rationale_card.raw_evidence_refs.length > 0 && (
                <div className="truncate">Refs: <strong className="text-slate-300">{rationale_card.raw_evidence_refs.map(r => typeof r === 'object' ? JSON.stringify(r) : String(r)).join(', ')}</strong></div>
              )}
            </div>
          </div>
        </div>

        {/* 5. Engine Metric Parameters */}
        {rationale_card.metric_values && Object.keys(rationale_card.metric_values).length > 0 && (
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2 font-mono">5. Measured Engine Metric Parameters</h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {Object.entries(rationale_card.metric_values).map(([k, v]) => (
                <div key={k} className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                  <div className="text-[10px] uppercase font-mono text-slate-400 truncate">{k.replace(/_/g, ' ')}</div>
                  <div className="text-sm font-mono font-bold text-brand-300 mt-0.5">{String(v)}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 6. Risk Impact & 7. Recommended Action */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-slate-800">
          <div className="p-3.5 rounded-lg bg-rose-950/30 border border-rose-800/40 text-xs text-rose-200">
            <span className="font-bold uppercase font-mono text-[11px] block text-rose-400 mb-0.5">6. Risk Impact Assessment</span>
            High-priority supervisory violation. May indicate unmonitored attack vectors, SLA gaming, or critical triage omissions.
          </div>

          <div className="p-3.5 rounded-lg bg-brand-950/40 border border-brand-800/40 text-xs text-brand-200">
            <span className="font-bold uppercase font-mono text-[11px] block text-brand-400 mb-0.5">7. Recommended Supervisory Action</span>
            {rationale_card.recommended_action || 'Mandate immediate SOC supervisor review and issue regulatory clarification.'}
          </div>
        </div>
      </div>

      {/* Dual-Pane Evidence Viewer */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pane 1: Canonical Normalized Event Evidence */}
        <div className="bg-surface-card border border-surface-border rounded-xl p-5 shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-brand-400" />
                <h3 className="text-sm font-bold text-white">Canonical Evidence Records & Source Rows</h3>
              </div>
              <span className="text-xs font-mono text-slate-400">{evidence.length || rationale_card.raw_evidence_refs?.length || 0} records</span>
            </div>

            {evidence.length === 0 && (!rationale_card.raw_evidence_refs || rationale_card.raw_evidence_refs.length === 0) ? (
              <div className="py-8 text-center text-xs text-amber-400 bg-slate-950 rounded-lg font-mono border border-amber-900/40">
                Evidence unavailable
              </div>
            ) : (
              <div className="space-y-3 max-h-[380px] overflow-y-auto pr-1">
                {evidence.map((ev, idx) => (
                  <div
                    key={ev.event_id || idx}
                    className="p-3.5 rounded-lg bg-slate-950 border border-surface-border text-xs space-y-1.5 font-mono"
                  >
                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <span className="font-bold text-brand-300">{ev.raw_ref_id || ev.event_id}</span>
                      <span>{ev.event_timestamp || 'N/A'}</span>
                    </div>
                    <div className="flex items-center gap-2 text-slate-200">
                      <span>Asset: <strong>{ev.asset_id || 'UNKNOWN'}</strong></span>
                      <span>•</span>
                      <span>Action: <strong>{ev.action || 'ALERT'}</strong></span>
                      <span>•</span>
                      <RiskBadge level={ev.severity || 'HIGH'} size="sm" showDot={false} />
                    </div>
                    <pre className="mt-2 p-2 rounded bg-slate-900 text-[11px] text-slate-300 overflow-x-auto">
                      {JSON.stringify(ev.normalized_payload, null, 2)}
                    </pre>
                  </div>
                ))}

                {evidence.length === 0 && rationale_card.raw_evidence_refs?.map((ref, idx) => (
                  <div key={idx} className="p-3.5 rounded-lg bg-slate-950 border border-surface-border text-xs space-y-1.5 font-mono">
                    <div className="text-[11px] text-brand-300 font-bold">Evidence Reference #{idx + 1}</div>
                    <pre className="p-2 rounded bg-slate-900 text-[11px] text-slate-300 overflow-x-auto">
                      {typeof ref === 'object' ? JSON.stringify(ref, null, 2) : String(ref)}
                    </pre>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Pane 2: Raw Submission & Quarantined Diff */}
        <div className="bg-surface-card border border-surface-border rounded-xl p-5 shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Code2 className="w-4 h-4 text-amber-400" />
                <h3 className="text-sm font-bold text-white">Quarantine & Raw Submission Diff</h3>
              </div>
              <span className="text-xs font-mono text-amber-400">
                {rawDiff?.quarantined_rows?.length || 0} quarantined rows
              </span>
            </div>

            {(!rawDiff || (rawDiff.quarantined_rows.length === 0 && rawDiff.raw_snippets.length === 0)) ? (
              <div className="py-8 text-center text-xs text-slate-400 bg-slate-950 rounded-lg">
                No quarantined discrepancies detected for this finding.
              </div>
            ) : (
              <div className="space-y-3 max-h-[380px] overflow-y-auto pr-1">
                {rawDiff.quarantined_rows.map((q, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-lg bg-red-950/30 border border-red-900/60 text-xs space-y-1 font-mono"
                  >
                    <div className="flex items-center justify-between text-red-400 font-bold text-[11px]">
                      <span>Quarantine Row #{q.row_index}</span>
                      <span>Validation Error</span>
                    </div>
                    <div className="text-slate-300 text-xs">{q.failure_reason}</div>
                    <div className="text-[11px] text-slate-400">
                      Failed Fields: {Array.isArray(q.failed_fields) ? q.failed_fields.join(', ') : 'unknown'}
                    </div>
                    <pre className="mt-2 p-2 rounded bg-slate-950 text-[11px] text-slate-300 overflow-x-auto border border-red-950">
                      {JSON.stringify(q.raw_content, null, 2)}
                    </pre>
                  </div>
                ))}

                {rawDiff.raw_snippets.map((s, idx) => (
                  <div key={idx} className="p-3.5 rounded-lg bg-slate-950 border border-surface-border text-xs space-y-1 font-mono">
                    <div className="text-slate-400 text-[11px]">Source: {s.source}</div>
                    <pre className="p-2 rounded bg-slate-900 text-[11px] text-slate-300 overflow-x-auto">
                      {s.preview}
                    </pre>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Note Modal */}
      <Modal isOpen={isNoteModalOpen} onClose={() => setIsNoteModalOpen(false)} title="Add Supervisory Audit Note">
        <form onSubmit={handleAddNote} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Supervisory Audit Comment
            </label>
            <textarea
              rows={4}
              required
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              placeholder="Record supervisory rationale, mitigation mandate, or regulatory inquiry details..."
              className="w-full bg-slate-950 border border-surface-border rounded-lg p-3 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-brand-500"
            />
          </div>

          <div className="pt-2 flex justify-end gap-2 border-t border-surface-border">
            <button
              type="button"
              onClick={() => setIsNoteModalOpen(false)}
              className="px-4 py-2 rounded-lg bg-slate-900 border border-surface-border text-xs text-slate-300 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmittingNote}
              className="px-4 py-2 bg-brand-600 hover:bg-brand-500 rounded-lg text-xs font-semibold text-white shadow-lg shadow-brand-600/30"
            >
              {isSubmittingNote ? 'Saving...' : 'Save Audit Note'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
