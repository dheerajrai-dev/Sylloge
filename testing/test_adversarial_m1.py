"""Empirical Adversarial Challenge and Stress Test Suite for Milestone 1.

Tests boundary conditions, attack vectors, Merkle tree edge cases, JWT auth security,
Pydantic schema fuzzing, and SQLAlchemy ORM constraint/cascade guarantees.
"""

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import bcrypt
import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shared.auth.jwt import create_access_token, decode_access_token
from shared.auth.security import hash_password, verify_password
from shared.auth.service_auth import (
    get_current_supervisor,
    get_current_user_token,
    verify_internal_service_key,
)
from shared.config import settings
from shared.errors import AuthenticationError, SATSAError
from shared.events.enums import DatasetType, SeverityTier, StandardEventType
from shared.events.standard_event import StandardEvent
from shared.models.audit import AuditManifest
from shared.models.benchmark import PeerBenchmark
from shared.models.correlation import Correlation
from shared.models.dataset import Dataset
from shared.models.entity import Entity
from shared.models.event import NormalizedEvent
from shared.models.finding import ExecutionGapFinding, NegativeSpaceFinding
from shared.models.mapping import FieldMappingProfile
from shared.models.quarantine import QuarantinedRow
from shared.models.risk_score import RiskScore
from shared.models.submission import RawSubmission
from shared.models.user import User
from shared.schemas.auth import LoginRequest, TokenPayload, UserCreate
from shared.schemas.datasets import (
    AlertMetadataSchema,
    AnalystActivitySchema,
    AssetInventorySchema,
    CaseManagementSchema,
    CoverageReportSchema,
    EscalationRecordSchema,
    IncidentReportSchema,
    InvestigationRecordSchema,
)
from shared.storage.merkle import (
    MerkleTree,
    canonical_json_bytes,
    sha256_hash_bytes,
    sha256_hash_json,
    sha256_hash_str,
)


# ==============================================================================
# SECTION 1: MERKLE TREE & CRYPTOGRAPHIC ADVERSARIAL CHALLENGES
# ==============================================================================


@pytest.mark.parametrize("leaf_count", [0, 1, 2, 3, 4, 5, 7, 8, 9, 15, 16, 17, 31, 32, 33, 64, 100, 500])
def test_merkle_tree_scale_and_oddities(leaf_count: int):
    """Stress tests Merkle tree across power-of-two, prime, odd, and large leaf counts."""
    leaves = [sha256_hash_str(f"adversarial_leaf_{i}") for i in range(leaf_count)]
    tree = MerkleTree(leaves)
    root = tree.root_hash

    assert isinstance(root, str)
    assert len(root) == 64
    # Determinism check: rebuild and verify same root
    tree_repeat = MerkleTree(leaves)
    assert tree_repeat.root_hash == root


def test_merkle_tree_case_insensitivity():
    """Verifies that MerkleTree normalizes uppercase/mixed-case SHA-256 leaves."""
    lower_leaves = [sha256_hash_str(f"item_{i}").lower() for i in range(5)]
    upper_leaves = [h.upper() for h in lower_leaves]
    mixed_leaves = [h.upper() if i % 2 == 0 else h.lower() for i, h in enumerate(lower_leaves)]

    tree_lower = MerkleTree(lower_leaves)
    tree_upper = MerkleTree(upper_leaves)
    tree_mixed = MerkleTree(mixed_leaves)

    assert tree_lower.root_hash == tree_upper.root_hash
    assert tree_lower.root_hash == tree_mixed.root_hash


def test_merkle_tree_empty_and_single_leaf_invariants():
    """Verifies empty tree and single leaf tree invariants."""
    empty_tree = MerkleTree([])
    assert empty_tree.root_hash == hashlib.sha256(b"").hexdigest()

    single_leaf = sha256_hash_str("sole_node")
    single_tree = MerkleTree([single_leaf])
    assert single_tree.root_hash == single_leaf


