# File Handler FSA - Comprehensive File Operations

A production-ready File Service Adapter (FSA) providing comprehensive file handling capabilities with support for multiple formats, streaming, encryption, compression, and atomic operations.

## Features

### Core Capabilities
- **Multi-format Support**: Text, JSON, YAML, XML, CSV, Binary, Parquet, HDF5
- **Async & Sync Operations**: Flexible I/O operations
- **Streaming**: Efficient handling of large files
- **File Watching**: Real-time change detection with callbacks
- **Atomic Operations**: Safe writes with automatic rollback on failure
- **File Locking**: Concurrent access coordination
- **Compression**: gzip, bzip2, lzma, zstd
- **Encryption**: AES encryption for sensitive files
- **Memory-Mapped I/O**: High-performance file access
- **Temporary Files**: Auto-cleanup lifecycle management
- **Metadata Extraction**: Comprehensive file information
- **Path Traversal**: Directory operations with pattern matching
- **Backup & Versioning**: Automatic backup creation

## Installation

The File Handler FSA is part of the agno library:

```python
from agno.fsas.infrastructure.file_handler_fsa import FileHandlerFSA
```

## Quick Start

### Basic Usage

```python
from pathlib import Path
from agno.fsas.infrastructure.file_handler_fsa import (
    FileHandlerFSA,
    FileFormat,
    FileOperation
)

# Initialize FSA
fsa = FileHandlerFSA(base_dir=Path("/tmp/data"))

# Write a text file
fsa.write(
    Path("example.txt"),
    "Hello, World!",
    format=FileFormat.TEXT
)

# Read the file
content = fsa.read(
    Path("example.txt"),
    format=FileFormat.TEXT
)

print(content)  # "Hello, World!"
```

### JSON Operations

```python
data = {
    "name": "John Doe",
    "age": 30,
    "skills": ["Python", "Machine Learning", "Data Science"]
}

# Write JSON
fsa.write(
    Path("user.json"),
    data,
    format=FileFormat.JSON
)

# Read JSON
user_data = fsa.read(
    Path("user.json"),
    format=FileFormat.JSON
)
```

### YAML Operations

```python
config = {
    "database": {
        "host": "localhost",
        "port": 5432,
        "name": "mydb"
    },
    "logging": {
        "level": "INFO"
    }
}

# Write YAML
fsa.write(
    Path("config.yaml"),
    config,
    format=FileFormat.YAML
)

# Read YAML
config_data = fsa.read(
    Path("config.yaml"),
    format=FileFormat.YAML
)
```

### CSV Operations

```python
csv_data = [
    {"name": "Alice", "age": "30", "city": "New York"},
    {"name": "Bob", "age": "25", "city": "Los Angeles"},
    {"name": "Charlie", "age": "35", "city": "Chicago"}
]

# Write CSV
fsa.write(
    Path("users.csv"),
    csv_data,
    format=FileFormat.CSV
)

# Read CSV (non-streaming)
users = fsa.read(
    Path("users.csv"),
    format=FileFormat.CSV
)

# Stream large CSV files
for row in fsa.read(Path("large_data.csv"), format=FileFormat.CSV, streaming=True):
    process_row(row)
```

### Streaming Large Files

```python
# Stream text file line by line
for line in fsa.read(Path("large_file.txt"), format=FileFormat.TEXT, streaming=True):
    process_line(line)

# Stream binary file in chunks
for chunk in fsa.read(Path("large_binary.bin"), format=FileFormat.BINARY, streaming=True):
    process_chunk(chunk)
```

### Atomic Operations with Backup

```python
# Atomic write with automatic backup
fsa.write(
    Path("important_data.json"),
    data,
    format=FileFormat.JSON,
    atomic=True,  # Ensures atomicity
    backup=True   # Creates backup before writing
)
```

### File Watching

```python
def on_file_change(path, state):
    print(f"File {path} changed!")
    print(f"New state: {state}")

# Watch a single file
fsa.watch(
    Path("monitored.txt"),
    callback=on_file_change,
    recursive=False
)

# Watch directory recursively
fsa.watch(
    Path("data/"),
    callback=on_file_change,
    recursive=True,
    patterns=["*.json", "*.yaml"]
)
```

