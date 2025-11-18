"""
Comprehensive tests for Encryption FSA.

This test suite covers all major components:
- Key generation and management
- Encryption and decryption
- Signing and verification
- Certificate management
- File encryption
- Audit logging
- Metrics collection
- Security features
"""

import base64
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path

import pytest

from agno.fsas.infrastructure.encryption_fsa import (
    AuditLogger,
    CertificateManager,
    CryptoKey,
    CryptoOperations,
    DecryptionResult,
    EncryptionAlgorithm,
    EncryptionEngine,
    EncryptionFSA,
    EncryptionMetadata,
    EncryptionResult,
    FileEncryption,
    FSAState,
    HashAlgorithm,
    KeyDerivationFunction,
    KeyManager,
    KeyType,
    SecurityUtils,
    SignatureAlgorithm,
)


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def key_manager(temp_storage):
    """Create a key manager instance."""
    return KeyManager(temp_storage)


@pytest.fixture
def encryption_engine(key_manager):
    """Create an encryption engine instance."""
    return EncryptionEngine(key_manager)


@pytest.fixture
def crypto_ops(key_manager):
    """Create a crypto operations instance."""
    return CryptoOperations(key_manager)


@pytest.fixture
def cert_manager(key_manager):
    """Create a certificate manager instance."""
    return CertificateManager(key_manager)


@pytest.fixture
def encryption_fsa(temp_storage):
    """Create an encryption FSA instance."""
    return EncryptionFSA(storage_path=temp_storage, enable_audit=True, enable_metrics=True)


# ============================================================================
# SECURITY UTILS TESTS
# ============================================================================


class TestSecurityUtils:
    """Tests for security utility functions."""

    def test_constant_time_compare(self):
        """Test constant-time comparison."""
        a = b"test123"
        b = b"test123"
        c = b"test456"

        assert SecurityUtils.constant_time_compare(a, b) is True
        assert SecurityUtils.constant_time_compare(a, c) is False

    def test_secure_random_bytes(self):
        """Test secure random byte generation."""
        random1 = SecurityUtils.secure_random_bytes(32)
        random2 = SecurityUtils.secure_random_bytes(32)

        assert len(random1) == 32
        assert len(random2) == 32
        assert random1 != random2

    def test_secure_random_int(self):
        """Test secure random integer generation."""
        for _ in range(100):
            rand_int = SecurityUtils.secure_random_int(1, 100)
            assert 1 <= rand_int <= 100

    def test_wipe_memory(self):
        """Test memory wiping."""
        data = bytearray(b"sensitive data")
        SecurityUtils.wipe_memory(data)
        assert data == bytearray(len(data))

    def test_collect_entropy(self):
        """Test entropy collection."""
        entropy = SecurityUtils.collect_entropy()
        assert len(entropy) > 0
        assert isinstance(entropy, bytes)


# ============================================================================
# KEY MANAGER TESTS
# ============================================================================


