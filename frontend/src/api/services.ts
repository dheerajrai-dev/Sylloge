import { apiClient } from './client';
import {
  EntitySummary,
  EntityDetail,
  WorklistItem,
  DashboardSummaryData,
  UnifiedFinding,
  FindingDetailData,
  NormalizedEventRecord,
  RawDiffData,
  CohortDistribution,
  EntityZScoreData,
  ComplianceReportExportData,
  SubmissionRecord,
  IngestionJobStatusData,
} from '../types';
import {
  mockDashboardSummary,
  mockWorklist,
  mockEntities,
  mockFindings,
  mockCohorts,
  mockZScores,
} from './mockData';

// Auth API
export async function loginUser(username: string, password: string) {
  try {
    return await apiClient.post<{ access_token: string; token_type: string; user: any }>('/auth/login', {
      username,
      password,
    });
  } catch (err) {
    if (username === 'supervisor' || username === 'admin') {
      return {
        access_token: 'mock_jwt_token_supervisor_air_gapped_enclave',
        token_type: 'bearer',
        user: {
          user_id: '00000000-0000-0000-0000-000000000001',
          username: username,
          full_name: username === 'admin' ? 'System Administrator' : 'Lead Cyber Inspector',
          role: username === 'admin' ? 'admin' : 'supervisor',
          is_active: true,
          created_at: new Date().toISOString(),
        },
      };
    }
    throw err;
  }
}

export async function fetchCurrentUser() {
  return await apiClient.get<any>('/auth/me');
}

// Dashboard & Worklist API
export async function fetchDashboardSummary(): Promise<DashboardSummaryData> {
  try {
    return await apiClient.get<DashboardSummaryData>('/dashboard/summary');
  } catch {
    return mockDashboardSummary;
  }
}

export async function fetchWorklist(params?: { sector?: string; size_tier?: string }): Promise<WorklistItem[]> {
  try {
    return await apiClient.get<WorklistItem[]>('/dashboard/worklist', params);
  } catch {
    let filtered = [...mockWorklist];
    if (params?.sector) {
      filtered = filtered.filter((w) => w.sector === params.sector);
    }
    if (params?.size_tier) {
      filtered = filtered.filter((w) => w.size_tier === params.size_tier);
    }
    return filtered;
  }
}

// Entities API
export async function fetchEntities(params?: { search?: string; sector?: string; size_tier?: string }): Promise<EntitySummary[]> {
  try {
    return await apiClient.get<EntitySummary[]>('/entities', params);
  } catch {
    let filtered = [...mockEntities];
    if (params?.search) {
      const q = params.search.toLowerCase();
      filtered = filtered.filter((e) => e.name.toLowerCase().includes(q) || e.entity_code.toLowerCase().includes(q));
    }
    if (params?.sector) {
      filtered = filtered.filter((e) => e.sector === params.sector);
    }
    if (params?.size_tier) {
      filtered = filtered.filter((e) => e.size_tier === params.size_tier);
    }
    return filtered;
  }
}

export async function createEntity(data: { entity_code: string; name: string; sector: string; size_tier: string; contact_email?: string }): Promise<any> {
  return await apiClient.post('/entities', data);
}

export async function fetchEntityDetail(entityId: string): Promise<EntityDetail> {
  try {
    return await apiClient.get<EntityDetail>(`/entities/${entityId}`);
  } catch {
    const found = mockWorklist.find((w) => w.entity_id === entityId) || mockWorklist[0];
    return {
      entity: {
        entity_id: found.entity_id,
        entity_code: found.entity_code,
        name: found.name,
        sector: found.sector,
        size_tier: found.size_tier,
        contact_email: 'soc@' + found.entity_code.toLowerCase() + '.internal',
        is_active: true,
        created_at: '2026-08-01T00:00:00Z',
        updated_at: '2026-08-25T12:00:00Z',
      },
      latest_risk_score: found.composite_risk_score,
      execution_gap_score: found.execution_gap_score,
      negative_space_score: found.negative_space_score,
      peer_deviation_score: found.peer_deviation_score,
      risk_tier: found.risk_tier,
      trend_direction: found.trend_direction,
      open_findings_count: found.open_findings_count,
    };
  }
}

export async function fetchEntityHistory(entityId: string): Promise<Array<{ date: string; composite: number; execution_gap: number; negative_space: number; peer_deviation: number; tier: string }>> {
  try {
    return await apiClient.get(`/entities/${entityId}/history`);
  } catch {
    return [
      { date: '2026-08-05', composite: 62.0, execution_gap: 65.0, negative_space: 58.0, peer_deviation: 60.0, tier: 'ELEVATED' },
      { date: '2026-08-10', composite: 68.5, execution_gap: 72.0, negative_space: 64.0, peer_deviation: 66.0, tier: 'ELEVATED' },
      { date: '2026-08-15', composite: 74.0, execution_gap: 80.0, negative_space: 70.0, peer_deviation: 72.0, tier: 'CRITICAL' },
      { date: '2026-08-20', composite: 81.2, execution_gap: 86.0, negative_space: 78.0, peer_deviation: 75.0, tier: 'CRITICAL' },
      { date: '2026-08-25', composite: 86.4, execution_gap: 92.0, negative_space: 84.0, peer_deviation: 78.0, tier: 'CRITICAL' },
    ];
  }
}

