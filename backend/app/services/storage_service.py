"""Supabase Storage Service for secure complaint photograph management.

Features:
- Magic bytes image validation (JPEG, PNG, WebP)
- 5 MB maximum file size limit
- User-namespaced object paths preventing cross-user image theft
- Short-lived signed URL generation
- Atomic rollback cleanup
- Zero service-role key exposure to frontend
"""
import uuid
from typing import Optional
from fastapi import HTTPException, UploadFile, status
import httpx

from app.core.config import settings

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
BUCKET_NAME = "complaint-images"

ALLOWED_MAGIC_BYTES = {
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/webp": [b"RIFF"],  # Checked in conjunction with 'WEBP' at offset 8:12
}

MIME_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def detect_image_type(data: bytes) -> Optional[str]:
    """Verify image type by inspecting file header magic bytes."""
    if len(data) < 12:
        return None

    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"

    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"

    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"

    return None


class StorageService:
    """Service for interacting with Supabase Storage via secure backend calls."""

    def __init__(self):
        self.url = (settings.SUPABASE_URL or "").rstrip("/")
        self.service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY or ""
        self.anon_key = settings.SUPABASE_ANON_KEY or ""

    @property
    def is_configured(self) -> bool:
        """Check if storage service has required Supabase credentials."""
        return bool(self.url and self.service_role_key)

    def _get_admin_headers(self, content_type: Optional[str] = None) -> dict:
        headers = {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    async def upload_complaint_image(self, file: UploadFile, user_id: str) -> dict:
        """Validate and upload an image to the private complaint-images bucket.

        Stores objects under 'complaints/{user_id}/{unique_id}.{ext}' to enforce
        user isolation and prevent unauthorized reuse of another user's photos.
        """
        if not self.is_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage service is not configured. Please supply SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.",
            )

        # Read file content
        content = await file.read()
        file_size = len(content)

        # 1. Enforce max file size (5MB)
        if file_size > MAX_IMAGE_SIZE_BYTES:
            raise HTTPException(
                status_code=getattr(status, "HTTP_413_CONTENT_TOO_LARGE", 413),
                detail=f"Image file exceeds maximum permitted size of 5 MB ({file_size} bytes received).",
            )

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty image file received.",
            )

        # 2. Enforce magic bytes content inspection
        detected_mime = detect_image_type(content)
        if not detected_mime or detected_mime not in MIME_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Invalid image format. Allowed formats are JPEG, PNG, and WebP (verified via file signature).",
            )

        # 3. Generate unique namespaced storage path
        ext = MIME_EXTENSIONS[detected_mime]
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        object_path = f"complaints/{user_id}/{unique_filename}"

        # 4. Upload to Supabase Storage via REST
        endpoint = f"{self.url}/storage/v1/object/{BUCKET_NAME}/{object_path}"
        headers = self._get_admin_headers(content_type=detected_mime)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(endpoint, content=content, headers=headers)
                if resp.status_code not in (200, 201):
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Storage upload failed: {resp.text}",
                    )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to communicate with Supabase Storage: {str(exc)}",
            )

        # 5. Generate short-lived signed URL for initial preview
        signed_url = await self.create_signed_url(object_path, expires_in=3600)

        return {
            "image_path": object_path,
            "file_name": file.filename or unique_filename,
            "content_type": detected_mime,
            "size_bytes": file_size,
            "signed_url": signed_url,
        }

    async def create_signed_url(self, object_path: str, expires_in: int = 3600) -> Optional[str]:
        """Generate a short-lived signed URL for an authorized client."""
        if not self.is_configured or not object_path:
            return None

        # Clean path if prefixed with bucket name
        cleaned_path = object_path.lstrip("/")
        if cleaned_path.startswith(f"{BUCKET_NAME}/"):
            cleaned_path = cleaned_path[len(f"{BUCKET_NAME}/"):]

        endpoint = f"{self.url}/storage/v1/object/sign/{BUCKET_NAME}/{cleaned_path}"
        headers = self._get_admin_headers(content_type="application/json")
        payload = {"expiresIn": expires_in}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(endpoint, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    signed_url_fragment = data.get("signedURL")
                    if signed_url_fragment:
                        return f"{self.url}/storage/v1{signed_url_fragment}"
        except Exception:
            pass
        return None

    async def delete_complaint_image(self, object_path: str) -> bool:
        """Delete an object from storage (used for cleanup when database operations fail)."""
        if not self.is_configured or not object_path:
            return False

        cleaned_path = object_path.lstrip("/")
        if cleaned_path.startswith(f"{BUCKET_NAME}/"):
            cleaned_path = cleaned_path[len(f"{BUCKET_NAME}/"):]

        endpoint = f"{self.url}/storage/v1/object/{BUCKET_NAME}/{cleaned_path}"
        headers = self._get_admin_headers()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.delete(endpoint, headers=headers)
                return resp.status_code in (200, 204)
        except Exception:
            return False

    def validate_image_ownership(self, image_path: Optional[str], user_id: str) -> bool:
        """Verify that an image path was uploaded by the specified user.

        Blocks IDOR/tampering where User A attempts to link User B's photo to their complaint.
        """
        if not image_path:
            return True

        cleaned = image_path.lstrip("/")
        # Path must start with 'complaints/{user_id}/'
        expected_prefix = f"complaints/{user_id}/"
        return cleaned.startswith(expected_prefix)


# Global storage service instance
storage_service = StorageService()
