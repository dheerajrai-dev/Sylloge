"""Check registry for Negative Space Engine."""

from typing import Dict, List, Optional
from shared.logging import logger
from .default_checks import get_default_negative_space_checks
from .models import CheckDefinition


class NegativeSpaceCheckRegistry:
    """Registry maintaining active and custom negative space checks."""

    def __init__(self):
        self._checks: Dict[str, CheckDefinition] = {}
        self.load_default_checks()

    def load_default_checks(self) -> None:
        """Loads default 8 MVP negative space checks."""
        for check in get_default_negative_space_checks():
            self._checks[check.check_id] = check
        logger.info(f"Loaded {len(self._checks)} default Negative Space checks into registry.")

    def register_check(self, check: CheckDefinition) -> None:
        """Registers or updates a check definition."""
        self._checks[check.check_id] = check
        logger.info(f"Registered Negative Space check: {check.check_id} - {check.name}")

    def get_check(self, check_id: str) -> Optional[CheckDefinition]:
        """Retrieves check by ID."""
        return self._checks.get(check_id)

    def list_checks(self, active_only: bool = False) -> List[CheckDefinition]:
        """Lists all registered checks."""
        if active_only:
            return [c for c in self._checks.values() if c.is_active]
        return list(self._checks.values())

    def set_check_status(self, check_id: str, is_active: bool) -> bool:
        """Enables or disables a check."""
        if check_id in self._checks:
            self._checks[check_id].is_active = is_active
            return True
        return False
