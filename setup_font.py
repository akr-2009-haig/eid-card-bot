"""
Run this script once to download an Arabic font.
Usage: python setup_font.py
"""
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import FONT_PATH, FONTS_DIR

FONT_URL = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoNaskhArabic/NotoNaskhArabic-Regular.ttf"


def download_font():
    os.makedirs(FONTS_DIR, exist_ok=True)
    if os.path.exists(FONT_PATH):
        print(f"Font already exists at {FONT_PATH}")
        return
    print(f"Downloading Arabic font from Google Fonts...")
    try:
        urllib.request.urlretrieve(FONT_URL, FONT_PATH)
        print(f"Font downloaded successfully to {FONT_PATH}")
    except Exception as e:
        print(f"Download failed: {e}")
        print("\nAlternative: Place any .ttf Arabic font manually at:")
        print(f"  {os.path.abspath(FONT_PATH)}")


if __name__ == "__main__":
    download_font()
