"""Rules management endpoints for analytics engine."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from shared.auth.service_auth import verify_internal_service_key
from ..engines.execution_gap.models import RuleDefinition
from ..engines.execution_gap.registry import ExecutionGapRuleRegistry
from ..engines.negative_space.models import CheckDefinition
from ..engines.negative_space.registry import NegativeSpaceCheckRegistry
from ..schemas.requests import RuleListResponse

router = APIRouter(prefix="/api/v1/analytics/rules", tags=["Rules Management"])

# Global in-process registries
eg_registry = ExecutionGapRuleRegistry()
ns_registry = NegativeSpaceCheckRegistry()


@router.get("", response_model=RuleListResponse)
async def list_all_rules(
    active_only: bool = Query(False, description="Filter only active rules"),
):
    """Lists all registered Execution Gap rules and Negative Space absence checks."""
    return RuleListResponse(
        execution_gap_rules=eg_registry.list_rules(active_only=active_only),
        negative_space_checks=ns_registry.list_checks(active_only=active_only),
    )


@router.post("/execution-gap", response_model=RuleDefinition, status_code=status.HTTP_201_CREATED)
async def register_execution_gap_rule(
    rule: RuleDefinition,
    _key: str = Depends(verify_internal_service_key),
):
    """Registers or updates an Execution Gap declarative rule."""
    eg_registry.register_rule(rule)
    return rule


@router.post("/negative-space", response_model=CheckDefinition, status_code=status.HTTP_201_CREATED)
async def register_negative_space_check(
    check: CheckDefinition,
    _key: str = Depends(verify_internal_service_key),
):
    """Registers or updates a Negative Space check."""
    ns_registry.register_check(check)
    return check


@router.patch("/{rule_code}/status")
async def toggle_rule_status(
    rule_code: str,
    is_active: bool = Body(..., embed=True),
    _key: str = Depends(verify_internal_service_key),
):
    """Enables or disables an execution gap rule or negative space check."""
    if eg_registry.set_rule_status(rule_code, is_active):
        return {"status": "success", "rule_code": rule_code, "is_active": is_active}
    if ns_registry.set_check_status(rule_code, is_active):
        return {"status": "success", "rule_code": rule_code, "is_active": is_active}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Rule or Check with code '{rule_code}' not found.",
    )
