#!/usr/bin/env python3
"""Local-only Character Sheet companion: a bounded MCP bridge and sheet host.

Run ``serve`` to host one chosen HTML file and its separate private state on
127.0.0.1. Run ``mcp`` from a desktop AI's local-MCP configuration.  The MCP
server never reads arbitrary files, opens a public listener, or accepts raw
state replacement.  It accepts small JSON-Patch-like operations, records every
accepted revision, and can undo a revision.
"""

from __future__ import annotations

import argparse
import base64
import copy
import ctypes
import fcntl
import getpass
import hashlib
import json
import os
import re
import secrets
import shutil
import sys
import tempfile
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from contextlib import contextmanager
from urllib.parse import parse_qs, urlparse

MAX_BODY = 256_000
MAX_OPERATIONS = 20
MAX_HISTORY = 30
LOCK = threading.RLock()
HOSTED_PAGES: dict[tuple[str, str], tuple[ThreadingHTTPServer, str, threading.Thread]] = {}
ENCRYPTED_FORMAT = "character-sheet-encrypted-drive-v1"
ENCRYPTED_AAD = ENCRYPTED_FORMAT.encode("ascii")
DESTRUCTIVE_CONFIRMATION = "I CONFIRM DELETE OR BULK CHANGE"
DEFAULT_KEYCHAIN_ACCOUNT = "character-sheet"
DEFAULT_SCHEMA_NAMESPACE = "_characterSheet"


class BridgeError(ValueError):
    pass


class EncryptedStoreError(BridgeError):
    pass