class TestKeyManager:
    """Tests for key management system."""

    def test_generate_aes_key(self, key_manager):
        """Test AES key generation."""
        key = key_manager.generate_key(EncryptionAlgorithm.AES_256_GCM)

        assert key.key_id is not None
        assert key.key_type == KeyType.SYMMETRIC
        assert key.algorithm == EncryptionAlgorithm.AES_256_GCM.value
        assert len(key.key_data) == 32

    def test_generate_rsa_key(self, key_manager):
        """Test RSA key generation."""
        key = key_manager.generate_key(EncryptionAlgorithm.RSA_4096)

        assert key.key_id is not None
        assert key.key_type == KeyType.ASYMMETRIC_PRIVATE
        assert key.algorithm == EncryptionAlgorithm.RSA_4096.value
        assert len(key.key_data) > 0

    def test_generate_chacha20_key(self, key_manager):
        """Test ChaCha20 key generation."""
        key = key_manager.generate_key(EncryptionAlgorithm.CHACHA20_POLY1305)

        assert key.key_id is not None
        assert key.key_type == KeyType.SYMMETRIC
        assert len(key.key_data) == 32

    def test_key_expiration(self, key_manager):
        """Test key expiration."""
        key = key_manager.generate_key(
            EncryptionAlgorithm.AES_256_GCM,
            expires_in=1
        )

        assert not key.is_expired()
        time.sleep(2)
        assert key.is_expired()

    def test_get_key(self, key_manager):
        """Test key retrieval."""
        key = key_manager.generate_key(EncryptionAlgorithm.AES_256_GCM)
        retrieved_key = key_manager.get_key(key.key_id)

        assert retrieved_key.key_id == key.key_id
        assert retrieved_key.algorithm == key.algorithm

    def test_key_not_found(self, key_manager):
        """Test key not found error."""
        with pytest.raises(KeyError):
            key_manager.get_key("nonexistent-key-id")

    def test_derive_key_pbkdf2_sha256(self, key_manager):
        """Test key derivation with PBKDF2-SHA256."""
        password = "test_password_123"
        derived_key, salt = key_manager.derive_key(
            password,
            kdf=KeyDerivationFunction.PBKDF2_SHA256
        )

        assert len(derived_key) == 32
        assert len(salt) == 16

        # Verify same password produces same key with same salt
        derived_key2, _ = key_manager.derive_key(
            password,
            salt=salt,
            kdf=KeyDerivationFunction.PBKDF2_SHA256
        )
        assert derived_key == derived_key2

    def test_derive_key_scrypt(self, key_manager):
        """Test key derivation with scrypt."""
        password = "test_password_456"
        derived_key, salt = key_manager.derive_key(
            password,
            kdf=KeyDerivationFunction.SCRYPT
        )

        assert len(derived_key) == 32
        assert len(salt) == 16

    def test_key_rotation(self, key_manager):
        """Test key rotation."""
        original_key = key_manager.generate_key(EncryptionAlgorithm.AES_256_GCM)
        original_key_id = original_key.key_id

        rotated_key = key_manager.rotate_key(original_key_id)

        assert rotated_key.key_id == original_key_id
        assert rotated_key.version == original_key.version + 1
        assert rotated_key.key_data != original_key.key_data

    def test_import_key(self, key_manager):
        """Test key import."""
        key_data = SecurityUtils.secure_random_bytes(32)
        imported_key = key_manager.import_key(
            key_data,
            EncryptionAlgorithm.AES_256_GCM,
            key_id="imported-key"
        )

        assert imported_key.key_id == "imported-key"
        assert imported_key.key_data == key_data

    def test_export_key(self, key_manager):
        """Test key export."""
        key = key_manager.generate_key(EncryptionAlgorithm.AES_256_GCM)
        exported_data = key_manager.export_key(key.key_id)

        assert len(exported_data) == 32
        assert isinstance(exported_data, bytes)

    def test_delete_key(self, key_manager):
        """Test key deletion."""
        key = key_manager.generate_key(EncryptionAlgorithm.AES_256_GCM)
        key_id = key.key_id

        key_manager.delete_key(key_id)

        with pytest.raises(KeyError):
            key_manager.get_key(key_id)

    def test_list_keys(self, key_manager):
        """Test listing all keys."""
        key1 = key_manager.generate_key(EncryptionAlgorithm.AES_256_GCM)
        key2 = key_manager.generate_key(EncryptionAlgorithm.CHACHA20_POLY1305)

        keys = key_manager.list_keys()

        assert len(keys) >= 2
        key_ids = [k["key_id"] for k in keys]
        assert key1.key_id in key_ids
        assert key2.key_id in key_ids


# ============================================================================
# ENCRYPTION ENGINE TESTS
# ============================================================================


