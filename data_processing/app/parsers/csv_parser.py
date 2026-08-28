"""Resilient streaming CSV parser with auto-delimiter sniffing and header normalization."""

import csv
import io
from typing import Any, Dict, Generator, List, Optional, Union
from .base import BaseParser, ParsedRow


class CSVParser(BaseParser):
    """Parses delimited text files (CSV, TSV, PSV) into structured dictionaries."""

    def __init__(self, delimiter: Optional[str] = None):
        self.delimiter = delimiter

    def detect_delimiter(self, sample_text: str) -> str:
        """Sniffs delimiter or falls back to comma."""
        if self.delimiter:
            return self.delimiter

        lines = [line.strip() for line in sample_text.splitlines() if line.strip()][:5]
        if not lines:
            return ","

        sample = "\n".join(lines)
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample, delimiters=",\t;|")
            return dialect.delimiter
        except Exception:
            # Fallback heuristic
            first_line = lines[0]
            for delim in [",", "\t", ";", "|"]:
                if delim in first_line:
                    return delim
            return ","

    def parse_stream(
        self, stream: Union[io.BytesIO, io.StringIO, str, bytes]
    ) -> Generator[ParsedRow, None, None]:
        """Parses CSV stream row by row with 1-based indexing."""
        text = self.normalize_content_to_text(stream)
        if not text.strip():
            return

        delimiter = self.detect_delimiter(text)
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)

        headers: Optional[List[str]] = None
        row_index = 0

        for line_no, raw_row in enumerate(reader, start=1):
            if not raw_row or all(c.strip() == "" for c in raw_row):
                # Skip empty lines
                continue

            if headers is None:
                # First non-empty row is header
                headers = [h.strip() for h in raw_row]
                continue

            row_index += 1
            raw_text_repr = delimiter.join(raw_row)

            # Check for column count mismatch or corrupted row
            if len(raw_row) != len(headers):
                # If row is shorter or longer than header
                row_dict: Dict[str, Any] = {}
                for i, h in enumerate(headers):
                    if i < len(raw_row):
                        row_dict[h] = self._clean_value(raw_row[i])
                    else:
                        row_dict[h] = None
                
                # Extra columns stored under __extra__
                if len(raw_row) > len(headers):
                    row_dict["__extra__"] = [self._clean_value(v) for v in raw_row[len(headers):]]

                yield ParsedRow(
                    row_index=row_index,
                    data=row_dict,
                    is_corrupted=True,
                    corruption_reason=f"Column count mismatch: expected {len(headers)}, got {len(raw_row)}",
                    raw_text=raw_text_repr,
                )
                continue

            # Valid column count
            row_dict = {}
            for h, v in zip(headers, raw_row):
                row_dict[h] = self._clean_value(v)

            yield ParsedRow(
                row_index=row_index,
                data=row_dict,
                is_corrupted=False,
                raw_text=raw_text_repr,
            )

    @staticmethod
    def _clean_value(val: Any) -> Any:
        """Strips whitespace and normalizes empty string representations."""
        if val is None:
            return None
        if isinstance(val, str):
            cleaned = val.strip()
            if cleaned == "" or cleaned.lower() in ("null", "none", "n/a", "\\n"):
                return None
            return cleaned
        return val