def test_merkle_tree_record_fuzzing_complex_types():
    """Fuzzes MerkleTree.from_records with non-trivial Python objects and edge cases."""
    now = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
    uid = uuid.UUID("12345678-1234-5678-1234-567812345678")

    records = [
        {"nested": {"level2": {"level3": [1, 2, 3]}}, "flag": True},
        {"uuid": uid, "timestamp": now, "decimal": str(Decimal("123.45600"))},
        {"unicode": "CYBER_SEC_🔒_🛡️_Аналитика_网络安全", "null_byte": "foo\x00bar"},
        {"empty_list": [], "empty_dict": {}, "none_val": None},
        {"large_text": "A" * 10000},
    ]

    tree = MerkleTree.from_records(records)
    root = tree.root_hash
    assert len(root) == 64

    # Reordering keys inside a record must not alter the canonical hash
    reordered_records = [
        {"flag": True, "nested": {"level2": {"level3": [1, 2, 3]}}},
        {"decimal": str(Decimal("123.45600")), "timestamp": now, "uuid": uid},
        {"null_byte": "foo\x00bar", "unicode": "CYBER_SEC_🔒_🛡️_Аналитика_网络安全"},
        {"none_val": None, "empty_dict": {}, "empty_list": []},
        {"large_text": "A" * 10000},
    ]
    tree_reordered = MerkleTree.from_records(reordered_records)
    assert tree.root_hash == tree_reordered.root_hash


def test_composite_manifest_root_tamper_sensitivity():
    """Verifies that changing any bit in any component hash alters the composite root."""
    raw = "a" * 64
    quarantine = "b" * 64
    normalized = "c" * 64
    findings = "d" * 64

    original_root = MerkleTree.compute_composite_manifest_root(raw, quarantine, normalized, findings)

    # 1. Flip one character in raw
    tampered_raw_root = MerkleTree.compute_composite_manifest_root("e" + raw[1:], quarantine, normalized, findings)
    assert tampered_raw_root != original_root

    # 2. Flip one character in quarantine
    tampered_q_root = MerkleTree.compute_composite_manifest_root(raw, "e" + quarantine[1:], normalized, findings)
    assert tampered_q_root != original_root

    # 3. Flip one character in normalized
    tampered_norm_root = MerkleTree.compute_composite_manifest_root(raw, quarantine, "e" + normalized[1:], findings)
    assert tampered_norm_root != original_root

    # 4. Flip one character in findings
    tampered_f_root = MerkleTree.compute_composite_manifest_root(raw, quarantine, normalized, "e" + findings[1:])
    assert tampered_f_root != original_root


# ==============================================================================
# SECTION 2: ADVERSARIAL JWT & AUTH SECURITY ATTACK SCENARIOS
# ==============================================================================


def test_jwt_none_algorithm_exploit():
    """Adversarial challenge: Attempt authentication using 'none' algorithm token."""
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(uuid.uuid4()),
        "username": "attacker",
        "role": "supervisor",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    # Forge token without signature using algorithm none
    forged_none_token = jwt.encode(claims, key="", algorithm="none")

    with pytest.raises(AuthenticationError):
        decode_access_token(forged_none_token)


def test_jwt_algorithm_confusion_attacks():
    """Adversarial challenge: Tokens signed with unexpected symmetric/asymmetric algorithms."""
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(uuid.uuid4()),
        "username": "attacker",
        "role": "supervisor",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }

    # Token signed with HS512 instead of HS256
    hs512_token = jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm="HS512")
    with pytest.raises(AuthenticationError):
        decode_access_token(hs512_token)


def test_jwt_signature_stripping():
    """Adversarial challenge: Strip cryptographic signature from valid token."""
    valid_token = create_access_token(subject=str(uuid.uuid4()), username="supervisor_valid")
    parts = valid_token.split(".")
    stripped_token = f"{parts[0]}.{parts[1]}."

    with pytest.raises(AuthenticationError):
        decode_access_token(stripped_token)