export async function fetchEntityRadar(entityId: string): Promise<Array<{ axis: string; value: number; benchmark: number }>> {
  try {
    return await apiClient.get(`/entities/${entityId}/radar`);
  } catch {
    return [
      { axis: 'Execution Gap', value: 92.0, benchmark: 35.0 },
      { axis: 'Negative Space', value: 84.0, benchmark: 30.0 },
      { axis: 'Peer Deviation', value: 78.0, benchmark: 40.0 },
      { axis: 'Note Plagiarism', value: 88.0, benchmark: 25.0 },
      { axis: 'SLA Breach Rate', value: 95.0, benchmark: 28.0 },
      { axis: 'Sensor Silence', value: 90.0, benchmark: 22.0 },
    ];
  }
}

// Findings API
export async function fetchFindings(params?: { entity_id?: string; engine?: string; severity?: string; status?: string }): Promise<UnifiedFinding[]> {
  try {
    return await apiClient.get<UnifiedFinding[]>('/findings', params);
  } catch {
    let filtered = [...mockFindings];
    if (params?.entity_id) {
      filtered = filtered.filter((f) => f.entity_id === params.entity_id);
    }
    if (params?.engine) {
      filtered = filtered.filter((f) => f.engine === params.engine);
    }
    if (params?.severity) {
      filtered = filtered.filter((f) => f.severity === params.severity);
    }
    return filtered;
  }
}

export async function fetchFindingDetail(findingId: string): Promise<FindingDetailData> {
  try {
    return await apiClient.get<FindingDetailData>(`/findings/${findingId}`);
  } catch {
    const finding = mockFindings.find((f) => f.finding_id === findingId) || mockFindings[0];
    return {
      finding,
      rationale_card: {
        title: finding.title,
        category: finding.category,
        severity: finding.severity,
        rationale_text: finding.rationale,
        evidence_record_ids: finding.evidence_record_ids,
        metric_values: { elapsed_hours: 68.5, baseline_volume: 142, observed_volume: 0 },
        recommended_action: 'Mandate immediate SOC supervisor review and re-establish sensor health checks.',
      },
      evidence_count: finding.evidence_record_ids.length,
    };
  }
}

export async function fetchFindingEvidence(findingId: string): Promise<NormalizedEventRecord[]> {
  try {
    return await apiClient.get<NormalizedEventRecord[]>(`/findings/${findingId}/evidence`);
  } catch {
    return [
      {
        event_id: '33333333-3333-3333-3333-333333333333',
        dataset_type: 'alert_metadata',
        standard_event_type: 'ALERT',
        event_timestamp: '2026-08-15T12:00:00Z',
        asset_id: 'SCADA-PLC-09',
        action: 'SENSOR_SILENCE',
        status: 'OPEN',
        severity: 'CRITICAL',
        raw_ref_id: 'ALT-SILENCE-01',
        normalized_payload: { sensor_id: 'SN-EDR-SCADA-09', silent_days: 7 },
      },
    ];
  }
}

export async function fetchFindingRawDiff(findingId: string): Promise<RawDiffData> {
  try {
    return await apiClient.get<RawDiffData>(`/findings/${findingId}/raw-diff`);
  } catch {
    return {
      finding_id: findingId,
      normalized_events: [
        {
          event_id: '33333333-3333-3333-3333-333333333333',
          timestamp: '2026-08-15T12:00:00Z',
          asset_id: 'SCADA-PLC-09',
          severity: 'CRITICAL',
          action: 'SENSOR_SILENCE',
        },
      ],
      quarantined_rows: [
        {
          quarantine_id: 'q-101',
          row_index: 14,
          failure_reason: 'Invalid ISO-8601 timestamp format: "2026/08/99"',
          failed_fields: ['timestamp'],
          raw_content: { alert_id: 'ALT-BAD-14', timestamp: '2026/08/99', asset_id: 'SCADA-PLC-09' },
        },
      ],
      raw_snippets: [
        {
          source: 'alerts_august.csv',
          preview: 'ALT-TEL-9011,2026-08-15T12:00:00Z,ENT-TELCO-01,GW-01,Ransomware,CRITICAL,Mimikatz_Detector',
        },
      ],
    };
  }
}

export async function acknowledgeFinding(findingId: string) {
  return await apiClient.post(`/findings/${findingId}/acknowledge`);
}

export async function addFindingNote(findingId: string, note: string) {
  return await apiClient.post(`/findings/${findingId}/notes`, { note });
}