def json_clone(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _b64encode(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _b64decode(value: Any, field: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise EncryptedStoreError(f"Encrypted Character Sheet {field} is missing.")
    try:
        return base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as error:
        raise EncryptedStoreError(f"Encrypted Character Sheet {field} is invalid.") from error


def validate_drive_document(document: Any, namespace_key: str = DEFAULT_SCHEMA_NAMESPACE) -> dict[str, Any]:
    """Retain the existing canonical Drive envelope check inside the proof."""
    if not isinstance(document, dict):
        raise EncryptedStoreError("Character Sheet state must be a JSON object.")
    if not isinstance(namespace_key, str) or not namespace_key.startswith("_"):
        raise EncryptedStoreError("Character Sheet schema namespace is invalid.")
    namespace = document.get(namespace_key)
    if not isinstance(namespace, dict) or namespace.get("schemaVersion") != 1:
        raise EncryptedStoreError("Character Sheet state requires namespace schemaVersion 1.")
    if not isinstance(namespace.get("liveContext"), dict):
        raise EncryptedStoreError("Character Sheet state requires the namespace liveContext feed.")
    return document


def encrypt_drive_document(
    document: dict[str, Any], passphrase: str, namespace_key: str = DEFAULT_SCHEMA_NAMESPACE,
) -> dict[str, Any]:
    """Encrypt a complete canonical document before it reaches the Drive adapter."""
    if not isinstance(passphrase, str) or not passphrase:
        raise EncryptedStoreError("A non-empty recovery passphrase is required.")
    validate_drive_document(document, namespace_key)
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as error:
        raise EncryptedStoreError("The encrypted proof requires the cryptography package.") from error
    salt = os.urandom(16)
    nonce = os.urandom(12)
    n, r, p = 2**14, 8, 1
    key = hashlib.scrypt(passphrase.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=32)
    ciphertext = AESGCM(key).encrypt(nonce, _canonical_json_bytes(document), ENCRYPTED_AAD)
    return {
        "_characterSheetEncrypted": {
            "format": ENCRYPTED_FORMAT,
            "kdf": {"name": "scrypt", "salt": _b64encode(salt), "n": n, "r": r, "p": p},
            "cipher": {"name": "AES-256-GCM", "nonce": _b64encode(nonce), "ciphertext": _b64encode(ciphertext)},
        }
    }


def decrypt_drive_document(
    envelope: Any, passphrase: str, namespace_key: str = DEFAULT_SCHEMA_NAMESPACE,
) -> dict[str, Any]:
    """Authenticate, decrypt, parse, and revalidate a Drive envelope in memory."""
    if not isinstance(envelope, dict) or set(envelope) != {"_characterSheetEncrypted"}:
        raise EncryptedStoreError("Drive object is not an encrypted Character Sheet envelope.")
    wrapper = envelope["_characterSheetEncrypted"]
    if not isinstance(wrapper, dict) or wrapper.get("format") != ENCRYPTED_FORMAT:
        raise EncryptedStoreError("Encrypted Character Sheet format is unsupported.")
    kdf = wrapper.get("kdf")
    cipher = wrapper.get("cipher")
    if not isinstance(kdf, dict) or kdf.get("name") != "scrypt":
        raise EncryptedStoreError("Encrypted Character Sheet KDF is unsupported.")
    if not isinstance(cipher, dict) or cipher.get("name") != "AES-256-GCM":
        raise EncryptedStoreError("Encrypted Character Sheet cipher is unsupported.")
    try:
        n, r, p = int(kdf["n"]), int(kdf["r"]), int(kdf["p"])
    except (KeyError, TypeError, ValueError) as error:
        raise EncryptedStoreError("Encrypted Character Sheet KDF parameters are invalid.") from error
    if (n, r, p) != (2**14, 8, 1):
        raise EncryptedStoreError("Encrypted Character Sheet KDF parameters are not accepted by this proof.")
    salt = _b64decode(kdf.get("salt"), "salt")
    nonce = _b64decode(cipher.get("nonce"), "nonce")
    ciphertext = _b64decode(cipher.get("ciphertext"), "ciphertext")
    try:
        from cryptography.exceptions import InvalidTag
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        key = hashlib.scrypt(passphrase.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=32)
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, ENCRYPTED_AAD)
    except (InvalidTag, ValueError, TypeError) as error:
        raise EncryptedStoreError("Wrong passphrase or encrypted Character Sheet data was altered.") from error
    try:
        document = json.loads(plaintext)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise EncryptedStoreError("Decrypted Character Sheet data is invalid JSON.") from error
    return validate_drive_document(document, namespace_key)


class SyntheticDriveFile:
    """A persistent fake Drive object for the isolated encryption proof only."""

    def __init__(self, path: Path):
        self.path = path

    @staticmethod
    def _etag(envelope: dict[str, Any]) -> str:
        return '"' + hashlib.sha256(_canonical_json_bytes(envelope)).hexdigest() + '"'

    def _load(self) -> dict[str, Any]:
        try:
            record = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise EncryptedStoreError("Synthetic Drive object does not exist.") from error
        except (OSError, json.JSONDecodeError) as error:
            raise EncryptedStoreError("Synthetic Drive object is unreadable.") from error
        if not isinstance(record, dict) or not isinstance(record.get("content"), dict):
            raise EncryptedStoreError("Synthetic Drive object is invalid.")
        metadata = record.get("metadata")
        if not isinstance(metadata, dict) or not isinstance(metadata.get("version"), str) or not isinstance(metadata.get("etag"), str):
            raise EncryptedStoreError("Synthetic Drive metadata is invalid.")
        if metadata["etag"] != self._etag(record["content"]):
            raise EncryptedStoreError("Synthetic Drive ETag does not match its encrypted content.")
        return record

    def _write(self, record: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(_canonical_json_bytes(record) + b"\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary_name, 0o600)
            os.replace(temporary_name, self.path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)

    def create(self, envelope: dict[str, Any]) -> dict[str, Any]:
        if self.path.exists():
            raise EncryptedStoreError("Synthetic Drive object already exists.")
        metadata = {"version": "1", "etag": self._etag(envelope)}
        self._write({"metadata": metadata, "content": envelope})
        return dict(metadata)

    def fetch(self) -> tuple[dict[str, Any], dict[str, Any]]:
        record = self._load()
        return json_clone(record["content"]), dict(record["metadata"])

    def update(self, envelope: dict[str, Any], *, expected_version: str, expected_etag: str) -> dict[str, Any]:
        record = self._load()
        metadata = record["metadata"]
        if metadata["version"] != expected_version or metadata["etag"] != expected_etag:
            raise EncryptedStoreError("Conflict: encrypted Drive object changed since it was read.")
        next_metadata = {"version": str(int(metadata["version"]) + 1), "etag": self._etag(envelope)}
        self._write({"metadata": next_metadata, "content": envelope})
        return dict(next_metadata)


class MacOSKeychainUnlock:
    """Optional login-Keychain convenience through the native Security framework."""

    ITEM_NOT_FOUND = -25300

    def __init__(self, service: str, account: str = DEFAULT_KEYCHAIN_ACCOUNT):
        if not service or not account:
            raise EncryptedStoreError("Keychain service and account must not be blank.")
        self.service = service
        self.account = account

    @staticmethod
    def _frameworks() -> tuple[Any, Any]:
        if sys.platform != "darwin":
            raise EncryptedStoreError("macOS Login Keychain is available only on macOS.")
        security = ctypes.CDLL("/System/Library/Frameworks/Security.framework/Security")
        core = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        pointer = ctypes.c_void_p
        security.SecKeychainFindGenericPassword.argtypes = [
            pointer, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_uint32, ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(pointer), ctypes.POINTER(pointer),
        ]
        security.SecKeychainFindGenericPassword.restype = ctypes.c_int32
        security.SecKeychainAddGenericPassword.argtypes = [
            pointer, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_uint32, ctypes.c_char_p,
            ctypes.c_uint32, pointer, ctypes.POINTER(pointer),
        ]
        security.SecKeychainAddGenericPassword.restype = ctypes.c_int32
        security.SecKeychainItemDelete.argtypes = [pointer]
        security.SecKeychainItemDelete.restype = ctypes.c_int32
        security.SecKeychainItemFreeContent.argtypes = [pointer, pointer]
        security.SecKeychainItemFreeContent.restype = ctypes.c_int32
        core.CFRelease.argtypes = [pointer]
        core.CFRelease.restype = None
        return security, core

    def _find_secret_and_item(self) -> tuple[str | None, Any]:
        security, _ = self._frameworks()
        service = self.service.encode("utf-8")
        account = self.account.encode("utf-8")
        secret_length = ctypes.c_uint32()
        secret_data = ctypes.c_void_p()
        item = ctypes.c_void_p()
        status = security.SecKeychainFindGenericPassword(
            None, len(service), service, len(account), account,
            ctypes.byref(secret_length), ctypes.byref(secret_data), ctypes.byref(item),
        )
        if status == self.ITEM_NOT_FOUND:
            return None, None
        if status != 0:
            raise EncryptedStoreError(f"macOS Keychain lookup failed with status {status}.")
        try:
            secret = ctypes.string_at(secret_data, secret_length.value).decode("utf-8")
        except UnicodeDecodeError as error:
            raise EncryptedStoreError("macOS Keychain returned an invalid Character Sheet passphrase.") from error
        finally:
            security.SecKeychainItemFreeContent(None, secret_data)
        return secret, item

    @staticmethod
    def _release_item(item: Any) -> None:
        if item:
            _, core = MacOSKeychainUnlock._frameworks()
            core.CFRelease(item)

    def _delete_item(self, item: Any) -> None:
        security, _ = self._frameworks()
        status = security.SecKeychainItemDelete(item)
        if status != 0:
            raise EncryptedStoreError(f"macOS Keychain delete failed with status {status}.")

    def _add_item(self, passphrase: str) -> None:
        security, core = self._frameworks()
        service = self.service.encode("utf-8")
        account = self.account.encode("utf-8")
        encoded = passphrase.encode("utf-8")
        secret_buffer = ctypes.create_string_buffer(encoded)
        item = ctypes.c_void_p()
        status = security.SecKeychainAddGenericPassword(
            None, len(service), service, len(account), account,
            len(encoded), ctypes.cast(secret_buffer, ctypes.c_void_p), ctypes.byref(item),
        )
        if item:
            core.CFRelease(item)
        if status != 0:
            raise EncryptedStoreError(f"macOS Keychain save failed with status {status}.")

    def remember(self, passphrase: str) -> None:
        if not passphrase:
            raise EncryptedStoreError("Character Sheet recovery passphrase must not be blank.")
        _old_secret, existing = self._find_secret_and_item()
        if existing:
            try:
                self._delete_item(existing)
            finally:
                self._release_item(existing)
        self._add_item(passphrase)

    def unlock(self) -> str:
        secret, item = self._find_secret_and_item()
        try:
            if not secret:
                raise EncryptedStoreError("Character Sheet passphrase is not available from the unlocked macOS Keychain.")
            return secret
        finally:
            self._release_item(item)

    def forget(self) -> None:
        _secret, item = self._find_secret_and_item()
        if not item:
            raise EncryptedStoreError("Character Sheet proof entry is not present in macOS Keychain.")
        try:
            self._delete_item(item)
        finally:
            self._release_item(item)


class EncryptedCharacterSheetInterface:
    """Small local read/write surface suitable for an authorised local AI process."""

    def __init__(
        self,
        drive: SyntheticDriveFile,
        passphrase: str,
        namespace_key: str = DEFAULT_SCHEMA_NAMESPACE,
    ):
        self.drive = drive
        self.passphrase = passphrase
        self.namespace_key = namespace_key

    def initialise(self, document: dict[str, Any]) -> dict[str, Any]:
        return self.drive.create(encrypt_drive_document(document, self.passphrase, self.namespace_key))

    def read(self) -> dict[str, Any]:
        envelope, metadata = self.drive.fetch()
        return {
            "document": decrypt_drive_document(envelope, self.passphrase, self.namespace_key),
            "metadata": metadata,
        }

    def patch(
        self,
        operations: list[dict[str, Any]],
        *,
        expected_version: str,
        expected_etag: str,
        confirmation: str | None = None,
    ) -> dict[str, Any]:
        current = self.read()
        metadata = current["metadata"]
        if metadata["version"] != expected_version or metadata["etag"] != expected_etag:
            raise EncryptedStoreError("Conflict: encrypted Drive object changed since it was read.")
        updated, destructive = apply_operations(current["document"], operations)
        if (destructive or len(operations) > 5) and confirmation != DESTRUCTIVE_CONFIRMATION:
            raise EncryptedStoreError(f"Delete or bulk change requires confirmation exactly {DESTRUCTIVE_CONFIRMATION!r}.")
        validate_drive_document(updated, self.namespace_key)
        next_metadata = self.drive.update(
            encrypt_drive_document(updated, self.passphrase, self.namespace_key),
            expected_version=expected_version,
            expected_etag=expected_etag,
        )
        return {"changed": len(operations), "metadata": next_metadata}


def handle_encrypted_ai_request(interface: EncryptedCharacterSheetInterface, request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise EncryptedStoreError("Local Character Sheet request must be a JSON object.")
    action = request.get("action")
    if action == "read":
        return interface.read()
    if action == "patch":
        return interface.patch(
            request.get("operations"),
            expected_version=request.get("expectedVersion"),
            expected_etag=request.get("expectedEtag"),
            confirmation=request.get("confirmation"),
        )
    raise EncryptedStoreError("Local Character Sheet interface supports only read and patch.")


def run_encrypted_ai_jsonl(interface: EncryptedCharacterSheetInterface) -> None:
    for raw in sys.stdin:
        request: Any = None
        try:
            request = json.loads(raw)
            result = handle_encrypted_ai_request(interface, request)
            print(json.dumps({"id": request.get("id"), "result": result}, ensure_ascii=False), flush=True)
        except (json.JSONDecodeError, EncryptedStoreError) as error:
            request_id = request.get("id") if isinstance(request, dict) else None
            print(json.dumps({"id": request_id, "error": str(error)}, ensure_ascii=False), flush=True)


def load_record(state_path: Path) -> dict[str, Any]:
    if not state_path.exists():
        return {"version": 1, "revision": 0, "state": {}, "history": []}
    try:
        record = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BridgeError(f"Could not read the selected companion state: {error}") from error
    if not isinstance(record, dict) or record.get("version") != 1 or not isinstance(record.get("state"), dict):
        raise BridgeError("The selected companion state is not a valid Character Sheet companion file.")
    record.setdefault("history", [])
    if not isinstance(record["history"], list):
        raise BridgeError("The selected companion history is invalid.")
    return record


def write_record(state_path: Path, record: dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    if state_path.exists():
        # Retain the exact previous revision before replacing the canonical file.
        # A backup failure blocks the new write; backups are never pruned silently.
        previous = load_record(state_path)
        backup_dir = state_path.parent / f".{state_path.name}.backups"
        backup_dir.mkdir(mode=0o700, exist_ok=True)
        backup_path = backup_dir / f"revision-{previous['revision']:012d}.json"
        if backup_path.exists():
            if backup_path.read_bytes() != state_path.read_bytes():
                raise BridgeError("An existing companion backup differs from this revision; saving stopped.")
        else:
            with backup_path.open("xb") as backup:
                os.chmod(backup_path, 0o600)
                with state_path.open("rb") as source:
                    shutil.copyfileobj(source, backup)
                backup.flush()
                os.fsync(backup.fileno())
    fd, temporary_name = tempfile.mkstemp(prefix=".character-sheet-", suffix=".tmp", dir=state_path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(record, handle, ensure_ascii=False, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, state_path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


@contextmanager
def state_file_lock(state_path: Path):
    """Serialise read/modify/write across independent MCP and app processes."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = state_path.parent / f".{state_path.name}.lock"
    with LOCK, lock_path.open("a+b") as handle:
        os.chmod(lock_path, 0o600)
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def pointer_parts(path: str) -> list[str]:
    if not isinstance(path, str) or not path.startswith("/") or path == "/":
        raise BridgeError("Each operation needs a JSON pointer path below a sheet field.")
    parts = [part.replace("~1", "/").replace("~0", "~") for part in path[1:].split("/")]
    if any(not part or part.startswith("_") or part in {"__proto__", "constructor", "prototype"} for part in parts):
        raise BridgeError("That path is not an editable Character Sheet field.")
    return parts


def container_at(state: dict[str, Any], parts: list[str]) -> tuple[Any, str]:
    current: Any = state
    for part in parts[:-1]:
        if isinstance(current, dict):
            if part not in current:
                raise BridgeError(f"Cannot find {part!r} in the current sheet.")
            current = current[part]
        elif isinstance(current, list):
            if not part.isdigit() or int(part) >= len(current):
                raise BridgeError("That list item no longer exists. Read the sheet and try again.")
            current = current[int(part)]
        else:
            raise BridgeError("That path stops before its requested field.")
    return current, parts[-1]


def apply_operations(state: dict[str, Any], operations: list[dict[str, Any]]) -> tuple[dict[str, Any], bool]:
    if not isinstance(operations, list) or not operations or len(operations) > MAX_OPERATIONS:
        raise BridgeError(f"Send between 1 and {MAX_OPERATIONS} small operations.")
    updated = json_clone(state)
    destructive = False
    for operation in operations:
        if not isinstance(operation, dict):
            raise BridgeError("Each operation must be an object.")
        kind = operation.get("op")
        parts = pointer_parts(operation.get("path"))
        parent, key = container_at(updated, parts)
        if kind not in {"add", "replace", "remove"}:
            raise BridgeError("Only add, replace, and remove operations are supported.")
        if kind != "remove":
            value = operation.get("value")
            try:
                encoded = json.dumps(value, ensure_ascii=False)
            except (TypeError, ValueError) as error:
                raise BridgeError("Operation values must be JSON data.") from error
            if len(encoded.encode("utf-8")) > MAX_BODY:
                raise BridgeError("One operation is too large. Split it into smaller changes.")
        if isinstance(parent, dict):
            exists = key in parent
            if kind == "replace":
                if not exists:
                    raise BridgeError("Replace only changes an existing field. Use add for a new field.")
                parent[key] = value
            elif kind == "add":
                if exists:
                    raise BridgeError("Add only creates a new field. Use replace for an existing field.")
                parent[key] = value
            else:
                if not exists:
                    raise BridgeError("That field no longer exists.")
                del parent[key]
                destructive = True
        elif isinstance(parent, list):
            if kind == "add":
                if key == "-":
                    parent.append(value)
                elif key.isdigit() and int(key) <= len(parent):
                    parent.insert(int(key), value)
                else:
                    raise BridgeError("Use /- to add to the end of a list, or a current list index.")
            else:
                if not key.isdigit() or int(key) >= len(parent):
                    raise BridgeError("That list item no longer exists.")
                index = int(key)
                if kind == "replace":
                    parent[index] = value
                else:
                    parent.pop(index)
                    destructive = True
        else:
            raise BridgeError("That operation does not point to a field or list.")
    return updated, destructive


def require_approval(operations: list[dict[str, Any]], destructive: bool, approval: str | None) -> None:
    bulk = len(operations) > 5
    expected = "I CONFIRM DELETE OR BULK CHANGE" if destructive or bulk else "I APPROVE THIS SHEET CHANGE"
    if approval != expected:
        action = "delete or bulk change" if destructive or bulk else "sheet change"
        raise BridgeError(f"Before applying this {action}, get the user's explicit chat confirmation, then call again with approval exactly {expected!r}.")


def commit_operations(state_path: Path, expected_revision: int, operations: list[dict[str, Any]], approval: str | None, source: str) -> dict[str, Any]:
    with state_file_lock(state_path):
        record = load_record(state_path)
        if expected_revision != record["revision"]:
            raise BridgeError(f"Conflict: the sheet is revision {record['revision']}, not {expected_revision}. Read it again before changing it.")
        updated, destructive = apply_operations(record["state"], operations)
        require_approval(operations, destructive, approval)
        record["history"].append({"revision": record["revision"], "state": record["state"], "source": source})
        record["history"] = record["history"][-MAX_HISTORY:]
        record["state"] = updated
        record["revision"] += 1
        write_record(state_path, record)
        return {"revision": record["revision"], "state": updated, "changed": len(operations)}


def replace_from_app(state_path: Path, expected_revision: int, state: Any) -> dict[str, Any]:
    if not isinstance(state, dict):
        raise BridgeError("The companion page supplied an invalid sheet state.")
    encoded = json.dumps(state, ensure_ascii=False)
    if len(encoded.encode("utf-8")) > MAX_BODY:
        raise BridgeError("The sheet is too large for the local companion.")
    with state_file_lock(state_path):
        record = load_record(state_path)
        if expected_revision != record["revision"]:
            raise BridgeError(f"Conflict: the sheet is revision {record['revision']}, not {expected_revision}.")
        record["history"].append({"revision": record["revision"], "state": record["state"], "source": "sheet"})
        record["history"] = record["history"][-MAX_HISTORY:]
        record["state"] = json_clone(state)
        record["revision"] += 1
        write_record(state_path, record)
        return {"revision": record["revision"]}


def tool_result(value: Any) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}]}


def call_tool(state_path: Path, name: str, arguments: dict[str, Any], sheet_path: Path | None = None) -> dict[str, Any]:
    if name == "open_character_sheet":
        if sheet_path is None:
            raise BridgeError("This companion was not configured with its Character Sheet HTML file.")
        url, opened = open_companion_page(sheet_path, state_path)
        return tool_result({"url": url, "opened": opened, "browserConnected": False, "message": "The page is open, but it does not yet read or write the companion state file. Do not treat the browser sheet and companion file as one source of truth."})
    if name == "read_character_sheet":
        record = load_record(state_path)
        return tool_result({
            "revision": record["revision"], "state": record["state"],
            "source": "companion-state-file", "initialised": state_path.is_file(),
            "browserConnected": False,
            "warning": "The companion file is separate from browser storage. This read does not inspect the sheet open in your browser.",
        })
    if name == "apply_character_sheet_update":
        result = commit_operations(state_path, arguments.get("expected_revision"), arguments.get("operations"), arguments.get("approval"), "AI chat")
        return tool_result({"revision": result["revision"], "changed": result["changed"], "browserConnected": False, "message": "Saved to the companion file only. The browser page does not currently refresh from this file."})
    if name == "undo_character_sheet_update":
        expected = arguments.get("expected_revision")
        approval = arguments.get("approval")
        if approval != "I CONFIRM UNDO":
            raise BridgeError("Ask the user to explicitly confirm undo in the chat, then call again with approval exactly 'I CONFIRM UNDO'.")
        with state_file_lock(state_path):
            record = load_record(state_path)
            if expected != record["revision"]:
                raise BridgeError(f"Conflict: the sheet is revision {record['revision']}, not {expected}.")
            if not record["history"]:
                raise BridgeError("There is no companion revision to undo.")
            prior = record["history"].pop()
            record["history"].append({"revision": record["revision"], "state": record["state"], "source": "undo"})
            record["history"] = record["history"][-MAX_HISTORY:]
            record["state"] = prior["state"]
            record["revision"] += 1
            write_record(state_path, record)
        return tool_result({"revision": record["revision"], "message": "Undone locally."})
    raise BridgeError("Unknown Character Sheet companion tool.")


TOOLS = [
    {"name": "open_character_sheet", "description": "Open the Character Sheet page. Warning: this browser page does not yet share the companion state file; do not claim two-way sync.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "read_character_sheet", "description": "Read only the selected companion state file and its revision, not browser or Drive data. Do not infer or change anything.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "apply_character_sheet_update", "description": "Apply a small approved JSON-pointer update. Ask the user for explicit confirmation in this chat first. Deletes or more than five operations need the stronger confirmation phrase returned by the tool.", "inputSchema": {"type": "object", "required": ["expected_revision", "operations", "approval"], "properties": {"expected_revision": {"type": "integer"}, "operations": {"type": "array"}, "approval": {"type": "string"}}}},
    {"name": "undo_character_sheet_update", "description": "Undo the most recent companion revision after explicit chat confirmation.", "inputSchema": {"type": "object", "required": ["expected_revision", "approval"], "properties": {"expected_revision": {"type": "integer"}, "approval": {"type": "string"}}}},
]


def run_mcp(state_path: Path, sheet_path: Path | None = None) -> None:
    for raw in sys.stdin:
        try:
            request = json.loads(raw)
            method = request.get("method")
            request_id = request.get("id")
            if method == "initialize":
                result = {"protocolVersion": request.get("params", {}).get("protocolVersion", "2025-06-18"), "capabilities": {"tools": {}}, "serverInfo": {"name": "character-sheet-companion", "version": "1.1.0"}}
            elif method == "tools/list":
                result = {"tools": TOOLS}
            elif method == "tools/call":
                params = request.get("params") or {}
                result = call_tool(state_path, params.get("name"), params.get("arguments") or {}, sheet_path)
            elif method == "notifications/initialized":
                continue
            else:
                raise BridgeError("Unsupported MCP method.")
            if request_id is not None:
                print(json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result}), flush=True)
        except Exception as error:
            if isinstance(locals().get("request"), dict) and request.get("id") is not None:
                print(json.dumps({"jsonrpc": "2.0", "id": request["id"], "error": {"code": -32000, "message": str(error)}}), flush=True)


"""Proposal embedded in existing companion server; stdlib globals json/re exist."""
def _cs_compact_art_manifest(manifest, html):
    if manifest.get('version') != 2:
        return manifest, {}
    if set(manifest) != {'version', 'assets'} or not isinstance(manifest['assets'], dict) or len(manifest['assets']) != 1260:
        raise BridgeError('Invalid frozen artwork manifest.')
    tag = '<script type="application/json" id="cs-stock-assets-catalogue">'
    if html.count(tag) != 1:
        raise BridgeError('Missing frozen artwork catalogue.')
    body = html.split(tag, 1)[1].split('</script>', 1)[0]
    catalogue = json.loads(body)
    if catalogue != {'version': 1, 'assets': manifest['assets']}:
        raise BridgeError('Artwork manifest differs from its catalogue.')
    legacy, dimensions = {}, {}
    for path, row in manifest['assets'].items():
        match = re.fullmatch(r'assets/stock/([0-9a-f]{64})\.webp', path)
        if match is None or not isinstance(row, list) or len(row) != 3 or any(type(value) is not int or value < 1 for value in row) or row[0] > 26214400 or row[1]*row[2] > 16777216:
            raise BridgeError('Invalid frozen artwork row.')
        legacy[path] = {'sha256': match[1], 'bytes': row[0]}
        dimensions[path] = tuple(row[1:])
    return {'version': 1, 'assets': legacy}, dimensions


def _cs_static_webp_dimensions(raw):
    if len(raw) < 25 or raw[:4] != b'RIFF' or raw[8:12] != b'WEBP' or int.from_bytes(raw[4:8], 'little') + 8 != len(raw):
        raise BridgeError('Invalid frozen WebP.')
    kind = raw[12:16]
    if kind == b'VP8L' and raw[20] == 0x2f:
        bits = int.from_bytes(raw[21:25], 'little')
        if bits >> 29:
            raise BridgeError('Invalid frozen WebP version.')
        return 1+(bits & 0x3fff), 1+((bits >> 14) & 0x3fff)
    if len(raw) >= 30 and kind == b'VP8X' and int.from_bytes(raw[16:20], 'little') == 10 and not raw[20] & ~0x10:
        return 1+int.from_bytes(raw[24:27], 'little'), 1+int.from_bytes(raw[27:30], 'little')
    if len(raw) >= 30 and kind == b'VP8 ' and not raw[20] & 1 and raw[23:26] == b'\x9d\x01\x2a':
        return int.from_bytes(raw[26:28], 'little') & 0x3fff, int.from_bytes(raw[28:30], 'little') & 0x3fff
    raise BridgeError('Unsupported frozen WebP.')


def create_http_server(sheet_path: Path, state_path: Path, port: int = 0) -> tuple[ThreadingHTTPServer, str]:
    if not sheet_path.is_file() or sheet_path.suffix.lower() != ".html":
        raise BridgeError("--sheet must name the one Character Sheet HTML file to serve.")
    token = secrets.token_urlsafe(32)
    allowed_assets={}
    compact_stock_dimensions={}
    asset_manifest=sheet_path.parent/"public-assets.json"
    if asset_manifest.exists():
        if asset_manifest.is_symlink():raise BridgeError("Unsafe public artwork manifest.")
        manifest=json.loads(asset_manifest.read_text(encoding="utf-8"))
        manifest,compact_stock_dimensions=_cs_compact_art_manifest(manifest,sheet_path.read_text(encoding="utf-8"))
        if manifest.get("version")!=1 or not isinstance(manifest.get("assets"),dict):raise BridgeError("Invalid public artwork manifest.")
        for relative,expected in manifest["assets"].items():
            if not re.fullmatch(r"assets/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+\.(?:webp|png|jpg|jpeg)",relative):raise BridgeError("Unsupported public artwork path.")
            asset=sheet_path.parent/relative
            if asset.is_symlink() or not asset.is_file():raise BridgeError("Public artwork is missing or unsafe.")
            asset.resolve().relative_to(sheet_path.parent.resolve())
            data=asset.read_bytes()
            if hashlib.sha256(data).hexdigest()!=expected.get("sha256") or len(data)!=expected.get("bytes"):raise BridgeError("Public artwork checksum differs.")
            if relative in compact_stock_dimensions and _cs_static_webp_dimensions(data)!=compact_stock_dimensions[relative]:raise BridgeError("Public artwork dimensions differ.")
            allowed_assets["/"+relative]=data

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *_args: Any) -> None:
            return

        def end_headers(self) -> None:
            # Inline handlers are a documented compatibility exception; network destinations remain explicit.
            self.send_header("Content-Security-Policy","default-src 'self'; script-src 'self' 'unsafe-inline' blob: https://accounts.google.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self' https://api.anthropic.com https://api.openai.com http://localhost:11434 https://api.github.com https://raw.githubusercontent.com https://accounts.google.com https://oauth2.googleapis.com https://www.googleapis.com; frame-src https://accounts.google.com; worker-src 'self' blob:; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
            self.send_header("Referrer-Policy","no-referrer")
            self.send_header("X-Frame-Options","DENY")
            self.send_header("X-Content-Type-Options","nosniff")
            super().end_headers()

        def trusted_request(self) -> bool:
            hosts=self.headers.get_all("Host",[])
            allowed={f"127.0.0.1:{actual_port}",f"localhost:{actual_port}"}
            if len(hosts)!=1 or hosts[0] not in allowed:return False
            origin=self.headers.get("Origin")
            if origin is not None and origin!=f"http://{hosts[0]}":return False
            dest=self.headers.get("Sec-Fetch-Dest","")
            if dest in {"frame","iframe","object","embed"}:return False
            site=self.headers.get("Sec-Fetch-Site","")
            if site not in {"","none","same-origin"}:
                navigation=self.command=="GET" and urlparse(self.path).path in {"/","/character-sheet.html"} and self.headers.get("Sec-Fetch-Mode")=="navigate" and dest=="document"
                if not navigation:return False
            return True

        def authorised(self) -> bool:
            return secrets.compare_digest(self.headers.get("X-CS-Companion-Token", ""),token)

        def send_json(self, status: int, payload: Any) -> None:
            encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def do_GET(self) -> None:
            if not self.trusted_request():
                self.send_json(HTTPStatus.FORBIDDEN,{"error":"untrusted local request"});return
            parsed = urlparse(self.path)
            if parsed.path == "/api/state":
                if not self.authorised():
                    self.send_json(HTTPStatus.FORBIDDEN, {"error": "missing local companion token"})
                    return
                try:
                    record = load_record(state_path)
                    self.send_json(HTTPStatus.OK, {"revision": record["revision"], "state": record["state"]})
                except BridgeError as error:
                    self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
                return
            if parsed.path in {"/", "/character-sheet.html"}:
                query = parse_qs(parsed.query)
                if query.get("cs-companion") != ["1"] or query.get("cs-token") != [token]:
                    self.send_response(HTTPStatus.FOUND)
                    self.send_header("Location", f"/character-sheet.html?cs-companion=1&cs-token={token}")
                    self.end_headers()
                    return
                body = sheet_path.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if parsed.path in allowed_assets:
                body=allowed_assets[parsed.path]
                self.send_response(HTTPStatus.OK)
                extension=Path(parsed.path).suffix.lower()
                self.send_header("Content-Type",{".webp":"image/webp",".png":"image/png",".jpg":"image/jpeg",".jpeg":"image/jpeg"}[extension])
                self.send_header("Cache-Control","no-store")
                self.send_header("Content-Length",str(len(body)))
                self.end_headers();self.wfile.write(body);return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            if not self.trusted_request():
                self.send_json(HTTPStatus.FORBIDDEN,{"error":"untrusted local request"});return
            if urlparse(self.path).path != "/api/state" or not self.authorised():
                self.send_json(HTTPStatus.FORBIDDEN, {"error": "not available"})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if size <= 0 or size > MAX_BODY:
                    raise BridgeError("Invalid local companion request size.")
                payload = json.loads(self.rfile.read(size))
                result = replace_from_app(state_path, payload.get("expected_revision"), payload.get("state"))
                self.send_json(HTTPStatus.OK, result)
            except (BridgeError, json.JSONDecodeError, ValueError) as error:
                self.send_json(HTTPStatus.CONFLICT, {"error": str(error)})

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    actual_port = server.server_address[1]
    url = f"http://127.0.0.1:{actual_port}/"
    return server, url


def open_companion_page(sheet_path: Path, state_path: Path) -> tuple[str, bool]:
    key = (str(sheet_path), str(state_path))
    with LOCK:
        hosted = HOSTED_PAGES.get(key)
        if hosted is None:
            server, url = create_http_server(sheet_path, state_path)
            thread = threading.Thread(target=server.serve_forever, name="character-sheet-companion", daemon=True)
            thread.start()
            hosted = (server, url, thread)
            HOSTED_PAGES[key] = hosted
    return hosted[1], bool(webbrowser.open(hosted[1], new=2))


def close_hosted_pages() -> None:
    with LOCK:
        hosted = list(HOSTED_PAGES.values())
        HOSTED_PAGES.clear()
    for server, _url, thread in hosted:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def serve(sheet_path: Path, state_path: Path, port: int) -> None:
    server, url = create_http_server(sheet_path, state_path, port)
    print(f"Character Sheet companion is ready at {url}", flush=True)
    server.serve_forever()


def fictional_encryption_proof_document() -> dict[str, Any]:
    return {
        "cs-state-v1": {
            "name": "Avery Example",
            "mainQuest": {"title": "Try one fictional encrypted round trip"},
            "sideQuests": [],
        },
        DEFAULT_SCHEMA_NAMESPACE: {"schemaVersion": 1, "liveContext": {"proof": "fictional-only"}},
    }


def _prompt_recovery_passphrase(*, confirm: bool) -> str:
    passphrase = getpass.getpass("Character Sheet recovery passphrase: ")
    if not passphrase:
        raise EncryptedStoreError("Recovery passphrase must not be blank.")
    if confirm and getpass.getpass("Repeat recovery passphrase: ") != passphrase:
        raise EncryptedStoreError("Recovery passphrases did not match.")
    return passphrase


def main() -> int:
    parser = argparse.ArgumentParser(description="Local-only Character Sheet companion")
    subcommands = parser.add_subparsers(dest="command", required=True)
    for name in ("serve", "mcp"):
        command = subcommands.add_parser(name)
        command.add_argument("--state", type=Path, required=True, help="private companion state JSON")
    hosted = subcommands.choices["serve"]
    hosted.add_argument("--sheet", type=Path, required=True, help="the single Character Sheet HTML file")
    hosted.add_argument("--port", type=int, default=0, help="loopback port, or 0 for a free port")
    connected = subcommands.choices["mcp"]
    connected.add_argument("--sheet", type=Path, help="the single Character Sheet HTML file opened by the companion")

    proof_init = subcommands.add_parser("encrypted-proof-init", help="create a fictional encrypted synthetic Drive object")
    proof_init.add_argument("--store", type=Path, required=True, help="test-only encrypted synthetic Drive object")
    proof_init.add_argument("--remember-in-keychain", action="store_true", help="store the recovery passphrase in macOS Login Keychain")
    proof_init.add_argument("--keychain-service", default="org.character-sheet.encrypted-proof")
    proof_init.add_argument("--keychain-account", default=DEFAULT_KEYCHAIN_ACCOUNT)

    proof_ai = subcommands.add_parser("encrypted-proof-ai", help="serve the fictional encrypted object over local JSON lines")
    proof_ai.add_argument("--store", type=Path, required=True, help="test-only encrypted synthetic Drive object")
    proof_ai.add_argument("--keychain-service", help="unlock from macOS Login Keychain instead of prompting")
    proof_ai.add_argument("--keychain-account", default=DEFAULT_KEYCHAIN_ACCOUNT)

    proof_forget = subcommands.add_parser("encrypted-proof-forget-keychain", help="remove the test-only Login Keychain entry")
    proof_forget.add_argument("--keychain-service", default="org.character-sheet.encrypted-proof")
    proof_forget.add_argument("--keychain-account", default=DEFAULT_KEYCHAIN_ACCOUNT)

    args = parser.parse_args()
    try:
        if args.command == "serve":
            serve(args.sheet.expanduser().resolve(), args.state.expanduser().resolve(), args.port)
        elif args.command == "mcp":
            sheet_path = args.sheet.expanduser().resolve() if args.sheet else None
            run_mcp(args.state.expanduser().resolve(), sheet_path)
        elif args.command == "encrypted-proof-init":
            passphrase = _prompt_recovery_passphrase(confirm=True)
            interface = EncryptedCharacterSheetInterface(SyntheticDriveFile(args.store.expanduser().resolve()), passphrase)
            metadata = interface.initialise(fictional_encryption_proof_document())
            if args.remember_in_keychain:
                MacOSKeychainUnlock(args.keychain_service, args.keychain_account).remember(passphrase)
            print(json.dumps({"created": True, "metadata": metadata, "fictionalOnly": True}), flush=True)
        elif args.command == "encrypted-proof-ai":
            passphrase = (
                MacOSKeychainUnlock(args.keychain_service, args.keychain_account).unlock()
                if args.keychain_service
                else _prompt_recovery_passphrase(confirm=False)
            )
            run_encrypted_ai_jsonl(
                EncryptedCharacterSheetInterface(SyntheticDriveFile(args.store.expanduser().resolve()), passphrase)
            )
        else:
            MacOSKeychainUnlock(args.keychain_service, args.keychain_account).forget()
            print(json.dumps({"removed": True, "service": args.keychain_service, "account": args.keychain_account}), flush=True)
        return 0
    except (BridgeError, OSError) as error:
        print(f"Character Sheet companion: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