def test_jwt_payload_tampering():
    """Adversarial challenge: Tamper with payload claims without resigning."""
    user_id = str(uuid.uuid4())
    token = create_access_token(subject=user_id, username="analyst_user", role="viewer")
    parts = token.split(".")

    # Decode payload part, tamper role to supervisor, re-encode without key
    import base64
    payload_raw = parts[1] + "=="  # pad
    payload_data = json.loads(base64.urlsafe_b64decode(payload_raw.encode("utf-8")))
    payload_data["role"] = "supervisor"
    tampered_payload_b64 = base64.urlsafe_b64encode(json.dumps(payload_data).encode("utf-8")).decode("utf-8").rstrip("=")

    tampered_token = f"{parts[0]}.{tampered_payload_b64}.{parts[2]}"
    with pytest.raises(AuthenticationError):
        decode_access_token(tampered_token)


@pytest.mark.parametrize("missing_claim", ["sub", "username", "role", "exp", "iat"])
def test_jwt_missing_required_claims(missing_claim: str):
    """Adversarial challenge: Tokens missing mandatory claims."""
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(uuid.uuid4()),
        "username": "supervisor_test",
        "role": "supervisor",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    del claims[missing_claim]

    token = jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm="HS256")
    with pytest.raises(AuthenticationError):
        decode_access_token(token)


def test_jwt_expiration_boundary_conditions():
    """Verifies strict expiration enforcement with clock drift leeway."""
    user_id = str(uuid.uuid4())

    # 1. Expired 59s ago with 60s leeway -> MUST PASS
    token_within_leeway = create_access_token(
        subject=user_id,
        username="supervisor_leeway",
        expires_delta=timedelta(seconds=-59),
    )
    payload = decode_access_token(token_within_leeway, leeway=60)
    assert payload.username == "supervisor_leeway"

    # 2. Expired 61s ago with 60s leeway -> MUST FAIL
    token_past_leeway = create_access_token(
        subject=user_id,
        username="supervisor_expired",
        expires_delta=timedelta(seconds=-61),
    )
    with pytest.raises(AuthenticationError):
        decode_access_token(token_past_leeway, leeway=60)


@pytest.mark.parametrize("invalid_role", [
    "SUPERVISOR",      # uppercase
    "supervisor ",     # trailing whitespace
    " supervisor",     # leading whitespace
    "admin",           # non-supervisor privilege
    "root",
    "auditor",
    "",                # empty
    "null",
])
@pytest.mark.asyncio
async def test_role_escalation_variations(invalid_role: str):
    """Adversarial challenge: Attempt supervisor privilege escalation with non-exact roles."""
    payload = TokenPayload(
        sub=str(uuid.uuid4()),
        username="attacker",
        role=invalid_role,
        exp=int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        iat=int(datetime.now(timezone.utc).timestamp()),
    )
    with pytest.raises(HTTPException) as exc_info:
        await get_current_supervisor(payload)
    assert exc_info.value.status_code == 403


@pytest.mark.parametrize("bad_key", [
    None,
    "",
    " ",
    "test_internal_service_key_2026 ",
    "Test_Internal_Service_Key_2026",
    "test_internal_service_key_2026\x00injected",
    "wrong_key_12345",
])
@pytest.mark.asyncio
async def test_internal_service_key_attacks(bad_key: str):
    """Adversarial challenge: Inter-service authentication with malformed/forged keys."""
    with pytest.raises(HTTPException) as exc_info:
        await verify_internal_service_key(bad_key)
    assert exc_info.value.status_code == 403


