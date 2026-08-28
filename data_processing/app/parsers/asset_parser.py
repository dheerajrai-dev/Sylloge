"""Parser for Asset Inventory telemetry."""

from io import BytesIO, StringIO
from typing import Generator, Optional, Union
from shared.events.enums import DatasetType
from .base import BaseParser, ParsedRow
from .csv_parser import CSVParser
from .json_parser import JSONParser


class AssetInventoryParser(BaseParser):
    """Parser for Asset Inventory records."""

    DATASET_TYPE = DatasetType.ASSET_INVENTORY
    PRIMARY_KEY_CANDIDATES = ["asset_id", "id", "hostname", "assetId", "device_id"]
    TIMESTAMP_CANDIDATES = ["created_at", "updated_at", "last_seen", "timestamp"]

    def __init__(self, delimiter: Optional[str] = None):
        self.csv_parser = CSVParser(delimiter=delimiter)
        self.json_parser = JSONParser()

    def parse_stream(
        self,
        stream: Union[BytesIO, StringIO, str, bytes],
        format_hint: Optional[str] = None,
    ) -> Generator[ParsedRow, None, None]:
        """Parses asset inventory records detecting CSV or JSON."""
        text = self.normalize_content_to_text(stream).strip()
        if not text:
            return

        if format_hint == "json" or (format_hint != "csv" and (text.startswith("{") or text.startswith("["))):
            yield from self.json_parser.parse_stream(text)
        else:
            yield from self.csv_parser.parse_stream(text)
