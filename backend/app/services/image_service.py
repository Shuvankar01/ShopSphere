"""Local image file storage for product images.

Deliberately simple and development-friendly: files are written under
`settings.UPLOAD_DIR` and served by the `/uploads` static mount. No cloud
credentials required. Metadata lives in PostgreSQL (product_images.url).
"""
from __future__ import annotations

import uuid
from pathlib import Path
 
from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import BadRequestException

# Extension -> accepted content types (declared by the client).
_ALLOWED_TYPES = {
    "jpg": {"image/jpeg"},
    "jpeg": {"image/jpeg"},
    "png": {"image/png"},
    "webp": {"image/webp"},
    "gif": {"image/gif"},
}

# Characters allowed in a client-provided filename before we discard it
# entirely in favour of a generated uuid name.
_SAFE_NAME_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")

MAX_SIZE_BYTES = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024


class ImageStorage:
    def __init__(self, upload_dir: Path | None = None):
        self.upload_dir = upload_dir or settings.UPLOAD_DIR
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def save(self, file: UploadFile) -> str:
        """Validate and persist an uploaded image. Returns the public URL."""
        upload = _validate_upload(file)
        filename = f"{uuid.uuid4().hex}.{upload['ext']}"
        # Uploaded files come from a stripped filename + generated uuid, so
        # destination is always safe.
        dest = self.upload_dir / filename
        size = 0
        too_large = False
        try:
            with dest.open("wb") as out:
                while True:
                    chunk = file.file.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_SIZE_BYTES:
                        too_large = True
                        break
                    out.write(chunk)
        except Exception:
            # Abort mid-write: remove the partial file. This runs outside the
            # `with` block so the handle is closed (and unlink works on Windows).
            dest.unlink(missing_ok=True)
            raise
        if too_large:
            dest.unlink(missing_ok=True)
            raise BadRequestException(
                f"Image exceeds the {settings.MAX_IMAGE_SIZE_MB} MB size limit"
            )
        return f"/uploads/{filename}"

    def delete(self, url: str) -> None:
        """Best-effort removal of an uploaded file (ignored for external URLs)."""
        if not url or not url.startswith("/uploads/"):
            return
        filename = Path(url).name
        try:
            (self.upload_dir / filename).unlink()
        except FileNotFoundError:
            pass


def _validate_upload(file: UploadFile) -> dict:
    """Validate content type, extension, and filename safety before saving."""
    filename = file.filename or ""
    if not filename:
        raise BadRequestException("Uploaded file must have a filename")

    # Strip any path components / separators — never trust a raw filename.
    cleaned = Path(filename).name
    if cleaned != filename:
        raise BadRequestException("Invalid filename: path separators are not allowed")

    ext = cleaned.rsplit(".", 1)[-1].lower() if "." in cleaned else ""
    if ext not in _ALLOWED_TYPES:
        raise BadRequestException(
            f"Unsupported file type '.{ext or '?'}'. Allowed: "
            + ", ".join(sorted(_ALLOWED_TYPES))
        )

    content_type = (file.content_type or "").lower()
    if content_type not in _ALLOWED_TYPES[ext]:
        raise BadRequestException(
            f"File content type '{content_type or 'unknown'}' does not match extension '.{ext}'"
        )

    return {"ext": ext}

# content_type/ext table used by consumers (tests, docs).
ALLOWED_CONTENT_TYPES = sorted({ct for types in _ALLOWED_TYPES.values() for ct in types})
