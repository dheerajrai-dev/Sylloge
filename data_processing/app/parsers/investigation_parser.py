"""Parser for SOC Analyst Investigation records."""

from io import BytesIO, StringIO
from typing import Generator, Optional, Union
from shared.events.enums import DatasetType
from .base import BaseParser, ParsedRow
from .csv_parser import CSVParser
from .json_parser import JSONParser


class InvestigationRecordParser(BaseParser):
    """Parser for Investigation records."""

    DATASET_TYPE = DatasetType.INVESTIGATION_RECORDS
    PRIMARY_KEY_CANDIDATES = ["investigation_id", "id", "inv_id", "investigationId"]
    TIMESTAMP_CANDIDATES = ["timestamp", "investigated_at", "action_time", "created_at"]

    def __init__(self, delimiter: Optional[str] = None):
        self.csv_parser = CSVParser(delimiter=delimiter)
        self.json_parser = JSONParser()

    def parse_stream(
        self,
        stream: Union[BytesIO, StringIO, str, bytes],
        format_hint: Optional[str] = None,
    ) -> Generator[ParsedRow, None, None]:
        """Parses investigation records detecting CSV or JSON."""
        text = self.normalize_content_to_text(stream).strip()
        if not text:
            return

        if format_hint == "json" or (format_hint != "csv" and (text.startswith("{") or text.startswith("["))):
            yield from self.json_parser.parse_stream(text)
        else:
            yield from self.csv_parser.parse_stream(text)