### File Locking

```python
from agno.fsas.infrastructure.file_handler_fsa import LockMode

# Acquire exclusive lock
fsa.lock(Path("shared_resource.dat"), mode=LockMode.EXCLUSIVE)

try:
    # Perform operations
    data = fsa.read(Path("shared_resource.dat"), format=FileFormat.TEXT)
    # ... modify data ...
    fsa.write(Path("shared_resource.dat"), data, format=FileFormat.TEXT)
finally:
    fsa.unlock(Path("shared_resource.dat"))

# Using context manager
with fsa.locker.locked(Path("shared_resource.dat"), mode=LockMode.EXCLUSIVE):
    # File is locked here
    data = fsa.read(Path("shared_resource.dat"), format=FileFormat.TEXT)
    # ... operations ...
```

### Compression

```python
from agno.fsas.infrastructure.file_handler_fsa import CompressionAlgorithm

# Compress with GZIP
compressed_file = fsa.compress(
    Path("large_file.txt"),
    algorithm=CompressionAlgorithm.GZIP,
    level=9  # Maximum compression
)

# Decompress
decompressed_file = fsa.decompress(compressed_file)

# Other algorithms
fsa.compress(Path("file.txt"), algorithm=CompressionAlgorithm.BZIP2)
fsa.compress(Path("file.txt"), algorithm=CompressionAlgorithm.LZMA)
fsa.compress(Path("file.txt"), algorithm=CompressionAlgorithm.ZSTD)  # Requires zstandard
```

### Encryption & Decryption

```python
# Encrypt sensitive file
encrypted_file = fsa.encrypt(
    Path("secrets.txt"),
    password="my_secure_password_123"
)

# Decrypt
decrypted_file = fsa.decrypt(
    encrypted_file,
    password="my_secure_password_123"
)
```

### Memory-Mapped I/O

```python
# Read entire file using memory mapping
data = fsa.mmap_read(Path("large_binary.bin"))

# Read specific portion
partial_data = fsa.mmap_read(
    Path("large_binary.bin"),
    offset=1024,
    length=2048
)

# Use context manager for memory-mapped access
with fsa.mmapper.mmap_context(Path("large_file.bin"), mode='r') as mm:
    # Access file like an array
    byte_at_100 = mm[100]
    chunk = mm[100:200]
```

### Temporary File Management

```python
# Create temporary file
temp_file = fsa.create_temp(suffix=".txt", prefix="work_")

# Use temporary file
temp_file.write_text("Temporary data")
process_file(temp_file)

# Auto-cleanup on FSA destruction or manual cleanup
fsa.temp_manager.cleanup()

# Using context manager (auto-cleanup)
with FileHandlerFSA() as fsa:
    temp = fsa.create_temp()
    # ... use temp file ...
# Automatically cleaned up here
```

### Directory Traversal

```python
# Find all Python files (non-recursive)
py_files = fsa.traverse(
    Path("src/"),
    pattern="*.py",
    recursive=False
)

# Find all JSON files recursively
json_files = fsa.traverse(
    Path("data/"),
    pattern="*.json",
    recursive=True
)

# Find with multiple operations
for file_path in fsa.traverse(Path("logs/"), pattern="*.log", recursive=True):
    metadata = fsa.get_metadata(file_path)
    print(f"{file_path}: {metadata.size} bytes")
```

### Metadata Extraction

```python
metadata = fsa.get_metadata(Path("document.pdf"))

print(f"Size: {metadata.size} bytes")
print(f"Created: {metadata.created}")
print(f"Modified: {metadata.modified}")
print(f"Permissions: {metadata.permissions}")
print(f"Checksum: {metadata.checksum}")
print(f"Is file: {metadata.is_file}")
print(f"Is directory: {metadata.is_dir}")
```

### Using Execute Method

```python
# Generic execute interface
result = fsa.execute(
    operation=FileOperation.WRITE,
    path="output.json",
    data={"status": "success"},
    format=FileFormat.JSON,
    atomic=True
)

# Read operation
content = fsa.execute(
    operation=FileOperation.READ,
    path="output.json",
    format=FileFormat.JSON
)

# Compress operation
compressed = fsa.execute(
    operation=FileOperation.COMPRESS,
    path="large_file.txt",
    algorithm=CompressionAlgorithm.GZIP
)
```