class TestEncryptionEngine:
    """Tests for encryption engine."""

    def test_encrypt_decrypt_aes_gcm(self, encryption_engine, key_manager):
        """Test AES-GCM encryption and decryption."""
        key = key_manager.generate_key(EncryptionAlgorithm.AES_256_GCM)
        plaintext = "Hello, World! This is a test message."

        # Encrypt
        result = encryption_engine.encrypt(plaintext, key.key_id)
        assert result.success is True
        assert len(result.ciphertext) > 0

        # Decrypt
        decryption_result = encryption_engine.decrypt(result.ciphertext, result.metadata)
        assert decryption_result.success is True
        assert decryption_result.plaintext == plaintext.encode('utf-8')

    def test_encrypt_decrypt_aes_cbc(self, encryption_engine, key_manager):
        """Test AES-CBC encryption and decryption."""
        key = key_manager.generate_key(EncryptionAlgorithm.AES_256_CBC)
        plaintext = b"Binary data to encrypt"

        # Encrypt
        result = encryption_engine.encrypt(plaintext, key.key_id)
        assert result.success is True

        # Decrypt
        decryption_result = encryption_engine.decrypt(result.ciphertext, result.metadata)
        assert decryption_result.success is True
        assert decryption_result.plaintext == plaintext

    def test_encrypt_decrypt_aes_ctr(self, encryption_engine, key_manager):
        """Test AES-CTR encryption and decryption."""
        key = key_manager.generate_key(EncryptionAlgorithm.AES_256_CTR)
        plaintext = "Counter mode encryption test"

        # Encrypt
        result = encryption_engine.encrypt(plaintext, key.key_id)
        assert result.success is True

        # Decrypt
        decryption_result = encryption_engine.decrypt(result.ciphertext, result.metadata)
        assert decryption_result.success is True
        assert decryption_result.plaintext == plaintext.encode('utf-8')

    def test_encrypt_decrypt_chacha20(self, encryption_engine, key_manager):
        """Test ChaCha20-Poly1305 encryption and decryption."""
        key = key_manager.generate_key(EncryptionAlgorithm.CHACHA20_POLY1305)
        plaintext = "ChaCha20 encryption test"

        # Encrypt
        result = encryption_engine.encrypt(plaintext, key.key_id)
        assert result.success is True

        # Decrypt
        decryption_result = encryption_engine.decrypt(result.ciphertext, result.metadata)
        assert decryption_result.success is True
        assert decryption_result.plaintext == plaintext.encode('utf-8')

    def test_encrypt_with_additional_data(self, encryption_engine, key_manager):
        """Test authenticated encryption with additional data."""
        key = key_manager.generate_key(EncryptionAlgorithm.AES_256_GCM)
        plaintext = "Message with additional data"
        additional_data = b"metadata"

        # Encrypt
        result = encryption_engine.encrypt(
            plaintext,
            key.key_id,
            additional_data=additional_data
        )
        assert result.success is True

        # Decrypt with correct additional data
        decryption_result = encryption_engine.decrypt(
            result.ciphertext,
            result.metadata,
            additional_data=additional_data
        )
        assert decryption_result.success is True

        # Decrypt with wrong additional data should fail
        decryption_result = encryption_engine.decrypt(
            result.ciphertext,
            result.metadata,
            additional_data=b"wrong"
        )
        assert decryption_result.success is False

    def test_encrypt_large_data(self, encryption_engine, key_manager):
        """Test encryption of large data."""
        key = key_manager.generate_key(EncryptionAlgorithm.AES_256_GCM)
        plaintext = b"x" * (1024 * 1024)  # 1 MB

        # Encrypt
        result = encryption_engine.encrypt(plaintext, key.key_id)
        assert result.success is True

        # Decrypt
        decryption_result = encryption_engine.decrypt(result.ciphertext, result.metadata)
        assert decryption_result.success is True
        assert decryption_result.plaintext == plaintext

    def test_encryption_timing(self, encryption_engine, key_manager):
        """Test encryption timing metrics."""
        key = key_manager.generate_key(EncryptionAlgorithm.AES_256_GCM)

        # Perform some encryptions
        for _ in range(5):
            encryption_engine.encrypt("test data", key.key_id)

        avg_time = encryption_engine.get_average_encryption_time()
        assert avg_time > 0


# ============================================================================
# CRYPTO OPERATIONS TESTS
# ============================================================================


