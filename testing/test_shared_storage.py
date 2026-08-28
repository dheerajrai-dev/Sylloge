"""Unit tests for SHA-256 Merkle tree calculation and MinIO storage client."""

import hashlib
import json
import uuid
from unittest.mock import MagicMock, patch
import pytest

from shared.errors import StorageError
from shared.storage.merkle import (
    MerkleTree,
    canonical_json_bytes,
    sha256_hash_bytes,
    sha256_hash_json,
    sha256_hash_str,
)
from shared.storage.minio_client import MinIOClientWrapper


def test_sha256_helpers():
    """Verifies SHA-256 byte and string helpers."""
    assert sha256_hash_bytes(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert sha256_hash_str("") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    data = {"b": 2, "a": 1}
    # Deterministic sorting regardless of key order
    data_reordered = {"a": 1, "b": 2}
    assert sha256_hash_json(data) == sha256_hash_json(data_reordered)


def test_merkle_tree_empty():
    """Verifies Merkle tree on empty leaf collection."""
    tree = MerkleTree([])
    assert tree.root_hash == hashlib.sha256(b"").hexdigest()


def test_merkle_tree_single_leaf():
    """Verifies Merkle tree with single leaf."""
    leaf = sha256_hash_str("test_leaf")
    tree = MerkleTree([leaf])
    assert tree.root_hash == leaf


def test_merkle_tree_multi_leaves():
    """Verifies Merkle tree with multiple leaves produces deterministic hash."""
    leaves = [sha256_hash_str(f"record_{i}") for i in range(5)]
    tree1 = MerkleTree(leaves)
    tree2 = MerkleTree(list(reversed(leaves)))  # Tree implementation sorts internally

    assert tree1.root_hash == tree2.root_hash
    assert len(tree1.root_hash) == 64


def test_merkle_tree_tamper_detection():
    """Verifies modifying a single leaf changes the root Merkle hash."""
    records_clean = [{"id": 1, "val": "normal"}, {"id": 2, "val": "normal"}]
    records_tampered = [{"id": 1, "val": "tampered"}, {"id": 2, "val": "normal"}]

    tree_clean = MerkleTree.from_records(records_clean)
    tree_tampered = MerkleTree.from_records(records_tampered)

    assert tree_clean.root_hash != tree_tampered.root_hash


def test_composite_manifest_root_computation():
    """Verifies authoritative formula for Merkle root manifest computation."""
    raw_sha = "1111" * 16
    quarantine_sha = "2222" * 16
    normalized_sha = "3333" * 16
    findings_sha = "4444" * 16

    root1 = MerkleTree.compute_composite_manifest_root(
        raw_submissions_sha256=raw_sha,
        quarantined_records_sha256=quarantine_sha,
        normalized_events_sha256=normalized_sha,
        findings_and_scores_sha256=findings_sha,
    )

    # Order of arguments should not matter due to internal sorting
    root2 = MerkleTree.compute_composite_manifest_root(
        raw_submissions_sha256=findings_sha,
        quarantined_records_sha256=raw_sha,
        normalized_events_sha256=quarantine_sha,
        findings_and_scores_sha256=normalized_sha,
    )

    assert root1 == root2
    assert len(root1) == 64


def test_minio_client_wrapper_mocked():
    """Verifies MinIO client wrapper operations with mocked S3 backend."""
    mock_minio = MagicMock()
    mock_minio.bucket_exists.return_value = False

    client = MinIOClientWrapper(endpoint="localhost:9000")
    client._client = mock_minio

    # Test bucket creation
    created = client.ensure_buckets(["test-bucket-1", "test-bucket-2"])
    assert len(created) == 2
    assert mock_minio.make_bucket.call_count == 2

    # Test byte upload
    sample_bytes = b"Hello SAT-SA Air Gap"
    computed_sha = client.upload_bytes("test-bucket-1", "sample.txt", sample_bytes)
    assert computed_sha == sha256_hash_bytes(sample_bytes)
    assert mock_minio.put_object.called

    # Test JSON upload
    data = {"platform": "SAT-SA", "version": "1.0"}
    json_sha = client.upload_json("test-bucket-1", "metadata.json", data)
    assert len(json_sha) == 64

    # Test download bytes
    mock_response = MagicMock()
    mock_response.read.return_value = sample_bytes
    mock_minio.get_object.return_value = mock_response

    downloaded = client.download_bytes("test-bucket-1", "sample.txt")
    assert downloaded == sample_bytes

    # Test download JSON
    mock_response.read.return_value = json.dumps(data).encode("utf-8")
    downloaded_json = client.download_json("test-bucket-1", "metadata.json")
    assert downloaded_json["platform"] == "SAT-SA"

    # Test list objects
    mock_obj = MagicMock()
    mock_obj.object_name = "test.csv"
    mock_minio.list_objects.return_value = [mock_obj]
    obj_list = client.list_objects("test-bucket-1")
    assert obj_list == ["test.csv"]

    # Test delete object
    client.delete_object("test-bucket-1", "test.csv")
    mock_minio.remove_object.assert_called_with("test-bucket-1", "test.csv")
