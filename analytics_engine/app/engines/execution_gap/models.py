"""Execution gap rule and condition data models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import uuid
from pydantic import BaseModel, Field


class ConditionOperator(str, Enum):
    """Operators supported by the generic logic interpreter."""
    EQ = "EQ"
    NE = "NE"
    GT = "GT"
    GTE = "GTE"
    LT = "LT"
    LTE = "LTE"
    IN = "IN"
    NOT_IN = "NOT_IN"
    CONTAINS = "CONTAINS"
    NOT_CONTAINS = "NOT_CONTAINS"
    STARTS_WITH = "STARTS_WITH"
    ENDS_WITH = "ENDS_WITH"
    REGEX_MATCH = "REGEX_MATCH"
    IS_NULL = "IS_NULL"
    IS_NOT_NULL = "IS_NOT_NULL"
    LENGTH_LT = "LENGTH_LT"
    LENGTH_GT = "LENGTH_GT"
    LOWER_IN = "LOWER_IN"


class LogicalOperator(str, Enum):
    """Logical grouping operators."""
    AND = "AND"
    OR = "OR"
    NOT = "NOT"


class JoinRelation(str, Enum):
    """Temporal join relational conditions."""
    EXISTS = "EXISTS"
    NOT_EXISTS = "NOT_EXISTS"


class RuleCondition(BaseModel):
    """Declarative AST rule condition or condition branch."""
    field: Optional[str] = None
    operator: Optional[ConditionOperator] = None
    value: Optional[Any] = None
    logical_op: Optional[LogicalOperator] = None
    conditions: Optional[List["RuleCondition"]] = None


class TemporalJoin(BaseModel):
    """Temporal join specification between event streams."""
    target_dataset: str
    join_key: str = "raw_ref_id"
    join_fallback_key: Optional[str] = None
    relation: JoinRelation = JoinRelation.NOT_EXISTS
    max_time_delta_seconds: Optional[int] = None
    min_time_delta_seconds: Optional[int] = None
    filter_condition: Optional[RuleCondition] = None


class RuleDefinition(BaseModel):
    """Declarative Execution Gap Rule specification."""
    rule_code: str
    name: str
    category: str = "COMPLIANCE_GAP"
    target_dataset: str
    filter_condition: Optional[RuleCondition] = None
    temporal_join: Optional[TemporalJoin] = None
    severity_base: int = 70
    severity_multiplier_field: Optional[str] = None
    severity_multiplier_weight: float = 0.0
    max_severity: int = 100
    confidence: float = 0.95
    description_template: str
    rationale_template: str
    recommendation: Optional[str] = None
    is_active: bool = True
    custom_params: Dict[str, Any] = Field(default_factory=dict)


class ExecutionGapFindingDraft(BaseModel):
    """Evaluated execution gap finding draft ready for persistence."""
    finding_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    entity_id: uuid.UUID
    rule_id: str
    rule_name: str
    rule_category: str
    severity: str
    severity_score: int
    confidence: float
    period_start: datetime
    period_end: datetime
    description: str
    rationale: str
    evidence_record_ids: List[str]
    raw_evidence_refs: List[Any] = Field(default_factory=list)
    raw_row_indices: List[int] = Field(default_factory=list)
    metric_values: Dict[str, Any] = Field(default_factory=dict)
    recommendation: Optional[str] = None
