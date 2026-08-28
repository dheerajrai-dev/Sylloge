"""Hashing and cryptographic utility helpers."""

import hashlib
import json
from pathlib import Path
from typing import Any, Union


def hash_file_sha256(file_path: Union[str, Path]) -> str:
    """Calculates SHA-256 checksum of a local file in chunks."""
    sha256_func = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256_func.update(chunk)
    return sha256_func.hexdigest()


def compute_sha256(data: Union[str, bytes, bytearray]) -> str:
    """Computes SHA-256 for strings or bytes."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def canonical_json_dumps(obj: Any) -> str:
    """Returns canonical formatted JSON string."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
