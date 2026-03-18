import os
import sys
import random
import uuid
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    FONT_PATH, FONT_SIZE_NAME, FONT_SIZE_LABEL,
    TEXT_COLOR, TEXT_SHADOW_COLOR, GENERATED_DIR
)


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()


def _draw_text_with_shadow(draw: ImageDraw.ImageDraw, pos: tuple, text: str, font, color, shadow_color, shadow_offset: int = 2):
    x, y = pos
    draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=shadow_color)
    draw.text((x, y), text, font=font, fill=color)


def _get_text_size(draw: ImageDraw.ImageDraw, text: str, font) -> tuple:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def generate_card(template_path: str, user_name: str) -> str:
    img = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    width, height = img.size

    font_label = _get_font(FONT_SIZE_LABEL)
    font_name = _get_font(FONT_SIZE_NAME)

    label_text = "تهنئة من"
    lw, lh = _get_text_size(draw, label_text, font_label)
    label_x = (width - lw) // 2
    label_y = int(height * 0.70)

    _draw_text_with_shadow(draw, (label_x, label_y), label_text, font_label, TEXT_COLOR, TEXT_SHADOW_COLOR)

    nw, nh = _get_text_size(draw, user_name, font_name)
    name_x = (width - nw) // 2
    name_y = label_y + lh + 10

    _draw_text_with_shadow(draw, (name_x, name_y), user_name, font_name, TEXT_COLOR, TEXT_SHADOW_COLOR)

    os.makedirs(GENERATED_DIR, exist_ok=True)
    out_path = os.path.join(GENERATED_DIR, f"card_{uuid.uuid4().hex}.png")
    img = img.convert("RGB")
    img.save(out_path, "PNG")
    return out_path


def pick_random_template(templates: list) -> dict | None:
    if not templates:
        return None
    return random.choice(templates)
