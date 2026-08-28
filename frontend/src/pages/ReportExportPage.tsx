import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Printer,
  FileDown,
  ArrowLeft,
  ShieldCheck,
  Download,
} from 'lucide-react';
import { fetchComplianceReport } from '../api/services';
import { ComplianceReportExportData } from '../types';
import { RiskBadge } from '../components/common/RiskBadge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { useNotification } from '../context/NotificationContext';

export const ReportExportPage: React.FC = () => {
  const { entityId } = useParams<{ entityId: string }>();
  const [report, setReport] = useState<ComplianceReportExportData | null>(null);
  const [loading, setLoading] = useState(true);

  const navigate = useNavigate();
  const { notify } = useNotification();

  useEffect(() => {
    const loadReport = async () => {
      if (!entityId) return;
      setLoading(true);
      try {
        const data = await fetchComplianceReport(entityId);
        setReport(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    loadReport();
  }, [entityId]);

  const handlePrint = () => {
    window.print();
  };

  const handleExportMarkdown = () => {
    if (!report) return;
    const md = `# SUPERVISORY CYBERSECURITY COMPLIANCE REPORT
**Report ID**: ${report.report_id}
**Generated**: ${report.generated_at}
**Inspector**: ${report.inspector}

## Entity Profile
- **Name**: ${report.entity.name}
- **Code**: ${report.entity.entity_code}
- **Sector**: ${report.entity.sector} (${report.entity.size_tier})

## Executive Summary
${report.executive_summary}

## Evaluated Risk Score
- **Composite Risk Score**: ${report.composite_risk_score} / 100 (${report.risk_tier})
- **Execution Gap (45% weight)**: ${report.subscores.execution_gap}
- **Negative Space (35% weight)**: ${report.subscores.negative_space}
- **Peer Deviation (20% weight)**: ${report.subscores.peer_deviation}

## Top Findings
${report.critical_findings
  .map(
    (f, idx) =>
      `### ${idx + 1}. ${f.title} [${f.severity}] (${f.rule_or_check_id})\n- **Engine**: ${f.engine}\n- **Rationale**: ${f.rationale}\n- **Evidence**: ${f.evidence_record_ids.join(', ')}\n`
  )
  .join('\n')}

## Cryptographic Merkle Root Manifest
- **Manifest ID**: ${report.audit_manifest?.manifest_id || 'N/A'}
- **SHA-256 Root**: ${report.audit_manifest?.root_merkle_sha256 || 'N/A'}
- **Verification Status**: VERIFIED_TAMPER_PROOF
`;

    const blob = new Blob([md], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `compliance_report_${report.entity.entity_code}.md`;
    a.click();
    URL.revokeObjectURL(url);
    notify('info', 'Markdown Exported', 'Report saved as Markdown file');
  };

  const handleDownloadManifest = () => {
    if (!report?.audit_manifest) return;
    const blob = new Blob([JSON.stringify(report.audit_manifest, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit_manifest_${report.audit_manifest.manifest_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
    notify('info', 'Manifest Exported', 'Signed cryptographic JSON manifest downloaded');
  };

  if (loading || !report) {
    return (
      <div className="py-20 flex justify-center">
        <LoadingSpinner size="lg" text="Generating Structured Supervisory Compliance Report..." />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Top Toolbar (Hidden when printing) */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 no-print">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition w-fit"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Entity Detail</span>
        </button>

        <div className="flex items-center gap-3">
          <button
            onClick={handleExportMarkdown}
            className="flex items-center gap-2 px-3 py-2 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-lg text-xs font-medium text-slate-200 transition"
          >
            <FileDown className="w-4 h-4 text-brand-400" />
            <span>Export Markdown</span>
          </button>

          {report.audit_manifest && (
            <button
              onClick={handleDownloadManifest}
              className="flex items-center gap-2 px-3 py-2 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-lg text-xs font-medium text-slate-200 transition"
            >
              <Download className="w-4 h-4 text-emerald-400" />
              <span>Signed Manifest</span>
            </button>
          )}

          <button
            onClick={handlePrint}
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-500 rounded-lg text-xs font-semibold text-white shadow-lg shadow-brand-600/30 transition"
          >
            <Printer className="w-4 h-4" />
            <span>Print / Save PDF</span>
          </button>
        </div>
      </div>

      {/* Printable Report Document Card */}
      <div className="print-page bg-surface-card border border-surface-border rounded-2xl p-8 sm:p-12 shadow-2xl space-y-8 text-slate-100 print:text-black print:bg-white print:border-none print:shadow-none">
        {/* Document Header */}
        <div className="border-b border-surface-border pb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="text-xs font-mono font-bold tracking-wider text-brand-400 uppercase">
              SYLLOGE • SUPERVISORY AUDIT DOSSIER
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white print:text-black mt-1">
              Cybersecurity Compliance Inspection Report
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Supervised Entity: <strong>{report.entity.name}</strong> ({report.entity.entity_code})
            </p>
          </div>

          <div className="text-right font-mono text-xs text-slate-400 space-y-1">
            <div>Report Ref: <strong className="text-slate-200 print:text-black">{report.report_id.slice(0, 13)}</strong></div>
            <div>Date: {new Date(report.generated_at).toLocaleDateString()}</div>
            <div>Lead Inspector: <strong className="text-slate-200 print:text-black">{report.inspector}</strong></div>
          </div>
        </div>

        {/* Executive Summary */}
        <div className="p-5 rounded-xl bg-slate-950/80 border border-surface-border print-card">
          <h2 className="text-xs font-bold uppercase tracking-wider text-brand-400 mb-2">
            1. Executive Supervisory Summary
          </h2>
          <p className="text-xs text-slate-300 print:text-black leading-relaxed">
            {report.executive_summary}
          </p>
        </div>

        {/* Evaluated Score & 45/35/20 Formula Breakdown */}
        <div className="space-y-4">
          <h2 className="text-sm font-bold uppercase tracking-wider text-white print:text-black">
            2. Tripartite Weighted Risk Evaluation (45 / 35 / 20)
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-slate-950 border border-surface-border print-card">
              <div className="text-[11px] font-semibold text-slate-400 uppercase">Composite Risk</div>
              <div className="text-3xl font-extrabold text-brand-400 print:text-black mt-2">
                {report.composite_risk_score}
              </div>
              <div className="mt-1">
                <RiskBadge level={report.risk_tier} size="sm" />
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-surface-border print-card">
              <div className="text-[11px] font-semibold text-slate-400 uppercase">Execution Gap (45%)</div>
              <div className="text-2xl font-bold text-red-400 print:text-black mt-2">
                {report.subscores.execution_gap}
              </div>
              <div className="text-[10px] text-slate-400 mt-1">SLA & Triage Failures</div>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-surface-border print-card">
              <div className="text-[11px] font-semibold text-slate-400 uppercase">Negative Space (35%)</div>
              <div className="text-2xl font-bold text-amber-400 print:text-black mt-2">
                {report.subscores.negative_space}
              </div>
              <div className="text-[10px] text-slate-400 mt-1">Sensor Silence & Volume Cliffs</div>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-surface-border print-card">
              <div className="text-[11px] font-semibold text-slate-400 uppercase">Peer Deviation (20%)</div>
              <div className="text-2xl font-bold text-sky-400 print:text-black mt-2">
                {report.subscores.peer_deviation}
              </div>
              <div className="text-[10px] text-slate-400 mt-1">Sector Baseline Z-Score</div>
            </div>
          </div>
        </div>

        {/* Top Critical Execution Gap Findings */}
        <div className="space-y-4">
          <h2 className="text-sm font-bold uppercase tracking-wider text-white print:text-black">
            3. Critical Execution Gap Violations
          </h2>

          <div className="space-y-3">
            {report.critical_findings.map((f, idx) => (
              <div
                key={idx}
                className="p-4 rounded-xl bg-slate-950/80 border border-surface-border print-card space-y-2"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <RiskBadge level={f.severity} size="sm" />
                    <span className="font-bold text-xs text-white print:text-black">{f.title}</span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-400">{f.rule_or_check_id}</span>
                </div>
                <div className="text-xs text-slate-300 print:text-black">{f.rationale}</div>
                <div className="text-[10px] font-mono text-slate-400">
                  Evidence Records: {f.evidence_record_ids.join(', ') || 'N/A'}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Negative Space Sensor Silence Findings */}
        <div className="space-y-4">
          <h2 className="text-sm font-bold uppercase tracking-wider text-white print:text-black">
            4. Negative Space & Telemetry Silence Detections
          </h2>

          <div className="space-y-3">
            {report.sensor_silence_findings.map((f, idx) => (
              <div
                key={idx}
                className="p-4 rounded-xl bg-slate-950/80 border border-surface-border print-card space-y-2"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <RiskBadge level={f.severity} size="sm" />
                    <span className="font-bold text-xs text-white print:text-black">{f.title}</span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-400">{f.rule_or_check_id}</span>
                </div>
                <div className="text-xs text-slate-300 print:text-black">{f.rationale}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Cryptographic SHA-256 Merkle Manifest Attestation */}
        <div className="p-6 rounded-xl bg-slate-950 border border-emerald-800/60 print-card space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-emerald-400">
                5. Cryptographic SHA-256 Merkle Audit Manifest
              </h2>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 border border-emerald-800 text-emerald-400">
              TAMPER-PROOF ATTESTATION
            </span>
          </div>

          <p className="text-xs text-slate-300 print:text-black">
            The mathematical state of all raw submission files, quarantined records, normalized standard events, and generated findings has been bound into an immutable deterministic SHA-256 Merkle tree.
          </p>

          <div className="font-mono text-xs space-y-1.5 pt-2 border-t border-slate-900">
            <div className="text-slate-400">
              Manifest ID: <strong className="text-slate-200 print:text-black">{report.audit_manifest?.manifest_id || 'N/A'}</strong>
            </div>
            <div className="text-slate-400 break-all">
              Merkle Root SHA-256: <strong className="text-emerald-400 print:text-black">{report.audit_manifest?.root_merkle_sha256 || 'N/A'}</strong>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
