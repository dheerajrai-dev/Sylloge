"""Milestone 2 Top-Level Integration & Pipeline Verification Tests."""

import io
import json
import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from shared.events.enums import DatasetType, SubmissionStatus, StandardEventType
from shared.models.entity import Entity
from shared.models.event import NormalizedEvent
from shared.models.mapping import FieldMappingProfile
from shared.models.quarantine import QuarantinedRow
from shared.models.submission import RawSubmission

import sys
import os
dp_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_processing")
if dp_root not in sys.path:
    sys.path.insert(0, dp_root)

from data_processing.parsers import get_parser_for_dataset, CSVParser, JSONParser
from data_processing.quarantine.validator import RowValidator
from data_processing.quarantine.manager import QuarantineManager
from data_processing.mapping.engine import FieldMappingEngine
from data_processing.mapping.normalizer import CanonicalNormalizer
from data_processing.pipeline.ingestion_service import IngestionPipelineService


def test_e2e_all_8_datasets_sync_ingestion(sync_db: Session, sample_entity: Entity):
    """Verifies synchronous ingestion across all 8 dataset types."""
    datasets_data = {
        DatasetType.ALERT_METADATA: (
            "alert_id,timestamp,severity,rule_name,source_ip,destination_ip,asset_id\n"
            "ALT-01,2026-08-25T10:00:00Z,CRITICAL,BruteForce,1.1.1.1,2.2.2.2,SRV-01\n"
            "ALT-02,2026-08-25T10:05:00Z,HIGH,PortScan,1.1.1.2,2.2.2.2,SRV-01\n"
        ),
        DatasetType.CASE_MANAGEMENT: (
            "case_id,created_at,status,priority,title,assigned_analyst\n"
            "CASE-01,2026-08-25T10:10:00Z,OPEN,P1_CRITICAL,Investigate BruteForce,AN-1\n"
        ),
        DatasetType.INVESTIGATION_RECORDS: (
            "investigation_id,case_id,analyst_id,timestamp,action_taken,notes\n"
            "INV-01,CASE-01,AN-1,2026-08-25T10:30:00Z,Analysis,Confirmed brute force attempt from external IP\n"
        ),
        DatasetType.ESCALATION_RECORDS: (
            "escalation_id,case_id,escalated_at,escalated_by,escalated_to,escalation_reason\n"
            "ESC-01,CASE-01,2026-08-25T10:45:00Z,AN-1,TIER_2_SOC,Escalating for IP blocking\n"
        ),
        DatasetType.ASSET_INVENTORY: (
            "asset_id,hostname,ip_address,asset_type,criticality_tier,owner\n"
            "SRV-01,srv-app-prod,2.2.2.2,SERVER,CROWN_JEWEL,DevOps\n"
        ),
        DatasetType.INCIDENT_REPORTS: (
            "incident_id,declared_at,severity,root_cause,attack_vector\n"
            "INC-01,2026-08-25T11:00:00Z,CRITICAL,Exposed SSH,CREDENTIAL_STUFFING\n"
        ),
        DatasetType.COVERAGE_REPORTS: (
            "coverage_id,reported_at,reporting_period_start,tool_name,uptime_pct,event_count\n"
            "COV-01,2026-08-25T00:00:00Z,2026-08-01,EDR,99.9,1500000\n"
        ),
        DatasetType.ANALYST_ACTIVITY: (
            "activity_id,analyst_id,timestamp,activity_type,console_session_id\n"
            "ACT-01,AN-1,2026-08-25T10:00:00Z,LOGIN,SESS-01\n"
        ),
    }

    for ds_type, csv_content in datasets_data.items():
        sub_id = uuid.uuid4()
        sub = RawSubmission(
            submission_id=sub_id,
            entity_id=sample_entity.entity_id,
            dataset_type=ds_type.value,
            file_name=f"{ds_type.value}.csv",
            file_size_bytes=len(csv_content),
            mime_type="text/csv",
            minio_raw_path=f"raw-submissions/{sub_id}.csv",
            sha256_hash="dummy_hash",
            ingestion_status="PENDING",
        )
        sync_db.add(sub)
        sync_db.commit()

        result = IngestionPipelineService.process_sync(
            db=sync_db,
            submission_id=sub_id,
            entity_id=sample_entity.entity_id,
            dataset_type=ds_type,
            raw_content=csv_content,
        )

        assert result.status == SubmissionStatus.NORMALIZED
        assert result.valid_rows >= 1
        assert result.quarantined_rows == 0

        # Check DB records
        events = sync_db.query(NormalizedEvent).filter(NormalizedEvent.submission_id == sub_id).all()
        assert len(events) == result.valid_rows


@pytest.mark.asyncio
async def test_e2e_async_quarantine_and_normalization_adversarial(async_db: AsyncSession):
    """Verifies that an adversarial dataset with corrupted lines, missing fields, and bad types quarantines properly."""
    entity = Entity(
        entity_id=uuid.uuid4(),
        entity_code="TEST_SEC",
        name="Test Security Sector",
        sector="Government",
        size_tier="Tier-2",
        is_active=True,
    )
    async_db.add(entity)
    await async_db.commit()

    sub_id = uuid.uuid4()
    sub = RawSubmission(
        submission_id=sub_id,
        entity_id=entity.entity_id,
        dataset_type="alert_metadata",
        file_name="adversarial_alerts.csv",
        file_size_bytes=2048,
        mime_type="text/csv",
        minio_raw_path="raw-submissions/adv.csv",
        sha256_hash="adv_hash",
        ingestion_status="PENDING",
    )
    async_db.add(sub)
    await async_db.commit()

    # Adversarial payload:
    # Row 1: Valid
    # Row 2: Missing timestamp
    # Row 3: Missing alert_id
    # Row 4: Unparseable date
    # Row 5: Valid
    # Row 6: Duplicate alert_id (same as Row 5)
    adv_csv = (
        "alert_id,timestamp,severity,rule_name\n"
        "ADV-1,2026-08-25T10:00:00Z,HIGH,Rule1\n"
        "ADV-2,,HIGH,Rule2\n"
        ",2026-08-25T10:02:00Z,HIGH,Rule3\n"
        "ADV-4,INVALID_TIMESTAMP_FORMAT_HERE,HIGH,Rule4\n"
        "ADV-5,2026-08-25T10:04:00Z,CRITICAL,Rule5\n"
        "ADV-5,2026-08-25T10:05:00Z,CRITICAL,Rule5Dupe\n"
    )

    result = await IngestionPipelineService.process_async(
        db=async_db,
        submission_id=sub_id,
        entity_id=entity.entity_id,
        dataset_type=DatasetType.ALERT_METADATA,
        raw_content=adv_csv,
    )

    assert result.status == SubmissionStatus.PARTIAL_SUCCESS
    assert result.total_rows == 6
    assert result.valid_rows == 2
    assert result.quarantined_rows == 4

    # Verify quarantined rows in DB
    q_stmt = select(QuarantinedRow).where(QuarantinedRow.submission_id == sub_id)
    q_records = (await async_db.execute(q_stmt)).scalars().all()
    assert len(q_records) == 4

    # Verify valid events in DB
    e_stmt = select(NormalizedEvent).where(NormalizedEvent.submission_id == sub_id)
    e_records = (await async_db.execute(e_stmt)).scalars().all()
    assert len(e_records) == 2
    ref_ids = {e.raw_ref_id for e in e_records}
    assert ref_ids == {"ADV-1", "ADV-5"}