class TestCryptoOperations:
    """Tests for cryptographic operations."""

    def test_sign_verify_rsa_pss(self, crypto_ops, key_manager):
        """Test RSA-PSS signing and verification."""
        key = key_manager.generate_key(EncryptionAlgorithm.RSA_4096)
        data = b"Data to sign"

        # Sign
        sign_result = crypto_ops.sign(data, key.key_id, SignatureAlgorithm.RSA_PSS)
        assert sign_result.success is True
        assert len(sign_result.signature) > 0

        # Verify
        verify_result = crypto_ops.verify(
            data,
            sign_result.signature,
            key.key_id,
            SignatureAlgorithm.RSA_PSS
        )
        assert verify_result.valid is True

    def test_verify_invalid_signature(self, crypto_ops, key_manager):
        """Test verification of invalid signature."""
        key = key_manager.generate_key(EncryptionAlgorithm.RSA_4096)
        data = b"Data to sign"

        # Sign
        sign_result = crypto_ops.sign(data, key.key_id, SignatureAlgorithm.RSA_PSS)

        # Verify with modified data
        verify_result = crypto_ops.verify(
            b"Modified data",
            sign_result.signature,
            key.key_id,
            SignatureAlgorithm.RSA_PSS
        )
        assert verify_result.valid is False

    def test_hash_sha256(self, crypto_ops):
        """Test SHA-256 hashing."""
        data = b"Data to hash"
        hash_digest = crypto_ops.hash_data(data, HashAlgorithm.SHA256)

        # Verify against known hash
        expected = hashlib.sha256(data).digest()
        assert hash_digest == expected

    def test_hash_sha512(self, crypto_ops):
        """Test SHA-512 hashing."""
        data = b"Data to hash"
        hash_digest = crypto_ops.hash_data(data, HashAlgorithm.SHA512)

        expected = hashlib.sha512(data).digest()
        assert hash_digest == expected

    def test_hmac(self, crypto_ops, key_manager):
        """Test HMAC generation."""
        key = key_manager.generate_key(EncryptionAlgorithm.AES_256_GCM)
        data = b"Data to authenticate"

        hmac_digest = crypto_ops.hmac(data, key.key_id, HashAlgorithm.SHA256)
        assert len(hmac_digest) == 32

        # Verify HMAC is deterministic
        hmac_digest2 = crypto_ops.hmac(data, key.key_id, HashAlgorithm.SHA256)
        assert hmac_digest == hmac_digest2

    def test_password_hash_bcrypt(self, crypto_ops):
        """Test bcrypt password hashing."""
        try:
            password = "test_password_123"
            hashed = crypto_ops.password_hash(password, algorithm="bcrypt")

            assert len(hashed) > 0
            assert hashed.startswith("$2b$")
        except ImportError:
            pytest.skip("bcrypt not available")

    def test_password_hash_scrypt(self, crypto_ops):
        """Test scrypt password hashing."""
        password = "test_password_456"
        hashed = crypto_ops.password_hash(password, algorithm="scrypt")

        assert len(hashed) > 0
        # Should be base64 encoded
        assert base64.b64decode(hashed)


# ============================================================================
# CERTIFICATE MANAGER TESTS
# ============================================================================


