/**
 * Dataset Auto-Detection Engine for SAT-SA Offline Supervisory Enclave.
 * Implements multi-tiered heuristic analysis for all 8 canonical telemetry dataset types:
 * 1. alert_metadata
 * 2. case_management
 * 3. investigation_records
 * 4. escalation_records
 * 5. asset_inventory
 * 6. incident_reports
 * 7. coverage_reports
 * 8. analyst_activity
 */

export type CanonicalDatasetType =
  | 'alert_metadata'
  | 'case_management'
  | 'investigation_records'
  | 'escalation_records'
  | 'asset_inventory'
  | 'incident_reports'
  | 'coverage_reports'
  | 'analyst_activity';

export interface DatasetSchemaDefinition {
  type: CanonicalDatasetType;
  canonicalIndex: number;
  label: string;
  shortName: string;
  description: string;
  primaryKey: string;
  primaryKeyAliases: string[];
  discriminatorHeaders: string[];
  commonHeaders: string[];
  fileNameKeywords: string[];
  numberPrefix: string;
}

export interface DatasetDetectionResult {
  type: CanonicalDatasetType;
  label: string;
  shortName: string;
  description: string;
  confidence: number;
  matchedHeaders: string[];
  primaryKey: string;
}

export const CANONICAL_DATASETS: Record<CanonicalDatasetType, DatasetSchemaDefinition> = {
  alert_metadata: {
    type: 'alert_metadata',
    canonicalIndex: 1,
    label: '1. Alert Metadata',
    shortName: 'Alert Metadata',
    description: 'Raw security alerts from SIEM/EDR engines, alert signatures & IP mappings',
    primaryKey: 'alert_id',
    primaryKeyAliases: ['alert_id', 'alertid', 'alert_uid', 'incident_id', 'id'],
    discriminatorHeaders: ['rule_name', 'source_ip', 'destination_ip', 'signature_name', 'eventtime_utc', 'srcaddr', 'dstaddr'],
    commonHeaders: ['severity', 'status', 'description', 'criticality_tier', 'asset_id', 'owner', 'department', 'timestamp'],
    fileNameKeywords: ['alert', 'alerts', 'siem', 'edr', 'sensor_alerts'],
    numberPrefix: '01',
  },
  case_management: {
    type: 'case_management',
    canonicalIndex: 2,
    label: '2. Case Management',
    shortName: 'Case Management',
    description: 'SOC case tracking, SLA metrics, analyst ticket assignment & lifecycle status',
    primaryKey: 'case_id',
    primaryKeyAliases: ['case_id', 'caseid', 'ticket_id', 'case_number', 'id'],
    discriminatorHeaders: ['assigned_analyst', 'priority', 'closed_at', 'opened_at', 'ticket_id'],
    commonHeaders: ['created_at', 'updated_at', 'status', 'severity', 'title', 'description', 'notes'],
    fileNameKeywords: ['case', 'cases', 'ticket', 'tickets', 'case_management', 'triage_cases'],
    numberPrefix: '02',
  },
  investigation_records: {
    type: 'investigation_records',
    canonicalIndex: 3,
    label: '3. Investigation Records',
    shortName: 'Investigation Records',
    description: 'Forensic notes, analyst triage steps, time spent & investigation findings',
    primaryKey: 'investigation_id',
    primaryKeyAliases: ['investigation_id', 'inv_id', 'investigationid', 'id'],
    discriminatorHeaders: ['investigation_action', 'findings_summary', 'time_spent_minutes', 'analyst_id', 'inv_id'],
    commonHeaders: ['case_id', 'alert_id', 'timestamp', 'notes'],
    fileNameKeywords: ['investigation', 'investigations', 'inv', 'forensic', 'investigation_records'],
    numberPrefix: '03',
  },
  escalation_records: {
    type: 'escalation_records',
    canonicalIndex: 4,
    label: '4. Escalation Records',
    shortName: 'Escalation Records',
    description: 'Tier-1 to Tier-2/3 SOC handoffs, escalation reasons & approval statuses',
    primaryKey: 'escalation_id',
    primaryKeyAliases: ['escalation_id', 'esc_id', 'escalationid', 'id'],
    discriminatorHeaders: ['escalated_from', 'escalated_to', 'escalation_reason', 'approval_status', 'esc_id'],
    commonHeaders: ['case_id', 'alert_id', 'timestamp', 'notes'],
    fileNameKeywords: ['escalation', 'escalations', 'esc', 'tier_escalation', 'escalation_records'],
    numberPrefix: '04',
  },
  asset_inventory: {
    type: 'asset_inventory',
    canonicalIndex: 5,
    label: '5. Asset Inventory',
    shortName: 'Asset Inventory',
    description: 'Monitored critical infrastructure assets, IP addresses, OS & criticality tiers',
    primaryKey: 'asset_id',
    primaryKeyAliases: ['asset_id', 'assetid', 'device_id', 'id'],
    discriminatorHeaders: ['hostname', 'ip_address', 'asset_type', 'os', 'is_monitored', 'targethost', 'device_id'],
    commonHeaders: ['criticality_tier', 'department', 'owner'],
    fileNameKeywords: ['asset', 'assets', 'inventory', 'cmdb', 'hosts', 'asset_inventory'],
    numberPrefix: '05',
  },
  incident_reports: {
    type: 'incident_reports',
    canonicalIndex: 6,
    label: '6. Incident Reports',
    shortName: 'Incident Reports',
    description: 'Declared major security incidents, root causes, attack vectors & financial impact',
    primaryKey: 'incident_id',
    primaryKeyAliases: ['incident_id', 'incidentid', 'report_id', 'id'],
    discriminatorHeaders: ['root_cause', 'attack_vector', 'financial_impact', 'declared_at', 'contained_at'],
    commonHeaders: ['case_id', 'title', 'severity', 'closed_at'],
    fileNameKeywords: ['incident', 'incidents', 'major_incident', 'incident_reports', 'breach'],
    numberPrefix: '06',
  },
  coverage_reports: {
    type: 'coverage_reports',
    canonicalIndex: 7,
    label: '7. Coverage Reports',
    shortName: 'Coverage Reports',
    description: 'Sensor health, detection rule mapping, active sensors & uptime percentages',
    primaryKey: 'coverage_id',
    primaryKeyAliases: ['coverage_id', 'coverageid', 'report_id', 'id'],
    discriminatorHeaders: ['tool_name', 'source_type', 'total_assets_monitored', 'active_sensors', 'coverage_percentage', 'uptime_pct', 'event_count'],
    commonHeaders: ['asset_id', 'reported_at'],
    fileNameKeywords: ['coverage', 'coverage_reports', 'sensor', 'sensor_health', 'detection_coverage'],
    numberPrefix: '07',
  },
  analyst_activity: {
    type: 'analyst_activity',
    canonicalIndex: 8,
    label: '8. Analyst Activity',
    shortName: 'Analyst Activity',
    description: 'Analyst console timestamps, activity types, duration seconds & session IDs',
    primaryKey: 'activity_id',
    primaryKeyAliases: ['activity_id', 'activityid', 'log_id', 'id'],
    discriminatorHeaders: ['activity_type', 'duration_seconds', 'session_id', 'entity_ref_id', 'action_taken', 'shift_start', 'shift_end'],
    commonHeaders: ['analyst_id', 'timestamp', 'alert_id', 'case_id'],
    fileNameKeywords: ['activity', 'analyst', 'analyst_activity', 'shifts', 'console_activity', 'analyst_logs'],
    numberPrefix: '08',
  },
};

