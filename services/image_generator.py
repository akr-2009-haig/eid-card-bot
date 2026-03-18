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

PLACEHOLDER_WIDTH_MULTIPLIER = 2.8
PLACEHOLDER_PADDING_X = 12
PLACEHOLDER_PADDING_Y = 8


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


def _pick_fill_color(img: Image.Image, x: int, y: int, w: int, h: int) -> tuple:
    left = max(x - 10, 0)
    top = max(y - 10, 0)
    right = min(x + w + 10, img.width)
    bottom = min(y + h + 10, img.height)
    sample = img.crop((left, top, right, bottom)).convert("RGB")
    pixels = list(sample.getdata())
    sampled_pixels = pixels[::8] if len(pixels) > 8 else pixels
    pixels = sampled_pixels
    if not pixels:
        return 255, 255, 255
    return tuple(sum(channel) // len(pixels) for channel in zip(*pixels))


def _draw_name_on_placeholder(img: Image.Image, draw: ImageDraw.ImageDraw, user_name: str, template: dict) -> bool:
    x = template.get("placeholder_x")
    y = template.get("placeholder_y")
    w = template.get("placeholder_w")
    h = template.get("placeholder_h")
    if None in (x, y, w, h):
        return False

    font_size = template.get("font_size") or max(int(h), FONT_SIZE_NAME)
    font = _get_font(font_size)
    text_w, text_h = _get_text_size(draw, user_name, font)

    # Allow the replacement name to grow beyond the detected placeholder box so longer names still fit naturally.
    max_width = max(int(w * PLACEHOLDER_WIDTH_MULTIPLIER), text_w)
    while text_w > max_width and font_size > 20:
        font_size -= 2
        font = _get_font(font_size)
        text_w, text_h = _get_text_size(draw, user_name, font)

    fill_color = _pick_fill_color(img, int(x), int(y), int(w), int(h))
    draw.rectangle(
        (
            int(x) - PLACEHOLDER_PADDING_X,
            int(y) - PLACEHOLDER_PADDING_Y,
            int(x + max(w, text_w) + PLACEHOLDER_PADDING_X),
            int(y + max(h, text_h) + PLACEHOLDER_PADDING_Y),
        ),
        fill=fill_color,
    )
    _draw_text_with_shadow(
        draw,
        (int(x) + max((int(w) - text_w) // 2, 0), int(y) + max((int(h) - text_h) // 2, 0)),
        user_name,
        font,
        TEXT_COLOR,
        TEXT_SHADOW_COLOR,
    )
    return True


def generate_card(template_path: str, user_name: str, template: dict | None = None) -> str:
    img = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    width, height = img.size

    if template and _draw_name_on_placeholder(img, draw, user_name, template):
        os.makedirs(GENERATED_DIR, exist_ok=True)
        out_path = os.path.join(GENERATED_DIR, f"card_{uuid.uuid4().hex}.png")
        img = img.convert("RGB")
        img.save(out_path, "PNG")
        return out_path

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
