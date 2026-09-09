"""Shared validators (SRS FR-LED-04, FR-STU-06)."""
import os
import re

from django.conf import settings
from django.core.exceptions import ValidationError

BD_PHONE = re.compile(r"^(?:\+?880|0)1[3-9]\d{8}$")


def validate_bd_phone(value):
    cleaned = re.sub(r"[\s\-()]", "", value or "")
    if not BD_PHONE.match(cleaned):
        raise ValidationError(
            "Enter a valid Bangladeshi mobile number, e.g. 01712345678 or +8801712345678.")


def normalise_bd_phone(value):
    cleaned = re.sub(r"[\s\-()]", "", value or "")
    if cleaned.startswith("0"):
        cleaned = "+88" + cleaned
    elif cleaned.startswith("880"):
        cleaned = "+" + cleaned
    return cleaned


def validate_upload(f):
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if f.size > max_bytes:
        raise ValidationError(f"File is larger than {settings.MAX_UPLOAD_SIZE_MB} MB.")
    ext = os.path.splitext(f.name)[1].lower()
    if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
        raise ValidationError(
            "Allowed file types: " + ", ".join(settings.ALLOWED_UPLOAD_EXTENSIONS))
    content_type = getattr(f, "content_type", None)
    if content_type and content_type not in settings.ALLOWED_UPLOAD_MIME:
        raise ValidationError("The file content does not match an allowed type.")
    return f