def test_password_hashing_security_and_edge_cases():
    """Stress tests password hashing with extreme characters and invalid hashes."""
    # 1. Unicode & special symbols
    unicode_pass = "P@sswørd🔒2026_漢字_🛡️!#$%"
    h = hash_password(unicode_pass)
    assert verify_password(unicode_pass, h) is True
    assert verify_password("WrongUnicode", h) is False

    # 2. Maximum standard length password (72 bytes for bcrypt)
    pass_72 = "A" * 72
    h_72 = hash_password(pass_72)
    assert verify_password(pass_72, h_72) is True

    # 3. Passwords > 72 bytes: bcrypt raises ValueError in bcrypt 4.x/5.x
    # verify_password handles it gracefully and returns False
    assert verify_password("A" * 200, h_72) is False

    # 4. Malformed hash strings
    assert verify_password("secret", "not_a_bcrypt_hash") is False
    assert verify_password("secret", "") is False
    assert verify_password("secret", "$2b$12$tooshort") is False


# ==============================================================================
# SECTION 3: ADVERSARIAL PYDANTIC SCHEMA FUZZING & VALIDATION
# ==============================================================================


def test_alert_metadata_fuzzing():
    """Fuzzes AlertMetadataSchema with valid extra fields and malformed types."""
    now = datetime.now(timezone.utc)

    # 1. Extra unexpected fields should be preserved (extra="allow")
    alert_with_extras = AlertMetadataSchema(
        alert_id="ALT-FUZZ-01",
        timestamp=now,
        rule_name="FUZZ_RULE",
        severity="MEDIUM",
        custom_header_x="val_1",
        telemetry_extra={"confidence": 0.99, "sensor_ver": "2.4.1"},
    )
    assert alert_with_extras.alert_id == "ALT-FUZZ-01"
    assert alert_with_extras.custom_header_x == "val_1"

    # 2. Missing mandatory field (alert_id)
    with pytest.raises(ValidationError):
        AlertMetadataSchema(timestamp=now, rule_name="R1", severity="HIGH")

    # 3. Malformed timestamp
    with pytest.raises(ValidationError):
        AlertMetadataSchema(alert_id="ALT-1", timestamp="invalid-datetime-str", rule_name="R1", severity="HIGH")


def test_all_dataset_schemas_fuzz_mandatory_failures():
    """Verifies all 8 dataset schemas strictly reject missing mandatory fields."""
    now = datetime.now(timezone.utc)

    # CaseManagement missing case_id
    with pytest.raises(ValidationError):
        CaseManagementSchema(created_at=now, status="OPEN", priority="P1", title="Title")

    # InvestigationRecord missing investigation_id
    with pytest.raises(ValidationError):
        InvestigationRecordSchema(case_id="C1", analyst_id="A1", timestamp=now, investigation_action="ACT", notes="N")

    # EscalationRecord missing escalated_from
    with pytest.raises(ValidationError):
        EscalationRecordSchema(escalation_id="E1", escalated_to="L2", timestamp=now, escalation_reason="R")

    # AssetInventory missing hostname
    with pytest.raises(ValidationError):
        AssetInventorySchema(asset_id="AST-1", asset_type="SRV", criticality="TIER_1")

    # IncidentReport missing declared_at
    with pytest.raises(ValidationError):
        IncidentReportSchema(incident_id="INC-1", title="Breach", severity="HIGH")

    # CoverageReport missing reported_at
    with pytest.raises(ValidationError):
        CoverageReportSchema(
            coverage_id="COV-1", tool_name="EDR", source_type="LOG",
            total_assets_monitored=10, active_sensors=10, coverage_percentage=100.0,
        )

    # AnalystActivity missing timestamp
    with pytest.raises(ValidationError):
        AnalystActivitySchema(activity_id="ACT-1", analyst_id="A1", activity_type="SEARCH")


