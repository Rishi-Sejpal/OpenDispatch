"""Storage abstraction.

Implementations: LocalFileStorage. The default backend is `local`. Storage
backends expose put/get and return opaque URIs.
"""

from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from typing import Protocol

from app.core.config import get_settings


class StorageProvider(Protocol):
    def put(self, *, name: str, content: bytes, mime: str = "application/octet-stream") -> str: ...
    def get(self, uri: str) -> bytes: ...
    def delete(self, uri: str) -> None: ...


class LocalFileStorage:
    def __init__(self, base_path: str) -> None:
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)

    def _path_for(self, uri: str) -> Path:
        # URIs are of the form `local://<name>`
        prefix = "local://"
        if uri.startswith(prefix):
            return self.base / uri[len(prefix):]
        return Path(uri)

    def put(self, *, name: str, content: bytes, mime: str = "application/octet-stream") -> str:
        unique = f"{uuid.uuid4().hex}-{name}"
        path = self.base / unique
        path.write_bytes(content)
        return f"local://{unique}"

    def get(self, uri: str) -> bytes:
        return self._path_for(uri).read_bytes()

    def delete(self, uri: str) -> None:
        p = self._path_for(uri)
        if p.exists():
            p.unlink()


_default: StorageProvider | None = None


def get_default_storage() -> StorageProvider:
    global _default
    if _default is None:
        settings = get_settings()
        if settings.storage_backend == "local":
            _default = LocalFileStorage(settings.storage_local_path)
        else:
            raise RuntimeError(f"Unknown storage backend: {settings.storage_backend}")
    return _default
