-- SAT-SA (SYLLOGE) PostgreSQL Seed Script
-- Initializes default schema objects, initial supervisor user, and demo supervised entities

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Insert Default Supervisor User
-- Initial admin account (configured via .env / migration)
INSERT INTO users (
    user_id,
    username,
    password_hash,
    full_name,
    role,
    is_active,
    created_at
) VALUES (
    '00000000-0000-0000-0000-000000000001',
    'admin',
    '$2b$12$6xAfMuSvFNwjFyth0FUT0OwCpHi0mMEkPl3OICqwGUcl4nb5c00Q.',
    'Chief Cyber Supervisor',
    'supervisor',
    true,
    NOW()
) ON CONFLICT (username) DO NOTHING;

-- Insert 5 Demo Supervised Entities
INSERT INTO entities (
    entity_id,
    entity_code,
    name,
    sector,
    size_tier,
    contact_email,
    is_active,
    entity_metadata,
    created_at,
    updated_at
) VALUES 
(
    'c1f7a420-5692-4f3b-8511-9a72df894001',
    'BANK_ALPHA',
    'Apex National Bank',
    'Banking',
    'Tier-1',
    'soc-lead@bankalpha.internal',
    true,
    '{"tier_desc": "Systemically Important Financial Institution", "soc_tier": "24x7 In-House"}',
    NOW(),
    NOW()
),
(
    'c1f7a420-5692-4f3b-8511-9a72df894002',
    'TELCO_BETA',
    'Broadband Telecom Infra',
    'Telecom',
    'Tier-1',
    'cyber-ops@telcobeta.internal',
    true,
    '{"tier_desc": "National Backbone Carrier", "soc_tier": "Hybrid Managed"}',
    NOW(),
    NOW()
),
(
    'c1f7a420-5692-4f3b-8511-9a72df894003',
    'ENERGY_GAMMA',
    'Grid Power Corporation',
    'Energy',
    'Tier-2',
    'ot-security@energygamma.internal',
    true,
    '{"tier_desc": "Regional Transmission Operator", "soc_tier": "8x5 OT Specialist"}',
    NOW(),
    NOW()
),
(
    'c1f7a420-5692-4f3b-8511-9a72df894004',
    'HEALTH_DELTA',
    'Apex Healthcare Systems',
    'Healthcare',
    'Tier-2',
    'hipaa-soc@healthdelta.internal',
    true,
    '{"tier_desc": "Regional Hospital Network", "soc_tier": "Outsourced MSSP"}',
    NOW(),
    NOW()
),
(
    'c1f7a420-5692-4f3b-8511-9a72df894005',
    'FINTECH_EPSILON',
    'SwiftPay Technologies',
    'Fintech',
    'Tier-3',
    'ciso@swiftpay.internal',
    true,
    '{"tier_desc": "Payment Aggregator", "soc_tier": "Cloud Native SOC"}',
    NOW(),
    NOW()
)
ON CONFLICT (entity_code) DO NOTHING;

-- Insert Field Mapping Profiles for BANK_ALPHA
INSERT INTO field_mapping_profiles (
    profile_id,
    entity_id,
    dataset_type,
    version,
    mapping_rules,
    transform_rules,
    is_active,
    created_at,
    updated_at
) VALUES 
(
    'd2a1b3c4-0001-4000-8000-000000000001',
    'c1f7a420-5692-4f3b-8511-9a72df894001',
    'alert_metadata',
    1,
    '{"raw_ref_id": "alert_id", "event_timestamp": "timestamp", "severity": "severity", "action": "rule_name", "source_ip": "source_ip", "destination_ip": "destination_ip", "asset_id": "asset_id", "status": "status"}',
    '{"date_format": "ISO8601", "severity_map": {"CRITICAL": "CRITICAL", "HIGH": "HIGH", "MED": "MEDIUM", "LOW": "LOW"}}',
    true,
    NOW(),
    NOW()
),
(
    'd2a1b3c4-0001-4000-8000-000000000002',
    'c1f7a420-5692-4f3b-8511-9a72df894001',
    'case_management',
    1,
    '{"raw_ref_id": "case_id", "event_timestamp": "created_at", "status": "status", "severity": "priority", "user_id": "assigned_analyst", "action": "title"}',
    '{"date_format": "ISO8601"}',
    true,
    NOW(),
    NOW()
),
(
    'd2a1b3c4-0001-4000-8000-000000000003',
    'c1f7a420-5692-4f3b-8511-9a72df894001',
    'investigation_records',
    1,
    '{"raw_ref_id": "investigation_id", "event_timestamp": "timestamp", "user_id": "analyst_id", "action": "investigation_action"}',
    '{"date_format": "ISO8601"}',
    true,
    NOW(),
    NOW()
)
ON CONFLICT (entity_id, dataset_type, version) DO NOTHING;
