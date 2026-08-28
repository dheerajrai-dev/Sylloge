"""Base parser abstractions for data ingestion."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from io import BytesIO, StringIO
from typing import Any, Dict, Generator, Iterator, List, Optional, Union
@dataclass
class ParsedRow:
    """Represents a single parsed raw row from a dataset source."""
    row_index: int
    data: Dict[str, Any]
    is_corrupted: bool = False
    corruption_reason: Optional[str] = None
    raw_text: Optional[str] = None


class BaseParser(ABC):
    """Abstract base class for dataset file parsers."""

    @abstractmethod
    def parse_stream(
        self, stream: Union[BytesIO, StringIO, str, bytes]
    ) -> Generator[ParsedRow, None, None]:
        """Streamingly parses input bytes, string or stream and yields ParsedRow records."""
        pass

    @staticmethod
    def normalize_content_to_text(content: Union[BytesIO, StringIO, str, bytes]) -> str:
        """Converts raw input (bytes, stream, or str) to standard unicode text."""
        if isinstance(content, str):
            # Strip UTF-8 BOM if present
            return content.lstrip("\ufeff")
        
        if isinstance(content, StringIO):
            return content.getvalue().lstrip("\ufeff")

        if isinstance(content, BytesIO):
            raw_bytes = content.getvalue()
        elif isinstance(content, bytes):
            raw_bytes = content
        else:
            raise TypeError(f"Unsupported content type: {type(content)}")

        # Try standard encodings
        for encoding in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
            try:
                return raw_bytes.decode(encoding)
            except UnicodeDecodeError:
                continue

        # Fallback with replacement characters
        return raw_bytes.decode("utf-8", errors="replace")