## Architecture

### Class Structure

- **FileHandlerFSA**: Main orchestrator
- **FileReader**: Multi-format reading with streaming
- **FileWriter**: Atomic writes with backup
- **FileWatcher**: Change detection with callbacks
- **FileLocker**: Concurrent access coordination
- **FileCompressor**: Compression/decompression
- **FileEncryptor**: Encryption/decryption
- **FileMMapper**: Memory-mapped operations
- **TempFileManager**: Temporary file lifecycle
- **PathNavigator**: Directory traversal utilities

### Error Handling

The FSA provides specific exceptions for different error scenarios:

```python
from agno.fsas.infrastructure.file_handler_fsa import (
    FileHandlerError,
    FileNotFoundError,
    PermissionError,
    EncodingError,
    CompressionError,
    EncryptionError,
    LockTimeoutError,
    DiskSpaceError
)

try:
    fsa.read(Path("missing_file.txt"))
except FileNotFoundError as e:
    print(f"File not found: {e}")

try:
    fsa.lock(Path("locked.txt"), timeout=1.0)
except LockTimeoutError as e:
    print(f"Could not acquire lock: {e}")
```

## Advanced Examples

### Parallel File Processing with Locking

```python
import threading

def process_file(file_path, fsa):
    try:
        # Acquire lock
        fsa.lock(file_path, mode=LockMode.EXCLUSIVE, timeout=5.0)

        # Read and process
        data = fsa.read(file_path, format=FileFormat.JSON)
        data['processed'] = True
        data['timestamp'] = str(datetime.now())

        # Write back
        fsa.write(file_path, data, format=FileFormat.JSON, atomic=True)

    finally:
        fsa.unlock(file_path)

# Process files in parallel
threads = []
for file_path in file_list:
    t = threading.Thread(target=process_file, args=(file_path, fsa))
    t.start()
    threads.append(t)

for t in threads:
    t.join()
```

### Incremental Backup System

```python
from datetime import datetime

def create_incremental_backup(source_file, fsa):
    # Get current checksum
    metadata = fsa.get_metadata(source_file)
    current_checksum = metadata.checksum

    # Check if backup needed
    backup_dir = Path("backups/")
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"{source_file.stem}_{timestamp}{source_file.suffix}"

    # Compress and backup
    compressed = fsa.compress(source_file, algorithm=CompressionAlgorithm.GZIP)
    compressed.rename(backup_file.with_suffix(compressed.suffix))

    return backup_file
```

### Log File Rotation with Compression

```python
def rotate_logs(log_file, fsa, max_size_mb=10):
    metadata = fsa.get_metadata(log_file)
    size_mb = metadata.size / (1024 * 1024)

    if size_mb > max_size_mb:
        # Compress current log
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_file = log_file.with_name(f"{log_file.stem}_{timestamp}.gz")

        fsa.compress(log_file, algorithm=CompressionAlgorithm.GZIP)

        # Clear current log
        fsa.write(log_file, "", format=FileFormat.TEXT)
```

## Performance Tips

1. **Use streaming for large files**: Reduces memory footprint
2. **Enable memory mapping**: Fast for large binary files
3. **Use appropriate compression levels**: Balance speed vs size
4. **Batch operations**: Reduce I/O overhead
5. **Use shared locks when possible**: Better concurrency
6. **Clean up temp files**: Prevent disk space issues

## Requirements

### Required
- Python 3.8+
- PyYAML (for YAML support)

### Optional
- pandas (for Parquet and HDF5 support)
- cryptography (for encryption support)
- zstandard (for ZSTD compression)

## Testing

Run the comprehensive test suite:

```bash
pytest libs/agno/tests/unit/fsas/test_file_handler_fsa.py -v
```

The test suite includes:
- Text, JSON, YAML, XML, CSV, and binary file operations
- Streaming operations for large files
- Atomic writes with rollback
- File watching and change detection
- File locking and concurrent access
- Compression/decompression with multiple algorithms
- Encryption/decryption
- Memory-mapped operations
- Temporary file management
- Directory traversal and pattern matching
- Metadata extraction

## License

Part of the Agno project. See LICENSE for details.
