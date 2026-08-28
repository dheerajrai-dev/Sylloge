"""Rule registry for execution gap engine."""

from typing import Dict, List, Optional
from shared.logging import logger
from .default_rules import get_default_execution_gap_rules
from .models import RuleDefinition


class ExecutionGapRuleRegistry:
    """Registry maintaining active and custom execution gap rules."""

    def __init__(self):
        self._rules: Dict[str, RuleDefinition] = {}
        self.load_default_rules()

    def load_default_rules(self) -> None:
        """Loads default 8 MVP execution gap rules."""
        for rule in get_default_execution_gap_rules():
            self._rules[rule.rule_code] = rule
        logger.info(f"Loaded {len(self._rules)} default Execution Gap rules into registry.")

    def register_rule(self, rule: RuleDefinition) -> None:
        """Registers or updates a rule definition."""
        self._rules[rule.rule_code] = rule
        logger.info(f"Registered Execution Gap rule: {rule.rule_code} - {rule.name}")

    def get_rule(self, rule_code: str) -> Optional[RuleDefinition]:
        """Retrieves rule by code."""
        return self._rules.get(rule_code)

    def list_rules(self, active_only: bool = False) -> List[RuleDefinition]:
        """Lists all registered rules."""
        if active_only:
            return [r for r in self._rules.values() if r.is_active]
        return list(self._rules.values())

    def set_rule_status(self, rule_code: str, is_active: bool) -> bool:
        """Enables or disables a rule."""
        if rule_code in self._rules:
            self._rules[rule_code].is_active = is_active
            return True
        return False
