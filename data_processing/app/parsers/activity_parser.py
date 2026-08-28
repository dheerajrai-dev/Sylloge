"""Parser for SOC Analyst Activity Logs."""

from io import BytesIO, StringIO
from typing import Generator, Optional, Union
from shared.events.enums import DatasetType
from .base import BaseParser, ParsedRow
from .csv_parser import CSVParser
from .json_parser import JSONParser


class AnalystActivityParser(BaseParser):
    """Parser for Analyst Activity telemetry."""

    DATASET_TYPE = DatasetType.ANALYST_ACTIVITY
    PRIMARY_KEY_CANDIDATES = ["activity_id", "id", "log_id", "activityId"]
    TIMESTAMP_CANDIDATES = ["timestamp", "activity_time", "created_at", "event_time"]

    def __init__(self, delimiter: Optional[str] = None):
        self.csv_parser = CSVParser(delimiter=delimiter)
        self.json_parser = JSONParser()

    def parse_stream(
        self,
        stream: Union[BytesIO, StringIO, str, bytes],
        format_hint: Optional[str] = None,
    ) -> Generator[ParsedRow, None, None]:
        """Parses activity stream detecting CSV or JSON."""
        text = self.normalize_content_to_text(stream).strip()
        if not text:
            return

        if format_hint == "json" or (format_hint != "csv" and (text.startswith("{") or text.startswith("["))):
            yield from self.json_parser.parse_stream(text)
        else:
            yield from self.csv_parser.parse_stream(text)
