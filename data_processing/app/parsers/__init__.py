"""Parser registry and factory for SAT-SA telemetry dataset ingestion."""

from typing import Dict, Optional, Type, Union
from shared.events.enums import DatasetType
from .base import BaseParser, ParsedRow
from .csv_parser import CSVParser
from .json_parser import JSONParser
from .alert_parser import AlertMetadataParser
from .case_parser import CaseManagementParser
from .investigation_parser import InvestigationRecordParser
from .escalation_parser import EscalationRecordParser
from .asset_parser import AssetInventoryParser
from .incident_parser import IncidentReportParser
from .coverage_parser import CoverageReportParser
from .activity_parser import AnalystActivityParser


PARSER_REGISTRY: Dict[DatasetType, Type[BaseParser]] = {
    DatasetType.ALERT_METADATA: AlertMetadataParser,
    DatasetType.CASE_MANAGEMENT: CaseManagementParser,
    DatasetType.INVESTIGATION_RECORDS: InvestigationRecordParser,
    DatasetType.ESCALATION_RECORDS: EscalationRecordParser,
    DatasetType.ASSET_INVENTORY: AssetInventoryParser,
    DatasetType.INCIDENT_REPORTS: IncidentReportParser,
    DatasetType.COVERAGE_REPORTS: CoverageReportParser,
    DatasetType.ANALYST_ACTIVITY: AnalystActivityParser,
}


def get_parser_for_dataset(
    dataset_type: Union[DatasetType, str], delimiter: Optional[str] = None
) -> BaseParser:
    """Instantiates and returns the specialized parser for the requested dataset type."""
    if isinstance(dataset_type, str):
        try:
            dataset_type = DatasetType(dataset_type)
        except ValueError:
            # Fallback to general CSV or JSON parser
            return CSVParser(delimiter=delimiter)

    parser_cls = PARSER_REGISTRY.get(dataset_type)
    if parser_cls is not None:
        if parser_cls in (CSVParser, JSONParser):
            return parser_cls()
        return parser_cls(delimiter=delimiter)

    return CSVParser(delimiter=delimiter)


__all__ = [
    "BaseParser",
    "ParsedRow",
    "CSVParser",
    "JSONParser",
    "AlertMetadataParser",
    "CaseManagementParser",
    "InvestigationRecordParser",
    "EscalationRecordParser",
    "AssetInventoryParser",
    "IncidentReportParser",
    "CoverageReportParser",
    "AnalystActivityParser",
    "PARSER_REGISTRY",
    "get_parser_for_dataset",
]
