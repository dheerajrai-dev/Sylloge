"""Resilient JSON and NDJSON parser supporting multiple container layouts and malformed recovery."""

import io
import json
from typing import Any, Dict, Generator, List, Optional, Union
from .base import BaseParser, ParsedRow


class JSONParser(BaseParser):
    """Parses JSON formats (JSON Array, NDJSON/JSONL, Nested Arrays, Single Object)."""

    def parse_stream(
        self, stream: Union[io.BytesIO, io.StringIO, str, bytes]
    ) -> Generator[ParsedRow, None, None]:
        """Streamingly parses JSON or NDJSON stream."""
        text = self.normalize_content_to_text(stream).strip()
        if not text:
            return

        # 1. Attempt standard full-document JSON parse
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                # Standard array of records
                for idx, item in enumerate(parsed, start=1):
                    if isinstance(item, dict):
                        yield ParsedRow(row_index=idx, data=item, is_corrupted=False)
                    else:
                        yield ParsedRow(
                            row_index=idx,
                            data={"raw_value": item},
                            is_corrupted=True,
                            corruption_reason="Array item is not a JSON object",
                            raw_text=json.dumps(item),
                        )
                return

            if isinstance(parsed, dict):
                # Check for known array wrapper keys
                wrapper_keys = [
                    "records", "data", "events", "items", "alerts",
                    "cases", "investigations", "escalations", "assets",
                    "incidents", "coverage", "activities"
                ]
                found_wrapper = False
                for key in wrapper_keys:
                    if key in parsed and isinstance(parsed[key], list):
                        found_wrapper = True
                        for idx, item in enumerate(parsed[key], start=1):
                            if isinstance(item, dict):
                                yield ParsedRow(row_index=idx, data=item, is_corrupted=False)
                            else:
                                yield ParsedRow(
                                    row_index=idx,
                                    data={"raw_value": item},
                                    is_corrupted=True,
                                    corruption_reason="Wrapped item is not a JSON object",
                                    raw_text=json.dumps(item),
                                )
                        return

                if not found_wrapper:
                    # Single JSON object
                    yield ParsedRow(row_index=1, data=parsed, is_corrupted=False)
                    return

        except json.JSONDecodeError:
            # Fall back to line-by-line NDJSON / JSONL parsing
            pass

        # 2. NDJSON / Line-by-line fallback
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for idx, line in enumerate(lines, start=1):
            try:
                item = json.loads(line)
                if isinstance(item, dict):
                    yield ParsedRow(row_index=idx, data=item, is_corrupted=False, raw_text=line)
                else:
                    yield ParsedRow(
                        row_index=idx,
                        data={"raw_value": item},
                        is_corrupted=True,
                        corruption_reason="NDJSON row is not a JSON object",
                        raw_text=line,
                    )
            except json.JSONDecodeError as exc:
                yield ParsedRow(
                    row_index=idx,
                    data={"corrupted_line": line},
                    is_corrupted=True,
                    corruption_reason=f"Invalid JSON line syntax: {str(exc)}",
                    raw_text=line,
                )
