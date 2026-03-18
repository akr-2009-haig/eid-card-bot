import os
import sys
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TEMPLATES_DIR
from database.db import add_template, get_templates, delete_template


def save_template_file(file_id: str, local_path: str) -> str:
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    ext = os.path.splitext(local_path)[1] or ".jpg"
    count = len(get_templates()) + 1
    dest = os.path.join(TEMPLATES_DIR, f"template_{count}{ext}")
    shutil.copy2(local_path, dest)
    return dest


def register_template(file_id: str, file_path: str) -> int:
    return add_template(file_id, file_path)


def remove_template(template_id: int):
    row = delete_template(template_id)
    if row and row.get("file_path") and os.path.exists(row["file_path"]):
        os.remove(row["file_path"])
