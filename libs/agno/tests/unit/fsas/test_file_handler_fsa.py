"""
Comprehensive unit tests for File Handler FSA.

Tests cover:
- Multi-format file I/O (text, JSON, YAML, XML, CSV, binary)
- Streaming operations for large files
- Atomic writes with rollback
- File watching and change detection
- File locking for concurrent access
- Compression and decompression
- Encryption and decryption
- Memory-mapped file operations
- Temporary file management with auto-cleanup
- Directory traversal and pattern matching
- Metadata extraction
"""

import json
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Dict, List

import pytest
import yaml

from agno.fsas.infrastructure.file_handler_fsa import (
    CompressionAlgorithm,
    FileCompressor,
    FileEncryptor,
    FileFormat,
    FileHandlerFSA,
    FileLocker,
    FileMMapper,
    FileOperation,
    FileReader,
    FileWatcher,
    FileWriter,
    LockMode,
    PathNavigator,
    TempFileManager,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    if temp_path.exists():
        import shutil
        shutil.rmtree(temp_path)


@pytest.fixture
def fsa(temp_dir):
    """Create FileHandlerFSA instance for tests."""
    return FileHandlerFSA(base_dir=temp_dir, enable_encryption=True)


def test_read_write_text_file(fsa, temp_dir):
    """Test reading and writing text files."""
    test_file = temp_dir / "test.txt"
    test_content = "Hello, World!\nThis is a test file."

    # Write text file
    result = fsa.write(test_file, test_content, format=FileFormat.TEXT)
    assert result is True
    assert test_file.exists()

    # Read text file
    content = fsa.read(test_file, format=FileFormat.TEXT)
    assert content == test_content


def test_read_write_json_yaml_files(fsa, temp_dir):
    """Test reading and writing JSON and YAML files."""
    test_data = {
        "name": "Test",
        "value": 123,
        "nested": {
            "key": "value",
            "items": [1, 2, 3]
        }
    }

    # Test JSON
    json_file = temp_dir / "test.json"
    fsa.write(json_file, test_data, format=FileFormat.JSON)
    assert json_file.exists()

    json_content = fsa.read(json_file, format=FileFormat.JSON)
    assert json_content == test_data

    # Test YAML
    yaml_file = temp_dir / "test.yaml"
    fsa.write(yaml_file, test_data, format=FileFormat.YAML)
    assert yaml_file.exists()

    yaml_content = fsa.read(yaml_file, format=FileFormat.YAML)
    assert yaml_content == test_data


def test_streaming_large_file(fsa, temp_dir):
    """Test streaming operations for large files."""
    test_file = temp_dir / "large.txt"

    # Create a large file
    large_content = "\n".join([f"Line {i}" for i in range(1000)])
    fsa.write(test_file, large_content, format=FileFormat.TEXT)

    # Stream read the file
    line_count = 0
    for line in fsa.read(test_file, format=FileFormat.TEXT, streaming=True):
        line_count += 1

    assert line_count == 1000


def test_atomic_write_with_rollback(fsa, temp_dir):
    """Test atomic write operations with backup and rollback."""
    test_file = temp_dir / "atomic_test.txt"

    # Write initial content
    initial_content = "Initial content"
    fsa.write(test_file, initial_content, format=FileFormat.TEXT, atomic=True, backup=True)

    # Verify initial content
    assert fsa.read(test_file, format=FileFormat.TEXT) == initial_content

    # Write new content with atomic operation
    new_content = "New content with atomic write"
    fsa.write(test_file, new_content, format=FileFormat.TEXT, atomic=True, backup=True)

    # Verify new content
    assert fsa.read(test_file, format=FileFormat.TEXT) == new_content

    # Check that backup was created
    backup_files = list(temp_dir.glob("*.backup_*"))
    assert len(backup_files) > 0


def test_file_watching_change_detection(fsa, temp_dir):
    """Test file watching and change detection."""
    test_file = temp_dir / "watched.txt"
    test_file.write_text("Initial content")

    changes_detected = []

    def on_change(path, state):
        changes_detected.append((path, state))

    # Start watching
    fsa.watch(test_file, on_change, recursive=False)

    # Make a change
    time.sleep(0.1)
    test_file.write_text("Modified content")

    # Wait for change detection
    time.sleep(1.5)

    # Verify change was detected
    assert len(changes_detected) > 0

    # Cleanup
    fsa.watcher.stop_watching(test_file)


def test_file_locking_concurrent_access(fsa, temp_dir):
    """Test file locking for concurrent access control."""
    test_file = temp_dir / "locked.txt"
    test_file.write_text("Content")

    # Acquire exclusive lock
    lock_acquired = fsa.lock(test_file, mode=LockMode.EXCLUSIVE)
    assert lock_acquired is True

    # Try to acquire another lock (should timeout)
    def try_lock():
        try:
            fsa.lock(test_file, mode=LockMode.EXCLUSIVE, timeout=0.5)
            return True
        except Exception:
            return False

    # Run in another thread
    result = [False]

    def thread_func():
        result[0] = try_lock()

    thread = threading.Thread(target=thread_func)
    thread.start()
    thread.join()

    # Second lock should have failed
    assert result[0] is False

    # Release lock
    fsa.unlock(test_file)

    # Now lock should succeed
    lock_acquired_2 = fsa.lock(test_file, mode=LockMode.EXCLUSIVE, timeout=0.5)
    assert lock_acquired_2 is True
    fsa.unlock(test_file)


def test_compression_decompression_formats(fsa, temp_dir):
    """Test compression and decompression with different algorithms."""
    test_file = temp_dir / "compress_test.txt"
    test_content = "This is test content for compression" * 100
    test_file.write_text(test_content)

    # Test GZIP compression
    gzip_file = fsa.compress(test_file, algorithm=CompressionAlgorithm.GZIP, level=9)
    assert gzip_file.exists()
    assert gzip_file.suffix == ".gzip"

    # Decompress
    decompressed_file = fsa.decompress(gzip_file)
    assert decompressed_file.exists()
    assert decompressed_file.read_text() == test_content

    # Test BZIP2 compression
    bzip2_file = fsa.compress(test_file, algorithm=CompressionAlgorithm.BZIP2, level=9)
    assert bzip2_file.exists()
    assert bzip2_file.suffix == ".bzip2"

    # Decompress
    decompressed_bzip2 = fsa.decompress(bzip2_file)
    assert decompressed_bzip2.exists()
    assert decompressed_bzip2.read_text() == test_content

    # Test LZMA compression
    lzma_file = fsa.compress(test_file, algorithm=CompressionAlgorithm.LZMA, level=9)
    assert lzma_file.exists()
    assert lzma_file.suffix == ".lzma"

    # Decompress
    decompressed_lzma = fsa.decompress(lzma_file)
    assert decompressed_lzma.exists()
    assert decompressed_lzma.read_text() == test_content


def test_encryption_decryption(fsa, temp_dir):
    """Test file encryption and decryption."""
    # Check if encryption is available
    try:
        from cryptography.fernet import Fernet
        crypto_available = True
    except ImportError:
        crypto_available = False

    if not crypto_available:
        pytest.skip("Cryptography package not available")

    test_file = temp_dir / "secret.txt"
    test_content = "Secret content that should be encrypted"
    test_file.write_text(test_content)

    password = "super_secret_password_123"

    # Encrypt file
    encrypted_file = fsa.encrypt(test_file, password)
    assert encrypted_file.exists()

    # Verify encrypted content is different
    encrypted_content = encrypted_file.read_bytes()
    assert encrypted_content != test_content.encode()

    # Decrypt file
    decrypted_file = fsa.decrypt(encrypted_file, password)
    assert decrypted_file.exists()

    # Verify decrypted content matches original
    decrypted_content = decrypted_file.read_text()
    assert decrypted_content == test_content


def test_memory_mapped_operations(fsa, temp_dir):
    """Test memory-mapped file operations for performance."""
    test_file = temp_dir / "mmap_test.bin"
    test_data = b"Memory mapped content for testing" * 100

    # Write binary file
    test_file.write_bytes(test_data)

    # Read using memory mapping
    mmap_data = fsa.mmap_read(test_file, offset=0)
    assert mmap_data == test_data

    # Read partial data
    partial_data = fsa.mmap_read(test_file, offset=10, length=20)
    assert partial_data == test_data[10:30]


def test_temp_file_auto_cleanup(fsa, temp_dir):
    """Test temporary file management with auto-cleanup."""
    # Create temporary files
    temp_file_1 = fsa.create_temp(suffix=".txt", prefix="test_")
    temp_file_2 = fsa.create_temp(suffix=".json", prefix="data_")

    assert temp_file_1.exists()
    assert temp_file_2.exists()
    assert temp_file_1.suffix == ".txt"
    assert temp_file_2.suffix == ".json"

    # Write some data
    temp_file_1.write_text("Temporary content")

    # Verify data
    assert temp_file_1.read_text() == "Temporary content"

    # Cleanup
    fsa.temp_manager.cleanup()

    # Verify files are deleted
    assert not temp_file_1.exists()
    assert not temp_file_2.exists()


def test_directory_traversal_patterns(fsa, temp_dir):
    """Test directory traversal with pattern matching."""
    # Create directory structure
    (temp_dir / "subdir1").mkdir()
    (temp_dir / "subdir2").mkdir()
    (temp_dir / "subdir1" / "nested").mkdir()

    # Create files
    (temp_dir / "file1.txt").write_text("content")
    (temp_dir / "file2.json").write_text("{}")
    (temp_dir / "subdir1" / "file3.txt").write_text("content")
    (temp_dir / "subdir1" / "nested" / "file4.txt").write_text("content")
    (temp_dir / "subdir2" / "file5.yaml").write_text("")

    # Traverse with pattern (non-recursive)
    txt_files = fsa.traverse(temp_dir, pattern="*.txt", recursive=False)
    assert len(txt_files) == 1

    # Traverse with pattern (recursive)
    txt_files_recursive = fsa.traverse(temp_dir, pattern="*.txt", recursive=True)
    assert len(txt_files_recursive) == 3

    # Traverse all files (recursive)
    all_files = fsa.traverse(temp_dir, pattern="*", recursive=True)
    assert len(all_files) == 5


def test_metadata_extraction(fsa, temp_dir):
    """Test file metadata extraction and validation."""
    test_file = temp_dir / "metadata_test.txt"
    test_content = "Test content for metadata"
    test_file.write_text(test_content)

    # Get metadata
    metadata = fsa.get_metadata(test_file)

    assert metadata.path == test_file
    assert metadata.size == len(test_content)
    assert metadata.is_file is True
    assert metadata.is_dir is False
    assert metadata.is_symlink is False
    assert metadata.checksum is not None
    assert len(metadata.checksum) == 64  # SHA256 hex digest length
    assert metadata.permissions is not None


def test_csv_file_operations(fsa, temp_dir):
    """Test CSV file reading and writing."""
    csv_file = temp_dir / "test.csv"
    csv_data = [
        {"name": "Alice", "age": "30", "city": "New York"},
        {"name": "Bob", "age": "25", "city": "Los Angeles"},
        {"name": "Charlie", "age": "35", "city": "Chicago"}
    ]

    # Write CSV
    fsa.write(csv_file, csv_data, format=FileFormat.CSV)
    assert csv_file.exists()

    # Read CSV
    read_data = fsa.read(csv_file, format=FileFormat.CSV)
    assert len(read_data) == 3
    assert read_data[0]["name"] == "Alice"
    assert read_data[1]["age"] == "25"

    # Test streaming CSV
    row_count = 0
    for row in fsa.read(csv_file, format=FileFormat.CSV, streaming=True):
        row_count += 1

    assert row_count == 3


def test_binary_file_operations(fsa, temp_dir):
    """Test binary file reading and writing."""
    binary_file = temp_dir / "test.bin"
    binary_data = bytes([0x00, 0x01, 0x02, 0x03, 0xFF, 0xFE, 0xFD])

    # Write binary
    fsa.write(binary_file, binary_data, format=FileFormat.BINARY)
    assert binary_file.exists()

    # Read binary
    read_data = fsa.read(binary_file, format=FileFormat.BINARY)
    assert read_data == binary_data

    # Test streaming binary
    chunk_count = 0
    total_bytes = b""
    for chunk in fsa.read(binary_file, format=FileFormat.BINARY, streaming=True):
        chunk_count += 1
        total_bytes += chunk

    assert total_bytes == binary_data


def test_append_operations(fsa, temp_dir):
    """Test file append operations."""
    append_file = temp_dir / "append.txt"

    # Write initial content
    fsa.write(append_file, "Line 1\n", format=FileFormat.TEXT)

    # Append more content
    fsa.append(append_file, "Line 2\n", format=FileFormat.TEXT)
    fsa.append(append_file, "Line 3\n", format=FileFormat.TEXT)

    # Read and verify
    content = fsa.read(append_file, format=FileFormat.TEXT)
    assert content == "Line 1\nLine 2\nLine 3\n"


def test_execute_operation(fsa, temp_dir):
    """Test the execute method with different operations."""
    test_file = temp_dir / "execute_test.txt"
    test_content = "Execute operation test"

    # Test WRITE operation
    result = fsa.execute(
        FileOperation.WRITE,
        test_file,
        data=test_content,
        format=FileFormat.TEXT
    )
    assert result is True

    # Test READ operation
    content = fsa.execute(
        FileOperation.READ,
        test_file,
        format=FileFormat.TEXT
    )
    assert content == test_content

    # Test APPEND operation
    fsa.execute(
        FileOperation.APPEND,
        test_file,
        data="\nAppended text",
        format=FileFormat.TEXT
    )

    updated_content = fsa.read(test_file, format=FileFormat.TEXT)
    assert "Appended text" in updated_content


def test_validation(fsa, temp_dir):
    """Test FSA validation method."""
    # Should pass validation
    result = fsa.validate()
    assert result is True


def test_context_manager(temp_dir):
    """Test FileHandlerFSA as a context manager."""
    test_file = temp_dir / "context_test.txt"

    with FileHandlerFSA(base_dir=temp_dir) as fsa:
        fsa.write(test_file, "Context manager test", format=FileFormat.TEXT)
        content = fsa.read(test_file, format=FileFormat.TEXT)
        assert content == "Context manager test"

        # Create temp file
        temp_file = fsa.create_temp()
        assert temp_file.exists()

    # After context exit, temp files should be cleaned up
    # (though the file might still exist if not properly managed)


def test_xml_file_operations(fsa, temp_dir):
    """Test XML file reading and writing."""
    import xml.etree.ElementTree as ET

    # Create XML structure
    root = ET.Element("root")
    child1 = ET.SubElement(root, "child1", attrib={"name": "first"})
    child1.text = "Child 1 content"
    child2 = ET.SubElement(root, "child2", attrib={"name": "second"})
    child2.text = "Child 2 content"

    xml_file = temp_dir / "test.xml"

    # Write XML
    fsa.write(xml_file, root, format=FileFormat.XML)
    assert xml_file.exists()

    # Read XML
    read_root = fsa.read(xml_file, format=FileFormat.XML)
    assert read_root.tag == "root"
    children = list(read_root)
    assert len(children) == 2
    assert children[0].attrib["name"] == "first"
