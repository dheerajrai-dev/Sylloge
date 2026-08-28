import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  ShieldAlert,
  FileCheck2,
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

      {/* Rationale Card (Explainability Engine Output) */}
      <div className="bg-surface-card border border-brand-800/40 rounded-xl p-6 shadow-2xl relative overflow-hidden bg-gradient-to-br from-slate-900 via-surface-card to-slate-950">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4 border-b border-surface-border pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-brand-950 border border-brand-700/60 text-brand-400">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-white tracking-tight">{rationale_card.title}</h1>
                <RiskBadge level={rationale_card.severity} size="sm" />
              </div>
              <p className="text-xs font-mono text-slate-400 mt-0.5">
                Rule ID: <strong className="text-brand-300">{finding.rule_or_check_id}</strong> • Engine: <strong className="text-slate-200">{finding.engine}</strong> • Entity: <strong className="text-slate-200">{finding.entity_name}</strong>
              </p>
            </div>
          </div>

          <div className="text-right">
            <span className="text-[11px] font-mono px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
              Status: <strong className="text-emerald-400">{finding.status}</strong>
            </span>
          </div>
        </div>

        {/* Explainability Rationale Content */}
        <div className="space-y-4">
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-1">Supervisory Rationale & Derivation</h4>
            <div className="p-4 rounded-lg bg-slate-950/80 border border-surface-border text-xs text-slate-200 leading-relaxed font-sans">
              {rationale_card.rationale_text}
            </div>
          </div>

          {/* Metric Values Key/Value grid */}
          {rationale_card.metric_values && Object.keys(rationale_card.metric_values).length > 0 && (
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Engine Metric Parameters</h4>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {Object.entries(rationale_card.metric_values).map(([k, v]) => (
                  <div key={k} className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                    <div className="text-[10px] uppercase font-mono text-surface-muted truncate">{k.replace(/_/g, ' ')}</div>
                    <div className="text-sm font-mono font-bold text-brand-300 mt-0.5">{String(v)}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommended Action */}
          {rationale_card.recommended_action && (
            <div className="p-3 rounded-lg bg-brand-950/40 border border-brand-800/40 text-xs text-brand-200 flex items-start gap-2.5">
              <FileCheck2 className="w-4 h-4 text-brand-400 mt-0.5 shrink-0" />
              <div>
                <span className="font-semibold">Recommended Supervisory Action: </span>
                {rationale_card.recommended_action}
              </div>
            </div>
          )}
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
                <h3 className="text-sm font-bold text-white">Canonical Event Records</h3>
              </div>
              <span className="text-xs font-mono text-slate-400">{evidence.length} rows linked</span>
            </div>

            {evidence.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-400 bg-slate-950 rounded-lg">
                No normalized event rows linked.
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
                {rawDiff?.quarantined_rows.length || 0} quarantined rows
              </span>
            </div>

            {rawDiff?.quarantined_rows.length === 0 && rawDiff?.raw_snippets.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-400 bg-slate-950 rounded-lg">
                No quarantined discrepancies detected for this finding.
              </div>
            ) : (
              <div className="space-y-3 max-h-[380px] overflow-y-auto pr-1">
                {rawDiff?.quarantined_rows.map((q, idx) => (
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

                {rawDiff?.raw_snippets.map((s, idx) => (
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
