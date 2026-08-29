import {
  EntitySummary,
  WorklistItem,
  DashboardSummaryData,
  UnifiedFinding,
  CohortDistribution,
  EntityZScoreData,
} from '../types';

export const mockDashboardSummary: DashboardSummaryData = {
  total_entities: 0,
  critical_risk_entities: 0,
  elevated_risk_entities: 0,
  active_gap_findings: 0,
  active_silence_findings: 0,
  total_submissions: 0,
  total_quarantined_rows: 0,
  average_risk_score: 0.0,
};

export const mockWorklist: WorklistItem[] = [];

export const mockEntities: EntitySummary[] = [];

export const mockFindings: UnifiedFinding[] = [];

export const mockCohorts: CohortDistribution[] = [];

export const mockZScores: EntityZScoreData[] = [];

