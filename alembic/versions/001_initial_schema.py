"""001_initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-08-25 11:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from shared.db.base import GUID, JSONType

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        'users',
        sa.Column('user_id', GUID, primary_key=True),
        sa.Column('username', sa.String(64), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(128), nullable=False),
        sa.Column('role', sa.String(32), nullable=False, server_default='supervisor'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_users_username', 'users', ['username'])

    # 2. entities
    op.create_table(
        'entities',
        sa.Column('entity_id', GUID, primary_key=True),
        sa.Column('entity_code', sa.String(32), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('sector', sa.String(64), nullable=False),
        sa.Column('size_tier', sa.String(16), nullable=False),
        sa.Column('contact_email', sa.String(128), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('entity_metadata', JSONType, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_entities_sector_tier', 'entities', ['sector', 'size_tier'])
    op.create_index('idx_entities_code', 'entities', ['entity_code'])

    # 3. field_mapping_profiles
    op.create_table(
        'field_mapping_profiles',
        sa.Column('profile_id', GUID, primary_key=True),
        sa.Column('entity_id', GUID, sa.ForeignKey('entities.entity_id', ondelete='CASCADE'), nullable=False),
        sa.Column('dataset_type', sa.String(64), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('mapping_rules', JSONType, nullable=False),
        sa.Column('transform_rules', JSONType, nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('entity_id', 'dataset_type', 'version', name='uq_entity_dataset_version'),
    )
    op.create_index('idx_fmp_entity_dataset', 'field_mapping_profiles', ['entity_id', 'dataset_type', 'is_active'])

    # 4. datasets
    op.create_table(
        'datasets',
        sa.Column('dataset_id', GUID, primary_key=True),
        sa.Column('entity_id', GUID, sa.ForeignKey('entities.entity_id', ondelete='CASCADE'), nullable=False),
        sa.Column('dataset_type', sa.String(64), nullable=False),
        sa.Column('display_name', sa.String(128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('schema_version', sa.String(16), nullable=False, server_default='1.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_datasets_entity_type', 'datasets', ['entity_id', 'dataset_type'])

    # 5. raw_submissions
    op.create_table(
        'raw_submissions',
        sa.Column('submission_id', GUID, primary_key=True),
        sa.Column('entity_id', GUID, sa.ForeignKey('entities.entity_id', ondelete='CASCADE'), nullable=False),
        sa.Column('dataset_type', sa.String(64), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('mime_type', sa.String(64), nullable=False),
        sa.Column('minio_raw_path', sa.String(512), nullable=False),
        sa.Column('sha256_hash', sa.String(64), nullable=False),
        sa.Column('row_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('valid_row_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('quarantined_row_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ingestion_status', sa.String(32), nullable=False, server_default='PENDING'),
        sa.Column('error_summary', sa.Text(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_submissions_entity_type', 'raw_submissions', ['entity_id', 'dataset_type'])
    op.create_index('idx_submissions_sha256', 'raw_submissions', ['sha256_hash'])
    op.create_index('idx_submissions_status', 'raw_submissions', ['ingestion_status'])

    # 6. quarantined_rows
    op.create_table(
        'quarantined_rows',
        sa.Column('quarantine_id', GUID, primary_key=True),
        sa.Column('submission_id', GUID, sa.ForeignKey('raw_submissions.submission_id', ondelete='CASCADE'), nullable=False),
        sa.Column('entity_id', GUID, sa.ForeignKey('entities.entity_id', ondelete='CASCADE'), nullable=False),
        sa.Column('dataset_type', sa.String(64), nullable=False),
        sa.Column('row_index', sa.Integer(), nullable=False),
        sa.Column('raw_content', JSONType, nullable=False),
        sa.Column('failure_reason', sa.Text(), nullable=False),
        sa.Column('failed_fields', JSONType, nullable=False, server_default='[]'),
        sa.Column('quarantined_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_quarantine_submission', 'quarantined_rows', ['submission_id', 'row_index'])
    op.create_index('idx_quarantine_entity', 'quarantined_rows', ['entity_id', 'quarantined_at'])

    # 7. normalized_events
    op.create_table(
        'normalized_events',
        sa.Column('event_id', GUID, primary_key=True),
        sa.Column('submission_id', GUID, sa.ForeignKey('raw_submissions.submission_id', ondelete='CASCADE'), nullable=False),
        sa.Column('entity_id', GUID, sa.ForeignKey('entities.entity_id', ondelete='CASCADE'), nullable=False),
        sa.Column('dataset_type', sa.String(64), nullable=False),
        sa.Column('standard_event_type', sa.String(64), nullable=False),
        sa.Column('event_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('asset_id', sa.String(128), nullable=True),
        sa.Column('user_id', sa.String(128), nullable=True),
        sa.Column('action', sa.String(128), nullable=True),
        sa.Column('status', sa.String(64), nullable=True),
        sa.Column('severity', sa.String(32), nullable=True),
        sa.Column('source_ip', sa.String(45), nullable=True),
        sa.Column('destination_ip', sa.String(45), nullable=True),
        sa.Column('raw_row_index', sa.Integer(), nullable=False),
        sa.Column('raw_ref_id', sa.String(128), nullable=True),
        sa.Column('normalized_payload', JSONType, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_events_entity_time', 'normalized_events', ['entity_id', 'event_timestamp'])
    op.create_index('idx_events_entity_type_time', 'normalized_events', ['entity_id', 'standard_event_type', 'event_timestamp'])
    op.create_index('idx_events_asset', 'normalized_events', ['entity_id', 'asset_id'])
    op.create_index('idx_events_submission', 'normalized_events', ['submission_id'])

    # 8. execution_gap_findings
    op.create_table(
        'execution_gap_findings',
        sa.Column('finding_id', GUID, primary_key=True),
        sa.Column('entity_id', GUID, sa.ForeignKey('entities.entity_id', ondelete='CASCADE'), nullable=False),
        sa.Column('rule_id', sa.String(64), nullable=False),
        sa.Column('rule_name', sa.String(255), nullable=False),
        sa.Column('rule_category', sa.String(64), nullable=False),
        sa.Column('severity', sa.String(32), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(32), nullable=False, server_default='OPEN'),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=False),
        sa.Column('evidence_record_ids', JSONType, nullable=False),
        sa.Column('raw_evidence_refs', JSONType, nullable=False, server_default='[]'),
        sa.Column('metric_values', JSONType, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_gap_entity_period', 'execution_gap_findings', ['entity_id', 'period_start', 'period_end'])
    op.create_index('idx_gap_rule', 'execution_gap_findings', ['rule_id', 'severity'])

    # 9. negative_space_findings
    op.create_table(
        'negative_space_findings',
        sa.Column('finding_id', GUID, primary_key=True),
        sa.Column('entity_id', GUID, sa.ForeignKey('entities.entity_id', ondelete='CASCADE'), nullable=False),
        sa.Column('check_id', sa.String(64), nullable=False),
        sa.Column('check_name', sa.String(255), nullable=False),
        sa.Column('check_category', sa.String(64), nullable=False),
        sa.Column('severity', sa.String(32), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expected_volume', sa.Float(), nullable=False),
        sa.Column('observed_volume', sa.Float(), nullable=False),
        sa.Column('drop_percentage', sa.Float(), nullable=False),
        sa.Column('entropy_score', sa.Float(), nullable=True),
        sa.Column('rationale', sa.Text(), nullable=False),
        sa.Column('evidence_record_ids', JSONType, nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_neg_entity_period', 'negative_space_findings', ['entity_id', 'period_start', 'period_end'])
    op.create_index('idx_neg_check', 'negative_space_findings', ['check_id'])

    # 10. correlations
    op.create_table(
        'correlations',
        sa.Column('correlation_id', GUID, primary_key=True),
        sa.Column('entity_id', GUID, sa.ForeignKey('entities.entity_id', ondelete='CASCADE'), nullable=False),
        sa.Column('correlation_type', sa.String(64), nullable=False),
        sa.Column('primary_event_id', GUID, sa.ForeignKey('normalized_events.event_id', ondelete='CASCADE'), nullable=False),
        sa.Column('correlated_event_id', GUID, sa.ForeignKey('normalized_events.event_id', ondelete='CASCADE'), nullable=False),
        sa.Column('asset_id', sa.String(128), nullable=True),
        sa.Column('similarity_score', sa.Float(), nullable=False),
        sa.Column('shared_attributes', JSONType, nullable=False, server_default='{}'),
        sa.Column('rationale', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_corr_entity_type', 'correlations', ['entity_id', 'correlation_type'])
    op.create_index('idx_corr_primary', 'correlations', ['primary_event_id'])
    op.create_index('idx_corr_correlated', 'correlations', ['correlated_event_id'])

    # 11. peer_benchmarks
    op.create_table(
        'peer_benchmarks',
        sa.Column('benchmark_id', GUID, primary_key=True),
        sa.Column('sector', sa.String(64), nullable=False),
        sa.Column('size_tier', sa.String(16), nullable=False),
        sa.Column('metric_name', sa.String(128), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('peer_group_size', sa.Integer(), nullable=False),
        sa.Column('mean_val', sa.Float(), nullable=False),
        sa.Column('std_dev', sa.Float(), nullable=False),
        sa.Column('p25', sa.Float(), nullable=False),
        sa.Column('p50', sa.Float(), nullable=False),
        sa.Column('p75', sa.Float(), nullable=False),
        sa.Column('p90', sa.Float(), nullable=False),
        sa.Column('is_low_confidence', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('calculated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('sector', 'size_tier', 'metric_name', 'period_start', 'period_end', name='uq_benchmark_cohort_metric_period'),
    )
    op.create_index('idx_benchmarks_cohort', 'peer_benchmarks', ['sector', 'size_tier', 'metric_name'])

    # 12. risk_scores
    op.create_table(
        'risk_scores',
        sa.Column('score_id', GUID, primary_key=True),
        sa.Column('entity_id', GUID, sa.ForeignKey('entities.entity_id', ondelete='CASCADE'), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('composite_risk_score', sa.Float(), nullable=False),
        sa.Column('execution_gap_score', sa.Float(), nullable=False),
        sa.Column('negative_space_score', sa.Float(), nullable=False),
        sa.Column('peer_deviation_score', sa.Float(), nullable=False),
        sa.Column('weights_applied', JSONType, nullable=False),
        sa.Column('risk_tier', sa.String(32), nullable=False),
        sa.Column('trend_direction', sa.String(16), nullable=False),
        sa.Column('rationale_summary', sa.Text(), nullable=False),
        sa.Column('calculated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_risk_entity_period', 'risk_scores', ['entity_id', 'period_start', 'period_end'])
    op.create_index('idx_risk_composite', 'risk_scores', ['composite_risk_score'])

    # 13. audit_manifests
    op.create_table(
        'audit_manifests',
        sa.Column('manifest_id', GUID, primary_key=True),
        sa.Column('entity_id', GUID, sa.ForeignKey('entities.entity_id', ondelete='CASCADE'), nullable=False),
        sa.Column('submission_id', GUID, sa.ForeignKey('raw_submissions.submission_id', ondelete='SET NULL'), nullable=True),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('manifest_type', sa.String(64), nullable=False),
        sa.Column('root_merkle_sha256', sa.String(64), nullable=False),
        sa.Column('file_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('event_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('finding_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('minio_manifest_path', sa.String(512), nullable=False),
        sa.Column('component_hashes', JSONType, nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_manifest_root_sha', 'audit_manifests', ['root_merkle_sha256'])
    op.create_index('idx_manifest_entity_period', 'audit_manifests', ['entity_id', 'period_start', 'period_end'])


def downgrade() -> None:
    op.drop_table('audit_manifests')
    op.drop_table('risk_scores')
    op.drop_table('peer_benchmarks')
    op.drop_table('correlations')
    op.drop_table('negative_space_findings')
    op.drop_table('execution_gap_findings')
    op.drop_table('normalized_events')
    op.drop_table('quarantined_rows')
    op.drop_table('raw_submissions')
    op.drop_table('datasets')
    op.drop_table('field_mapping_profiles')
    op.drop_table('entities')
    op.drop_table('users')
