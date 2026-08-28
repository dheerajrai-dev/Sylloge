export type SeverityLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFORMATIONAL';
export type SectorType = 'Banking' | 'Energy' | 'Healthcare' | 'Telecom' | 'Government' | 'Defense' | 'Fintech';
export type SizeTier = 'Tier-1' | 'Tier-2' | 'Tier-3';
export type RiskTier = 'LOW' | 'GUARDED' | 'ELEVATED' | 'CRITICAL';
export type TrendDirection = 'IMPROVING' | 'STABLE' | 'DETERIORATING';

export interface User {
  user_id: string;
  username: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
  last_login_at?: string;
}

export interface EntitySummary {
  entity_id: string;
  entity_code: string;
  name: string;
  sector: SectorType | string;
  size_tier: SizeTier | string;
  is_active: boolean;
  latest_risk_score?: number;
  latest_risk_tier?: RiskTier | string;
  latest_trend?: TrendDirection | string;
  open_findings_count: number;
}

export interface EntityDetail {
  entity: {
    entity_id: string;
    entity_code: string;
    name: string;
    sector: string;
    size_tier: string;
    contact_email?: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
  };
  latest_risk_score: number;
  execution_gap_score: number;
  negative_space_score: number;
  peer_deviation_score: number;
  risk_tier: string;
  trend_direction: string;
  open_findings_count: number;
}

export interface WorklistItem {
  entity_id: string;
  entity_code: string;
  name: string;
  sector: string;
  size_tier: string;
  composite_risk_score: number;
  execution_gap_score: number;
  negative_space_score: number;
  peer_deviation_score: number;
  risk_tier: string;
  trend_direction: string;
  open_findings_count: number;
  sparkline: number[];
  last_submission_date?: string;
}

export interface DashboardSummaryData {
  total_entities: number;
  critical_risk_entities: number;
  elevated_risk_entities: number;
  active_gap_findings: number;
  active_silence_findings: number;
  total_submissions: number;
  total_quarantined_rows: number;
  average_risk_score: number;
}

export interface UnifiedFinding {
  finding_id: string;
  entity_id: string;
  entity_name: string;
  engine: 'EXECUTION_GAP' | 'NEGATIVE_SPACE';
  rule_or_check_id: string;
  title: string;
  category: string;
  severity: SeverityLevel;
  period_start: string;
  period_end: string;
  status: 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED' | 'FALSE_POSITIVE';
  description: string;
  rationale: string;
  evidence_record_ids: string[];
  confidence: number;
  created_at: string;
}

export interface RationaleCardData {
  title: string;
  category: string;
  severity: string;
  rationale_text: string;
  evidence_record_ids: string[];
  raw_evidence_refs?: any[];
  metric_values?: Record<string, any>;
  recommended_action?: string;
}

export interface FindingDetailData {
  finding: UnifiedFinding;
  rationale_card: RationaleCardData;
  evidence_count: number;
}

export interface NormalizedEventRecord {
  event_id: string;
  submission_id?: string;
  dataset_type: string;
  standard_event_type: string;
  event_timestamp?: string;
  asset_id?: string;
  user_id?: string;
  action?: string;
  status?: string;
  severity?: string;
  raw_ref_id?: string;
  normalized_payload: Record<string, any>;
}

export interface RawDiffData {
  finding_id: string;
  normalized_events: any[];
  quarantined_rows: any[];
  raw_snippets: any[];
}

export interface SubmissionRecord {
  submission_id: string;
  entity_id: string;
  dataset_type: string;
  file_name: string;
  file_size_bytes: number;
  mime_type: string;
  minio_raw_path: string;
  sha256_hash: string;
  row_count: number;
  valid_row_count: number;
  quarantined_row_count: number;
  ingestion_status: string;
  error_summary?: string;
  uploaded_at: string;
  processed_at?: string;
}

export interface IngestionJobStatusData {
  job_id: string;
  submission_id: string;
  entity_id: string;
  dataset_type: string;
  status: string;
  progress_pct: number;
  total_rows: number;
  valid_rows: number;
  quarantined_rows: number;
  errors: any[];
  started_at: string;
  completed_at?: string;
}

export interface CohortDistribution {
  sector: string;
  size_tier: string;
  peer_group_size: number;
  mean_risk_score: number;
  p25: number;
  p50: number;
  p75: number;
  p90: number;
  is_low_confidence: boolean;
  entities: Array<{
    entity_id: string;
    name: string;
    score: number;
    tier: string;
  }>;
}

export interface EntityZScoreData {
  entity_id: string;
  entity_code: string;
  name: string;
  sector: string;
  size_tier: string;
  risk_score: number;
  sector_mean: number;
  z_score: number;
  is_outlier: boolean;
  is_low_confidence: boolean;
  peer_group_size: number;
}

export interface ComplianceReportExportData {
  report_id: string;
  generated_at: string;
  inspector: string;
  entity: {
    entity_id: string;
    entity_code: string;
    name: string;
    sector: string;
    size_tier: string;
  };
  executive_summary: string;
  composite_risk_score: number;
  risk_tier: string;
  subscores: {
    execution_gap: number;
    negative_space: number;
    peer_deviation: number;
  };
  weights_applied: {
    execution_gap: number;
    negative_space: number;
    peer_deviation: number;
  };
  critical_findings: Array<{
    title: string;
    rule_or_check_id: string;
    engine: string;
    severity: string;
    rationale: string;
    evidence_record_ids: string[];
  }>;
  sensor_silence_findings: Array<{
    title: string;
    rule_or_check_id: string;
    engine: string;
    severity: string;
    rationale: string;
    evidence_record_ids: string[];
  }>;
  peer_comparison: {
    sector: string;
    size_tier: string;
    peer_deviation_subscore: number;
    confidence: string;
  };
  audit_manifest?: {
    manifest_id: string;
    root_merkle_sha256: string;
    file_count: number;
    event_count: number;
    finding_count: number;
    generated_at: string;
    status: string;
  };
}