export const DATASET_LIST: DatasetSchemaDefinition[] = Object.values(CANONICAL_DATASETS).sort(
  (a, b) => a.canonicalIndex - b.canonicalIndex
);

/**
 * Extracts normalized header token strings from the first line of CSV, TSV, or JSON snippet.
 */
export function extractHeaderTokens(contentSnippet: string): string[] {
  if (!contentSnippet || typeof contentSnippet !== 'string') return [];

  const trimmed = contentSnippet.trim();
  if (!trimmed) return [];

  // Check if JSON format
  if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
    try {
      let parsed: any;
      if (trimmed.startsWith('[')) {
        parsed = JSON.parse(trimmed)[0];
      } else {
        parsed = JSON.parse(trimmed);
      }
      if (parsed && typeof parsed === 'object') {
        return Object.keys(parsed).map((k) => k.trim().toLowerCase());
      }
    } catch {
      // Fallback regex for keys in partial JSON snippet
      const regex = /"([a-zA-Z0-9_]+)"\s*:/g;
      const keys: string[] = [];
      let match;
      while ((match = regex.exec(trimmed)) !== null) {
        keys.push(match[1].toLowerCase());
      }
      if (keys.length > 0) return Array.from(new Set(keys));
    }
  }

  // Parse first line of CSV/TSV
  const firstLine = trimmed.split(/[\r\n]+/)[0] || '';
  // Determine delimiter
  let delimiter = ',';
  if (firstLine.includes('\t')) delimiter = '\t';
  else if (firstLine.includes(';') && !firstLine.includes(',')) delimiter = ';';
  else if (firstLine.includes('|') && !firstLine.includes(',')) delimiter = '|';

  return firstLine
    .split(delimiter)
    .map((h) => h.trim().replace(/^["']|["']$/g, '').trim().toLowerCase().replace(/[\s-]+/g, '_'))
    .filter((h) => h.length > 0);
}

/**
 * Multi-tiered auto-detection algorithm across all 8 canonical dataset types.
 * Evaluates primary keys, discriminator headers, common headers, and filename tokens.
 */
export function autoDetectDataset(fileName: string, contentSnippet: string = ''): DatasetDetectionResult {
  const cleanFileName = (fileName || '').toLowerCase();
  const headers = extractHeaderTokens(contentSnippet);

  let bestType: CanonicalDatasetType = 'alert_metadata';
  let bestScore = -1;
  let bestMatchedHeaders: string[] = [];

  for (const schema of DATASET_LIST) {
    let score = 0;
    const matched: string[] = [];

    // 1. Primary Key Check (Highest weight: 50 pts)
    for (const pk of schema.primaryKeyAliases) {
      if (headers.includes(pk)) {
        score += pk === schema.primaryKey ? 50 : 35;
        matched.push(pk);
        break;
      }
    }

    // 2. Discriminator Headers Check (20 pts per match)
    for (const disc of schema.discriminatorHeaders) {
      if (headers.includes(disc)) {
        score += 20;
        matched.push(disc);
      }
    }

    // 3. Common Headers Check (5 pts per match)
    for (const ch of schema.commonHeaders) {
      if (headers.includes(ch)) {
        score += 5;
        matched.push(ch);
      }
    }

    // 4. Filename Heuristic Check
    // Check numbered prefix e.g. 01_, 01-, 01.
    if (
      cleanFileName.startsWith(schema.numberPrefix + '_') ||
      cleanFileName.startsWith(schema.numberPrefix + '-') ||
      cleanFileName.startsWith(schema.numberPrefix + '.') ||
      cleanFileName.includes('/' + schema.numberPrefix + '_') ||
      cleanFileName.includes('\\' + schema.numberPrefix + '_')
    ) {
      score += 40;
    }

    let bestKwScore = 0;
    if (cleanFileName.includes(schema.type)) {
      bestKwScore = 35;
    } else {
      for (const kw of schema.fileNameKeywords) {
        if (cleanFileName.includes(kw)) {
          const kwScore = 20 + Math.min(kw.length, 15);
          if (kwScore > bestKwScore) {
            bestKwScore = kwScore;
          }
        }
      }
    }
    score += bestKwScore;

    if (score > bestScore) {
      bestScore = score;
      bestType = schema.type;
      bestMatchedHeaders = matched;
    }
  }

  // Calculate final confidence rating (capped between 40% and 100%)
  let confidence = 50;
  if (bestScore >= 70) {
    confidence = 100;
  } else if (bestScore >= 45) {
    confidence = 90;
  } else if (bestScore >= 25) {
    confidence = 75;
  } else if (bestScore > 0) {
    confidence = 60;
  }

  const def = CANONICAL_DATASETS[bestType];
  return {
    type: bestType,
    label: def.label,
    shortName: def.shortName,
    description: def.description,
    confidence,
    matchedHeaders: Array.from(new Set(bestMatchedHeaders)),
    primaryKey: def.primaryKey,
  };
}
