"""SAT-SA Data Processing Microservice Package."""

import os

_dp_dir = os.path.dirname(os.path.abspath(__file__))
_dp_app_dir = os.path.join(_dp_dir, "app")

__path__ = [_dp_app_dir, _dp_dir]

from data_processing.mapping.engine import FieldMappingEngine
from data_processing.mapping.normalizer import CanonicalNormalizer
from data_processing.parsers import get_parser_for_dataset, CSVParser, JSONParser
from data_processing.pipeline.ingestion_service import IngestionPipelineService
from data_processing.quarantine.manager import QuarantineManager
from data_processing.quarantine.validator import RowValidator
from data_processing.main import app

__all__ = [
    "app",
    "FieldMappingEngine",
    "CanonicalNormalizer",
    "IngestionPipelineService",
    "QuarantineManager",
    "RowValidator",
    "get_parser_for_dataset",
    "CSVParser",
    "JSONParser",
]