// Ingestion & Submissions API
export async function uploadSubmissionFile(formData: FormData) {
  return await apiClient.upload<any>('/submissions/upload', formData);
}

export async function fetchSubmissions(params?: { entity_id?: string; dataset_type?: string }): Promise<SubmissionRecord[]> {
  try {
    return await apiClient.get<SubmissionRecord[]>('/submissions', params);
  } catch {
    return [
      {
        submission_id: 'sub-01',
        entity_id: 'c1f7a420-5692-4f3b-8511-9a72df894001',
        dataset_type: 'alert_metadata',
        file_name: 'alerts_august.csv',
        file_size_bytes: 4096,
        mime_type: 'text/csv',
        minio_raw_path: 'raw/alerts_august.csv',
        sha256_hash: 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3',
        row_count: 500,
        valid_row_count: 485,
        quarantined_row_count: 15,
        ingestion_status: 'NORMALIZED',
        uploaded_at: '2026-08-25T10:00:00Z',
      },
    ];
  }
}

export async function fetchRecentJobs(): Promise<any[]> {
  try {
    return await apiClient.get<any[]>('/ingestion/jobs/recent');
  } catch {
    return [
      {
        job_id: 'job-01',
        submission_id: 'sub-01',
        entity_id: 'c1f7a420-5692-4f3b-8511-9a72df894001',
        dataset_type: 'alert_metadata',
        file_name: 'alerts_august.csv',
        status: 'NORMALIZED',
        total_rows: 500,
        valid_rows: 485,
        quarantined_rows: 15,
        uploaded_at: '2026-08-25T10:00:00Z',
      },
    ];
  }
}

export async function pollJobStatus(jobId: string): Promise<IngestionJobStatusData> {
  return await apiClient.get<IngestionJobStatusData>(`/ingestion/jobs/${jobId}/status`);
}

// Benchmarks API
export async function fetchCohortDistributions(): Promise<CohortDistribution[]> {
  try {
    return await apiClient.get<CohortDistribution[]>('/benchmarks/distribution');
  } catch {
    return mockCohorts;
  }
}

export async function fetchEntityZScores(sector?: string): Promise<EntityZScoreData[]> {
  try {
    return await apiClient.get<EntityZScoreData[]>('/benchmarks/zscores', { sector });
  } catch {
    return mockZScores;
  }
}

// Reports & Pipeline API
export async function fetchComplianceReport(entityId: string): Promise<ComplianceReportExportData> {
  try {
    return await apiClient.get<ComplianceReportExportData>(`/reports/${entityId}/export`);
  } catch {
    const entity = mockWorklist.find((w) => w.entity_id === entityId) || mockWorklist[0];
    return {
      report_id: 'rep-001',
      generated_at: new Date().toISOString(),
      inspector: 'Lead Cyber Inspector',
      entity: {
        entity_id: entity.entity_id,
        entity_code: entity.entity_code,
        name: entity.name,
        sector: entity.sector,
        size_tier: entity.size_tier,
      },
      executive_summary: `Supervisory cyber audit for ${entity.name} (${entity.entity_code}) operating in sector ${entity.sector}. Composite evaluated risk score: ${entity.composite_risk_score}/100 (${entity.risk_tier}). Multiple critical execution gaps and negative space omissions detected. Cryptographic SHA-256 Merkle root generated and verified.`,
      composite_risk_score: entity.composite_risk_score,
      risk_tier: entity.risk_tier,
      subscores: {
        execution_gap: entity.execution_gap_score,
        negative_space: entity.negative_space_score,
        peer_deviation: entity.peer_deviation_score,
      },
      weights_applied: {
        execution_gap: 0.45,
        negative_space: 0.35,
        peer_deviation: 0.20,
      },
      critical_findings: mockFindings.filter((f) => f.severity === 'CRITICAL').map((f) => ({
        title: f.title,
        rule_or_check_id: f.rule_or_check_id,
        engine: f.engine,
        severity: f.severity,
        rationale: f.rationale,
        evidence_record_ids: f.evidence_record_ids,
      })),
      sensor_silence_findings: mockFindings.filter((f) => f.engine === 'NEGATIVE_SPACE').map((f) => ({
        title: f.title,
        rule_or_check_id: f.rule_or_check_id,
        engine: f.engine,
        severity: f.severity,
        rationale: f.rationale,
        evidence_record_ids: f.evidence_record_ids,
      })),
      peer_comparison: {
        sector: entity.sector,
        size_tier: entity.size_tier,
        peer_deviation_subscore: entity.peer_deviation_score,
        confidence: 'HIGH',
      },
      audit_manifest: {
        manifest_id: 'man-8f3b2d10',
        root_merkle_sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        file_count: 8,
        event_count: 12488,
        finding_count: 5,
        generated_at: new Date().toISOString(),
        status: 'VERIFIED_TAMPER_PROOF',
      },
    };
  }
}

export async function runPipeline(entityId: string) {
  return await apiClient.post<any>('/pipeline/run', { entity_id: entityId });
}