@pytest.mark.parametrize("bad_username, bad_password", [
    ("a", "validpass123"),           # username too short (< 3)
    ("ab", "validpass123"),          # username too short (< 3)
    ("a" * 65, "validpass123"),      # username too long (> 64)
    ("validuser", "12345"),          # password too short (< 6)
    ("validuser", "p" * 129),        # password too long (> 128)
    ("validuser", ""),               # empty password
])
def test_login_request_boundary_validation(bad_username: str, bad_password: str):
    """Adversarial challenge: LoginRequest field length validation."""
    with pytest.raises(ValidationError):
        LoginRequest(username=bad_username, password=bad_password)


def test_login_request_valid_boundaries():
    """Verifies valid boundary values for LoginRequest."""
    req_min = LoginRequest(username="usr", password="p" * 6)
    assert req_min.username == "usr"

    req_max = LoginRequest(username="u" * 64, password="p" * 128)
    assert req_max.username == "u" * 64


def test_standard_event_invalid_enums():
    """Adversarial challenge: Invalid enum values in StandardEvent."""
    now = datetime.now(timezone.utc)
    uid = uuid.uuid4()

    # Invalid dataset_type
    with pytest.raises(ValidationError):
        StandardEvent(
            event_id=uid,
            submission_id=uid,
            entity_id=uid,
            dataset_type="INVALID_DATASET_TYPE",
            standard_event_type=StandardEventType.ALERT,
            event_timestamp=now,
            severity=SeverityTier.HIGH,
            raw_row_index=0,
        )

    # Invalid severity
    with pytest.raises(ValidationError):
        StandardEvent(
            event_id=uid,
            submission_id=uid,
            entity_id=uid,
            dataset_type=DatasetType.ALERT_METADATA,
            standard_event_type=StandardEventType.ALERT,
            event_timestamp=now,
            severity="SUPER_MEGA_CRITICAL",
            raw_row_index=0,
        )


# ==============================================================================
# SECTION 4: SQLALCHEMY ORM MODELS, CONSTRAINTS & CASCADE STRESS TESTS
# ==============================================================================


