"""Cryptographic Merkle Tree and SHA-256 Hashing Engine for SAT-SA."""

import hashlib
import json
from typing import Any, Dict, List, Optional, Union


def sha256_hash_bytes(data: bytes) -> str:
    """Computes hexadecimal SHA-256 digest of raw byte content."""
    return hashlib.sha256(data).hexdigest()


def sha256_hash_str(text: str) -> str:
    """Computes hexadecimal SHA-256 digest of utf-8 string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_json_bytes(data: Any) -> bytes:
    """Encodes Python dictionary/list into deterministic canonical sorted JSON bytes."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def sha256_hash_json(data: Any) -> str:
    """Computes hexadecimal SHA-256 digest of canonical deterministic JSON."""
    return sha256_hash_bytes(canonical_json_bytes(data))


class MerkleTree:
    """Deterministic Binary SHA-256 Merkle Tree implementation.
    
    Computes cryptographic root hashes across structured datasets, lists of records,
    and audit trail subtrees.
    """

    def __init__(self, leaves: Optional[List[str]] = None):
        """Initializes Merkle Tree from a list of leaf SHA-256 hex strings."""
        self.leaves: List[str] = [leaf.lower() for leaf in (leaves or [])]
        self._root: Optional[str] = None
        if self.leaves:
            self._root = self._build_tree(self.leaves)

    @classmethod
    def from_records(cls, records: List[Any]) -> "MerkleTree":
        """Builds a Merkle tree by deterministically hashing each record object."""
        leaf_hashes = [sha256_hash_json(r) for r in records]
        return cls(leaf_hashes)

    @property
    def root_hash(self) -> str:
        """Returns root SHA-256 hexadecimal hash.
        
        If tree is empty, returns the SHA-256 of empty bytes (e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855).
        """
        if self._root is None:
            if not self.leaves:
                return hashlib.sha256(b"").hexdigest()
            self._root = self._build_tree(self.leaves)
        return self._root

    def _build_tree(self, nodes: List[str]) -> str:
        """Recursively pairs and hashes nodes up to the root."""
        if not nodes:
            return hashlib.sha256(b"").hexdigest()
        if len(nodes) == 1:
            return nodes[0]

        current_level = sorted(nodes)  # Deterministic sorting
        next_level: List[str] = []

        for i in range(0, len(current_level), 2):
            left = current_level[i]
            if i + 1 < len(current_level):
                right = current_level[i + 1]
            else:
                right = left  # Duplicate odd leaf for binary tree balance
            combined = (left + right).encode("utf-8")
            parent_hash = hashlib.sha256(combined).hexdigest()
            next_level.append(parent_hash)

        return self._build_tree(next_level)

    @classmethod
    def compute_composite_manifest_root(
        cls,
        raw_submissions_sha256: str,
        quarantined_records_sha256: str,
        normalized_events_sha256: str,
        findings_and_scores_sha256: str,
    ) -> str:
        """Computes the authoritative composite root Merkle SHA-256 for a manifest.
        
        Formula:
        Root SHA-256 = SHA256(SortConcat(raw_sha || quarantine_sha || normalized_sha || findings_sha))
        """
        subtrees = sorted([
            raw_submissions_sha256.lower(),
            quarantined_records_sha256.lower(),
            normalized_events_sha256.lower(),
            findings_and_scores_sha256.lower(),
        ])
        concatenated = "".join(subtrees).encode("utf-8")
        return hashlib.sha256(concatenated).hexdigest()
