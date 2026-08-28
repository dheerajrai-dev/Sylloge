"""Generic declarative logic interpreter for execution gap condition evaluation."""

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from shared.logging import logger
from .models import (
    ConditionOperator,
    JoinRelation,
    LogicalOperator,
    RuleCondition,
    TemporalJoin,
)


class LogicInterpreter:
    """Evaluates declarative AST rule conditions over event records without eval()."""

    @staticmethod
    def parse_datetime_safe(val: Any) -> Any:
        """Converts string timestamp to timezone-aware datetime."""
        if val is None:
            return None
        if isinstance(val, datetime):
            if val.tzinfo is None:
                return val.replace(tzinfo=timezone.utc)
            return val
        if isinstance(val, str):
            val_str = val.strip()
            if val_str.endswith("Z"):
                val_str = val_str[:-1] + "+00:00"
            try:
                dt = datetime.fromisoformat(val_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except (ValueError, TypeError):
                pass
        return val

    @classmethod
    def extract_field_value(cls, record: Any, field_path: str) -> Any:
        """Extracts field value from record using dot notation or payload fallback."""
        if record is None or not field_path:
            return None

        val = None

        # Convert ORM model or Pydantic model to dict if needed
        rec_dict = record
        if hasattr(record, "to_dict") and callable(record.to_dict):
            rec_dict = record.to_dict()
        elif hasattr(record, "__dict__") and not isinstance(record, dict):
            # Read direct attributes
            val = getattr(record, field_path, None)
            if val is None:
                payload = getattr(record, "normalized_payload", None)
                if isinstance(payload, dict) and field_path in payload:
                    val = payload[field_path]

        if val is None and isinstance(rec_dict, dict):
            # Support dot-notation (e.g., 'normalized_payload.delay_hours')
            parts = field_path.split(".")
            current = rec_dict
            for part in parts:
                if isinstance(current, dict):
                    current = current.get(part)
                elif hasattr(current, part):
                    current = getattr(current, part)
                else:
                    current = None
                    break
            if current is not None:
                val = current
            elif "normalized_payload" in rec_dict and isinstance(rec_dict["normalized_payload"], dict):
                val = rec_dict["normalized_payload"].get(field_path)

        # Automatically parse timestamp fields into datetime objects
        timestamp_fields = {
            "event_timestamp", "created_at", "closed_at", "escalated_at",
            "declared_at", "resolved_at", "timestamp", "period_start", "period_end"
        }
        if val is not None and (field_path in timestamp_fields or field_path.endswith("_at") or field_path.endswith("_time") or "timestamp" in field_path):
            val = cls.parse_datetime_safe(val)

        return val

    @classmethod
    def evaluate_condition(cls, condition: Optional[RuleCondition], record: Any) -> bool:
        """Evaluates a single condition or composite logical tree against a record."""
        if condition is None:
            return True

        # Handle composite logical operators (AND, OR, NOT)
        if condition.logical_op == LogicalOperator.AND and condition.conditions:
            return all(cls.evaluate_condition(sub_cond, record) for sub_cond in condition.conditions)

        if condition.logical_op == LogicalOperator.OR and condition.conditions:
            return any(cls.evaluate_condition(sub_cond, record) for sub_cond in condition.conditions)

        if condition.logical_op == LogicalOperator.NOT and condition.conditions:
            return not any(cls.evaluate_condition(sub_cond, record) for sub_cond in condition.conditions)

        # Base atomic condition evaluation
        if not condition.field or condition.operator is None:
            return True

        actual_val = cls.extract_field_value(record, condition.field)
        target_val = condition.value
        op = condition.operator

        return cls._apply_operator(actual_val, op, target_val)

    @classmethod
    def _apply_operator(cls, actual: Any, op: ConditionOperator, target: Any) -> bool:
        """Applies comparison operator with robust type handling."""
        try:
            if op == ConditionOperator.IS_NULL:
                return actual is None or actual == "" or (isinstance(actual, (list, dict)) and len(actual) == 0)

            if op == ConditionOperator.IS_NOT_NULL:
                return actual is not None and actual != "" and not (isinstance(actual, (list, dict)) and len(actual) == 0)

            if actual is None:
                return False

            if op == ConditionOperator.EQ:
                if isinstance(actual, str) and isinstance(target, str):
                    return actual.strip().lower() == target.strip().lower()
                return str(actual) == str(target) if (isinstance(actual, (int, float)) or isinstance(target, (int, float))) else actual == target

            if op == ConditionOperator.NE:
                if isinstance(actual, str) and isinstance(target, str):
                    return actual.strip().lower() != target.strip().lower()
                return actual != target

            if op in (ConditionOperator.GT, ConditionOperator.GTE, ConditionOperator.LT, ConditionOperator.LTE):
                # Try numeric conversion
                try:
                    num_actual = float(actual)
                    num_target = float(target)
                    if op == ConditionOperator.GT:
                        return num_actual > num_target
                    if op == ConditionOperator.GTE:
                        return num_actual >= num_target
                    if op == ConditionOperator.LT:
                        return num_actual < num_target
                    if op == ConditionOperator.LTE:
                        return num_actual <= num_target
                except (ValueError, TypeError):
                    # Fallback to string or datetime comparison
                    if op == ConditionOperator.GT:
                        return actual > target
                    if op == ConditionOperator.GTE:
                        return actual >= target
                    if op == ConditionOperator.LT:
                        return actual < target
                    if op == ConditionOperator.LTE:
                        return actual <= target

            if op == ConditionOperator.IN:
                if isinstance(target, (list, tuple, set)):
                    if isinstance(actual, str):
                        target_normalized = {str(item).strip().lower() for item in target}
                        return actual.strip().lower() in target_normalized
                    return actual in target
                return False

            if op == ConditionOperator.NOT_IN:
                if isinstance(target, (list, tuple, set)):
                    if isinstance(actual, str):
                        target_normalized = {str(item).strip().lower() for item in target}
                        return actual.strip().lower() not in target_normalized
                    return actual not in target
                return True

            if op == ConditionOperator.CONTAINS:
                if isinstance(actual, (str, list, tuple, set)):
                    if isinstance(actual, str) and isinstance(target, str):
                        return target.lower() in actual.lower()
                    return target in actual
                return False

            if op == ConditionOperator.NOT_CONTAINS:
                if isinstance(actual, (str, list, tuple, set)):
                    if isinstance(actual, str) and isinstance(target, str):
                        return target.lower() not in actual.lower()
                    return target not in actual
                return True

            if op == ConditionOperator.STARTS_WITH:
                return str(actual).lower().startswith(str(target).lower())

            if op == ConditionOperator.ENDS_WITH:
                return str(actual).lower().endswith(str(target).lower())

            if op == ConditionOperator.REGEX_MATCH:
                return bool(re.search(str(target), str(actual), re.IGNORECASE))

            if op == ConditionOperator.LENGTH_LT:
                length = len(actual) if isinstance(actual, (str, list, dict)) else 0
                return length < int(target)

            if op == ConditionOperator.LENGTH_GT:
                length = len(actual) if isinstance(actual, (str, list, dict)) else 0
                return length > int(target)

            if op == ConditionOperator.LOWER_IN:
                act_str = str(actual).strip().lower()
                if isinstance(target, (list, tuple, set)):
                    return act_str in {str(t).strip().lower() for t in target}
                return act_str == str(target).strip().lower()

        except Exception as exc:
            logger.debug(f"Condition evaluation error on op {op}: {exc}")
            return False

        return False

    @classmethod
    def evaluate_temporal_join(
        cls,
        join_spec: Optional[TemporalJoin],
        primary_record: Any,
        target_events: List[Any],
    ) -> Tuple[bool, List[Any]]:
        """
        Evaluates temporal join condition between primary record and target dataset events.
        Returns:
            (is_matched: bool, matching_events: List[Any])
        """
        if join_spec is None:
            return True, []

        primary_time = cls.extract_field_value(primary_record, "event_timestamp")
        primary_key_val = cls.extract_field_value(primary_record, join_spec.join_key)
        fallback_key_val = (
            cls.extract_field_value(primary_record, join_spec.join_fallback_key)
            if join_spec.join_fallback_key
            else None
        )

        matched_events: List[Any] = []

        for target in target_events:
            # Check target dataset match
            target_ds = cls.extract_field_value(target, "dataset_type")
            target_evt_type = cls.extract_field_value(target, "standard_event_type")
            if join_spec.target_dataset not in (target_ds, target_evt_type):
                continue

            # Check key matching
            tgt_ref = cls.extract_field_value(target, "raw_ref_id")
            tgt_key_val = cls.extract_field_value(target, join_spec.join_key)
            tgt_fallback = (
                cls.extract_field_value(target, join_spec.join_fallback_key)
                if join_spec.join_fallback_key
                else None
            )

            # Key comparison
            key_matched = False
            if primary_key_val and (primary_key_val in (tgt_ref, tgt_key_val)):
                key_matched = True
            elif fallback_key_val and (fallback_key_val in (tgt_ref, tgt_key_val, tgt_fallback)):
                key_matched = True
            elif primary_key_val and tgt_fallback and primary_key_val == tgt_fallback:
                key_matched = True

            if not key_matched:
                continue

            # Check time delta if specified
            if primary_time and join_spec.max_time_delta_seconds is not None:
                target_time = cls.extract_field_value(target, "event_timestamp")
                if target_time:
                    delta_seconds = abs((target_time - primary_time).total_seconds())
                    if delta_seconds > join_spec.max_time_delta_seconds:
                        continue

            # Check optional filter condition on joined record
            if join_spec.filter_condition:
                if not cls.evaluate_condition(join_spec.filter_condition, target):
                    continue

            matched_events.append(target)

        if join_spec.relation == JoinRelation.EXISTS:
            return len(matched_events) > 0, matched_events
        elif join_spec.relation == JoinRelation.NOT_EXISTS:
            return len(matched_events) == 0, matched_events

        return False, []