class TestCertificateManager:
    """Tests for certificate management."""

    def test_generate_self_signed_certificate(self, cert_manager, key_manager):
        """Test self-signed certificate generation."""
        key = key_manager.generate_key(EncryptionAlgorithm.RSA_2048)
        cert_pem = cert_manager.generate_self_signed_certificate(
            key.key_id,
            "test.example.com",
            validity_days=365
        )

        assert b"BEGIN CERTIFICATE" in cert_pem
        assert b"END CERTIFICATE" in cert_pem

    def test_generate_csr(self, cert_manager, key_manager):
        """Test CSR generation."""
        key = key_manager.generate_key(EncryptionAlgorithm.RSA_2048)
        csr_pem = cert_manager.generate_csr(
            key.key_id,
            "test.example.com",
            san_dns=["www.example.com", "api.example.com"]
        )

        assert b"BEGIN CERTIFICATE REQUEST" in csr_pem
        assert b"END CERTIFICATE REQUEST" in csr_pem

    def test_parse_certificate(self, cert_manager, key_manager):
        """Test certificate parsing."""
        key = key_manager.generate_key(EncryptionAlgorithm.RSA_2048)
        cert_pem = cert_manager.generate_self_signed_certificate(
            key.key_id,
            "test.example.com"
        )

        cert_info = cert_manager.parse_certificate(cert_pem)

        assert "subject" in cert_info
        assert "issuer" in cert_info
        assert "serial_number" in cert_info
        assert "not_valid_before" in cert_info
        assert "not_valid_after" in cert_info

    def test_validate_certificate(self, cert_manager, key_manager):
        """Test certificate validation."""
        key = key_manager.generate_key(EncryptionAlgorithm.RSA_2048)
        cert_pem = cert_manager.generate_self_signed_certificate(
            key.key_id,
            "test.example.com",
            validity_days=365
        )

        is_valid = cert_manager.validate_certificate(cert_pem)
        assert is_valid is True

    def test_check_expiration(self, cert_manager, key_manager):
        """Test certificate expiration check."""
        key = key_manager.generate_key(EncryptionAlgorithm.RSA_2048)
        cert_pem = cert_manager.generate_self_signed_certificate(
            key.key_id,
            "test.example.com",
            validity_days=365
        )

        expiration_info = cert_manager.check_expiration(cert_pem)

        assert expiration_info["expired"] is False
        assert expiration_info["days_until_expiry"] > 0
        assert "not_valid_after" in expiration_info


# ============================================================================
# FILE ENCRYPTION TESTS
# ============================================================================


class TestFileEncryption:
    """Tests for file encryption."""

    def test_encrypt_decrypt_file(self, encryption_engine, key_manager, temp_storage):
        """Test file encryption and decryption."""
        file_encryption = FileEncryption(encryption_engine)

        # Create test file
        input_file = temp_storage / "test_input.txt"
        encrypted_file = temp_storage / "test_encrypted.bin"
        decrypted_file = temp_storage / "test_decrypted.txt"

        test_data = "This is test file content.\nMultiple lines.\nWith various data."
        input_file.write_text(test_data)

        # Generate key
        key = key_manager.generate_key(EncryptionAlgorithm.AES_256_GCM)

        # Encrypt file
        encrypt_result = file_encryption.encrypt_file(
            input_file,
            encrypted_file,
            key.key_id
        )
        assert encrypt_result.success is True
        assert encrypted_file.exists()

        # Decrypt file
        decrypt_result = file_encryption.decrypt_file(
            encrypted_file,
            decrypted_file
        )
        assert decrypt_result.success is True
        assert decrypted_file.exists()

        # Verify content
        decrypted_data = decrypted_file.read_text()
        assert decrypted_data == test_data

    def test_encrypt_large_file(self, encryption_engine, key_manager, temp_storage):
        """Test encryption of large file."""
        file_encryption = FileEncryption(encryption_engine)

        # Create large test file
        input_file = temp_storage / "large_input.bin"
        encrypted_file = temp_storage / "large_encrypted.bin"

        large_data = b"x" * (1024 * 1024)  # 1 MB
        input_file.write_bytes(large_data)

        # Generate key
        key = key_manager.generate_key(EncryptionAlgorithm.AES_256_GCM)

        # Encrypt file
        encrypt_result = file_encryption.encrypt_file(
            input_file,
            encrypted_file,
            key.key_id
        )
        assert encrypt_result.success is True


# ============================================================================
# AUDIT LOGGER TESTS
# ============================================================================