def test_entity_cascade_delete_all_child_tables(sync_db: Session):
    """Adversarial stress test: Verifies cascading deletion of Entity deletes all 10 child tables."""
    now = datetime.now(timezone.utc)

    # 1. Create root entity
    entity = Entity(
        entity_code="TEST_CASCADE_CORP",
        name="Cascade Test Corporation",
        sector="Financial",
        size_tier="Tier-1",
        contact_email="soc@cascade.corp",
        is_active=True,
    )
    sync_db.add(entity)
    sync_db.commit()
    ent_id = entity.entity_id

    # 2. Add child records across all related tables
    dataset = Dataset(entity_id=ent_id, dataset_type="alert_metadata", display_name="Alerts")
    sub = RawSubmission(
        entity_id=ent_id, dataset_type="alert_metadata", file_name="f.csv",
        file_size_bytes=100, mime_type="text/csv", minio_raw_path="p", sha256_hash="h1"
    )
    profile = FieldMappingProfile(
        entity_id=ent_id, dataset_type="alert_metadata", version=1,
        mapping_rules={"a": "b"}, is_active=True
    )
    sync_db.add_all([dataset, sub, profile])
    sync_db.commit()

    q_row = QuarantinedRow(
        submission_id=sub.submission_id, entity_id=ent_id, dataset_type="alert_metadata",
        row_index=1, raw_content={"bad": "row"}, failure_reason="Test"
    )
    norm_event1 = NormalizedEvent(
        submission_id=sub.submission_id, entity_id=ent_id, dataset_type="alert_metadata",
        standard_event_type="ALERT", event_timestamp=now, raw_row_index=0
    )
    norm_event2 = NormalizedEvent(
        submission_id=sub.submission_id, entity_id=ent_id, dataset_type="alert_metadata",
        standard_event_type="ALERT", event_timestamp=now, raw_row_index=1
    )
    sync_db.add_all([q_row, norm_event1, norm_event2])
    sync_db.commit()

    gap_finding = ExecutionGapFinding(
        entity_id=ent_id, rule_id="GAP_01", rule_name="Test Gap",
        rule_category="TRIAGE", severity="HIGH", period_start=now, period_end=now,
        description="d", rationale="r"
    )
    neg_finding = NegativeSpaceFinding(
        entity_id=ent_id, check_id="NEG_01", check_name="Test Neg",
        check_category="SILENCE", severity="MEDIUM", period_start=now, period_end=now,
        expected_volume=10.0, observed_volume=0.0, drop_percentage=100.0,
        entropy_score=0.0, rationale="r"
    )
    corr = Correlation(
        entity_id=ent_id, correlation_type="REPEAT",
        primary_event_id=norm_event1.event_id, correlated_event_id=norm_event2.event_id,
        similarity_score=1.0, rationale="r"
    )
    risk = RiskScore(
        entity_id=ent_id, period_start=now, period_end=now,
        composite_risk_score=75.0, execution_gap_score=80.0,
        negative_space_score=70.0, peer_deviation_score=60.0,
        weights_applied={"a": 1.0}, risk_tier="HIGH", trend_direction="UP",
        rationale_summary="r"
    )
    manifest = AuditManifest(
        entity_id=ent_id, period_start=now, period_end=now,
        manifest_type="PERIODIC", root_merkle_sha256="m_root",
        file_count=1, event_count=2, finding_count=2,
        minio_manifest_path="m_path", component_hashes={"h": "v"}
    )
    sync_db.add_all([gap_finding, neg_finding, corr, risk, manifest])
    sync_db.commit()

    # 3. Cascade delete entity
    sync_db.delete(entity)
    sync_db.commit()

    # 4. Verify all child tables are cleared
    assert sync_db.query(Dataset).filter_by(entity_id=ent_id).count() == 0
    assert sync_db.query(RawSubmission).filter_by(entity_id=ent_id).count() == 0
    assert sync_db.query(FieldMappingProfile).filter_by(entity_id=ent_id).count() == 0
    assert sync_db.query(QuarantinedRow).filter_by(entity_id=ent_id).count() == 0
    assert sync_db.query(NormalizedEvent).filter_by(entity_id=ent_id).count() == 0
    assert sync_db.query(ExecutionGapFinding).filter_by(entity_id=ent_id).count() == 0
    assert sync_db.query(NegativeSpaceFinding).filter_by(entity_id=ent_id).count() == 0
    assert sync_db.query(Correlation).filter_by(entity_id=ent_id).count() == 0
    assert sync_db.query(RiskScore).filter_by(entity_id=ent_id).count() == 0
    assert sync_db.query(AuditManifest).filter_by(entity_id=ent_id).count() == 0


