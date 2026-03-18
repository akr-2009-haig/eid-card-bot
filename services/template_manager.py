import os
import sys
import shutil
import uuid
import re

from PIL import Image

try:
    import pytesseract
except ImportError:  # pragma: no cover - optional runtime dependency
    pytesseract = None

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TEMPLATES_DIR
from database.db import add_template, delete_template

PLACEHOLDER_PATTERNS = {"الاسم", "اسم"}
# The strip pattern removes common placeholder wrappers like [الاسم], (الاسم), and decorative circles such as ⭕ الاسم.
OCR_STRIP_PATTERN = r"[\s\[\]\(\){}<>⭕•\-_=+*]+"


def _clean_ocr_text(value: str) -> str:
    return re.sub(OCR_STRIP_PATTERN, "", value or "").strip().lower()


def detect_name_placeholder(image_path: str) -> dict:
    if pytesseract is None:
        return {}

    try:
        image = Image.open(image_path)
        data = pytesseract.image_to_data(
            image,
            output_type=pytesseract.Output.DICT,
            lang="ara+eng",
            config="--psm 11",
        )
    except Exception:
        return {}

    for index, raw_text in enumerate(data.get("text", [])):
        normalized = _clean_ocr_text(raw_text)
        if not normalized:
            continue
        if normalized not in PLACEHOLDER_PATTERNS:
            continue

        left = int(data["left"][index])
        top = int(data["top"][index])
        width = int(data["width"][index])
        height = int(data["height"][index])
        return {
            "placeholder_x": left,
            "placeholder_y": top,
            "placeholder_w": width,
            "placeholder_h": height,
            "font_size": max(height, 32),
            "placeholder_text": raw_text,
        }

    return {}


def save_template_file(local_path: str, original_filename: str = "") -> str:
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    ext = os.path.splitext(original_filename or local_path)[1].lower() or ".jpg"
    if ext == ".jpeg":
        ext = ".jpg"
    if ext not in {".png", ".jpg", ".jpeg"}:
        ext = ".jpg"
    dest = os.path.join(TEMPLATES_DIR, f"template_{uuid.uuid4().hex}{ext}")
    shutil.copy2(local_path, dest)
    return dest


def register_template(file_id: str, file_path: str, original_filename: str = "") -> tuple[int, dict]:
    metadata = detect_name_placeholder(file_path)
    template_id = add_template(file_id, file_path, original_filename=original_filename, **metadata)
    return template_id, metadata


def remove_template(template_id: int):
    row = delete_template(template_id)
    if row and row.get("file_path") and os.path.exists(row["file_path"]):
        os.remove(row["file_path"])