class TestAuditLogger:
    """Tests for audit logging."""

    def test_log_event(self, temp_storage):
        """Test logging security events."""
        audit_logger = AuditLogger(temp_storage / "audit.log")

        audit_logger.log_event(
            event_type="encryption",
            success=True,
            key_id="test-key-123",
            algorithm="aes-256-gcm"
        )

        events = audit_logger.get_recent_events(1)
        assert len(events) == 1
        assert events[0]["event_type"] == "encryption"
        assert events[0]["success"] is True
        assert events[0]["key_id"] == "test-key-123"

    def test_query_events(self, temp_storage):
        """Test querying audit events."""
        audit_logger = AuditLogger(temp_storage / "audit.log")

        # Log multiple events
        audit_logger.log_event("encryption", success=True, user_id="user1")
        audit_logger.log_event("decryption", success=True, user_id="user2")
        audit_logger.log_event("encryption", success=False, user_id="user1")

        # Query by event type
        encryption_events = audit_logger.query_events(event_type="encryption")
        assert len(encryption_events) == 2

        # Query by user
        user1_events = audit_logger.query_events(user_id="user1")
        assert len(user1_events) == 2


# ============================================================================
# ENCRYPTION FSA INTEGRATION TESTS
# ============================================================================


class TestEncryptionFSA:
    """Integration tests for Encryption FSA."""

    def test_initialization(self, encryption_fsa):
        """Test FSA initialization."""
        assert encryption_fsa.state == FSAState.IDLE
        assert encryption_fsa.key_manager is not None
        assert encryption_fsa.encryption_engine is not None
        assert encryption_fsa.crypto_ops is not None
        assert encryption_fsa.cert_manager is not None

    def test_generate_key(self, encryption_fsa):
        """Test key generation through FSA."""
        key = encryption_fsa.generate_key(EncryptionAlgorithm.AES_256_GCM)

        assert key.key_id is not None
        assert encryption_fsa.state == FSAState.COMPLETED

    def test_encrypt_decrypt_flow(self, encryption_fsa):
        """Test complete encryption/decryption flow."""
        # Generate key
        key = encryption_fsa.generate_key(EncryptionAlgorithm.AES_256_GCM)

        # Encrypt
        plaintext = "Test message for FSA"
        encrypt_result = encryption_fsa.encrypt(plaintext, key.key_id)

        assert encrypt_result.success is True
        assert encryption_fsa.state == FSAState.COMPLETED

        # Decrypt
        decrypt_result = encryption_fsa.decrypt(
            encrypt_result.ciphertext,
            encrypt_result.metadata
        )

        assert decrypt_result.success is True
        assert decrypt_result.plaintext == plaintext.encode('utf-8')
        assert encryption_fsa.state == FSAState.COMPLETED

    def test_sign_verify_flow(self, encryption_fsa):
        """Test signing and verification flow."""
        # Generate key
        key = encryption_fsa.generate_key(EncryptionAlgorithm.RSA_2048)

        # Sign
        data = b"Data to sign"
        sign_result = encryption_fsa.sign(data, key.key_id)

        assert sign_result.success is True
        assert encryption_fsa.state == FSAState.COMPLETED

        # Verify
        verify_result = encryption_fsa.verify(
            data,
            sign_result.signature,
            key.key_id
        )

        assert verify_result.valid is True
        assert encryption_fsa.state == FSAState.COMPLETED

    def test_key_rotation_flow(self, encryption_fsa):
        """Test key rotation flow."""
        # Generate original key
        original_key = encryption_fsa.generate_key(EncryptionAlgorithm.AES_256_GCM)
        original_key_id = original_key.key_id

        # Rotate key
        rotated_key = encryption_fsa.rotate_key(original_key_id)

        assert rotated_key.key_id == original_key_id
        assert rotated_key.version > original_key.version
        assert encryption_fsa.state == FSAState.COMPLETED

    def test_metrics_collection(self, encryption_fsa):
        """Test metrics collection."""
        key = encryption_fsa.generate_key(EncryptionAlgorithm.AES_256_GCM)

        # Perform operations
        encryption_fsa.encrypt("test1", key.key_id)
        encryption_fsa.encrypt("test2", key.key_id)

        # Get metrics
        metrics = encryption_fsa.get_metrics()

        assert metrics["total_encryptions"] >= 2
        assert metrics["total_key_generations"] >= 1
        assert metrics["bytes_encrypted"] > 0

    def test_audit_logging(self, encryption_fsa):
        """Test audit logging."""
        key = encryption_fsa.generate_key(EncryptionAlgorithm.AES_256_GCM)
        encryption_fsa.encrypt("test", key.key_id)

        # Get audit log
        audit_log = encryption_fsa.get_audit_log()

        assert len(audit_log) >= 2  # key generation + encryption
        assert any(e["event_type"] == "key_generation" for e in audit_log)
        assert any(e["event_type"] == "encryption" for e in audit_log)

    def test_state_transitions(self, encryption_fsa):
        """Test FSA state transitions."""
        assert encryption_fsa.get_state() == FSAState.IDLE.value

        key = encryption_fsa.generate_key(EncryptionAlgorithm.AES_256_GCM)
        assert encryption_fsa.get_state() == FSAState.COMPLETED.value

        encryption_fsa.encrypt("test", key.key_id)
        assert encryption_fsa.get_state() == FSAState.COMPLETED.value

        # Check state history
        history = encryption_fsa.get_state_history()
        assert len(history) > 0

    def test_multiple_algorithms(self, encryption_fsa):
        """Test multiple encryption algorithms."""
        algorithms = [
            EncryptionAlgorithm.AES_256_GCM,
            EncryptionAlgorithm.AES_256_CBC,
            EncryptionAlgorithm.AES_256_CTR,
            EncryptionAlgorithm.CHACHA20_POLY1305,
        ]

        plaintext = "Test data for multiple algorithms"

        for algorithm in algorithms:
            key = encryption_fsa.generate_key(algorithm)
            encrypt_result = encryption_fsa.encrypt(plaintext, key.key_id)

            assert encrypt_result.success is True

            decrypt_result = encryption_fsa.decrypt(
                encrypt_result.ciphertext,
                encrypt_result.metadata
            )

            assert decrypt_result.success is True
            assert decrypt_result.plaintext == plaintext.encode('utf-8')

    def test_concurrent_operations(self, encryption_fsa):
        """Test concurrent encryption operations."""
        import threading

        key = encryption_fsa.generate_key(EncryptionAlgorithm.AES_256_GCM)
        results = []

        def encrypt_data(index):
            result = encryption_fsa.encrypt(f"test{index}", key.key_id)
            results.append(result)

        threads = []
        for i in range(10):
            thread = threading.Thread(target=encrypt_data, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert len(results) == 10
        assert all(r.success for r in results)

    def test_error_handling(self, encryption_fsa):
        """Test error handling."""
        # Try to encrypt with non-existent key
        result = encryption_fsa.encrypt("test", "nonexistent-key-id")

        assert result.success is False
        assert result.error is not None
        assert encryption_fsa.state == FSAState.ERROR


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================


class TestPerformance:
    """Performance tests for encryption operations."""

    def test_encryption_performance(self, encryption_fsa):
        """Test encryption performance."""
        key = encryption_fsa.generate_key(EncryptionAlgorithm.AES_256_GCM)

        start_time = time.time()
        iterations = 100

        for i in range(iterations):
            encryption_fsa.encrypt(f"test message {i}", key.key_id)

        elapsed = time.time() - start_time
        ops_per_second = iterations / elapsed

        print(f"\nEncryption performance: {ops_per_second:.2f} ops/sec")
        assert ops_per_second > 100  # Should handle at least 100 ops/sec

    def test_key_generation_performance(self, encryption_fsa):
        """Test key generation performance."""
        start_time = time.time()
        iterations = 10

        for _ in range(iterations):
            encryption_fsa.generate_key(EncryptionAlgorithm.AES_256_GCM)

        elapsed = time.time() - start_time
        ops_per_second = iterations / elapsed

        print(f"\nKey generation performance: {ops_per_second:.2f} ops/sec")
        assert ops_per_second > 10  # Should handle at least 10 key generations/sec