def test_unique_constraints_enforcement(sync_db: Session, sample_entity: Entity):
    """Verifies database uniqueness constraints across models."""
    now = datetime.now(timezone.utc)

    # 1. Unique constraint: Entity.entity_code
    duplicate_entity = Entity(
        entity_code=sample_entity.entity_code,
        name="Duplicate Bank",
        sector="Banking",
        size_tier="Tier-1",
    )
    sync_db.add(duplicate_entity)
    with pytest.raises(IntegrityError):
        sync_db.commit()
    sync_db.rollback()

    # 2. Unique constraint: User.username
    u1 = User(username="unique_user_01", password_hash="hash", full_name="User 1", role="supervisor")
    sync_db.add(u1)
    sync_db.commit()

    u2 = User(username="unique_user_01", password_hash="hash2", full_name="User 2", role="supervisor")
    sync_db.add(u2)
    with pytest.raises(IntegrityError):
        sync_db.commit()
    sync_db.rollback()

    # 3. Unique constraint: FieldMappingProfile(entity_id, dataset_type, version)
    fmp1 = FieldMappingProfile(
        entity_id=sample_entity.entity_id,
        dataset_type="case_management",
        version=1,
        mapping_rules={"k": "v"},
        is_active=True,
    )
    sync_db.add(fmp1)
    sync_db.commit()

    fmp2 = FieldMappingProfile(
        entity_id=sample_entity.entity_id,
        dataset_type="case_management",
        version=1,
        mapping_rules={"k2": "v2"},
        is_active=True,
    )
    sync_db.add(fmp2)
    with pytest.raises(IntegrityError):
        sync_db.commit()
    sync_db.rollback()

    # 4. Unique constraint: PeerBenchmark(sector, size_tier, metric_name, period_start, period_end)
    pb1 = PeerBenchmark(
        sector="Banking",
        size_tier="Tier-1",
        metric_name="mttd",
        period_start=now,
        period_end=now,
        peer_group_size=5,
        mean_val=1.0,
        std_dev=0.1,
        p25=0.5,
        p50=1.0,
        p75=1.5,
        p90=2.0,
    )
    sync_db.add(pb1)
    sync_db.commit()

    pb2 = PeerBenchmark(
        sector="Banking",
        size_tier="Tier-1",
        metric_name="mttd",
        period_start=now,
        period_end=now,
        peer_group_size=5,
        mean_val=2.0,
        std_dev=0.2,
        p25=1.0,
        p50=2.0,
        p75=2.5,
        p90=3.0,
    )
    sync_db.add(pb2)
    with pytest.raises(IntegrityError):
        sync_db.commit()
    sync_db.rollback()


def test_null_constraint_enforcement(sync_db: Session):
    """Verifies non-nullable column constraints raise IntegrityError on NULL."""
    # Attempt inserting User without username
    user_null_name = User(password_hash="hash", full_name="No Username", role="supervisor")
    sync_db.add(user_null_name)
    with pytest.raises(IntegrityError):
        sync_db.commit()
    sync_db.rollback()

    # Attempt inserting RawSubmission without minio_raw_path
    sub_null_path = RawSubmission(
        entity_id=uuid.uuid4(),
        dataset_type="alert_metadata",
        file_name="test.csv",
        file_size_bytes=100,
        mime_type="text/csv",
        sha256_hash="dummyhash",
        minio_raw_path=None,  # Not nullable
    )
    sync_db.add(sub_null_path)
    with pytest.raises(IntegrityError):
        sync_db.commit()
    sync_db.rollback()


def test_large_and_complex_json_in_models(sync_db: Session, sample_entity: Entity):
    """Verifies that JSONType columns handle deep nesting, unicode, and large structures."""
    sub = RawSubmission(
        entity_id=sample_entity.entity_id,
        dataset_type="alert_metadata",
        file_name="f.csv",
        file_size_bytes=100,
        mime_type="text/csv",
        minio_raw_path="p",
        sha256_hash="h1",
    )
    sync_db.add(sub)
    sync_db.commit()

    complex_payload = {
        "nested_dict": {"k1": {"k2": {"k3": ["item1", "item2", True, False, None]}}},
        "unicode_str": "SIH 2026 🔒 🛡️ 🚀 Привет мир! 日本語",
        "large_array": list(range(1000)),
        "float_values": [3.14159, 2.71828, 0.0000001],
    }

    q_row = QuarantinedRow(
        submission_id=sub.submission_id,
        entity_id=sample_entity.entity_id,
        dataset_type="alert_metadata",
        row_index=999,
        raw_content=complex_payload,
        failure_reason="Adversarial JSON stress test",
        failed_fields=["field_1", "field_2"],
    )
    sync_db.add(q_row)
    sync_db.commit()

    queried = sync_db.query(QuarantinedRow).filter_by(quarantine_id=q_row.quarantine_id).first()
    assert queried is not None
    assert queried.raw_content["unicode_str"] == complex_payload["unicode_str"]
    assert len(queried.raw_content["large_array"]) == 1000
    assert queried.raw_content["nested_dict"]["k1"]["k2"]["k3"][0] == "item1"
