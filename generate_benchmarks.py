import os
import sys
import time
from PIL import Image, ImageDraw, ImageFont

# Generate images for representative benchmark reports
def create_report_image(text_path, out_path, title):
    with open(text_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    is_lft = "lft" in text_path.lower()
    if is_lft:
        width, height = 1600, 2000
        img = Image.new("RGB", (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        font_path = "C:/Windows/Fonts/arial.ttf" if os.path.exists("C:/Windows/Fonts/arial.ttf") else None
        font = ImageFont.truetype(font_path, 24) if font_path else ImageFont.load_default()
        y = 80
        for line in lines:
            line_str = line.rstrip("\n")
            parts = [p for p in line_str.split("   ") if p.strip()]
            if len(parts) >= 3 and any(k in parts[0] for k in ["Bilirubin", "ALT", "AST", "Protein", "Albumin", "Globulin", "Ratio", "LDH", "Alkaline", "Gamma", "TEST"]):
                draw.text((80, y), parts[0].strip(), fill=(0, 0, 0), font=font)
                draw.text((450, y), parts[1].strip(), fill=(0, 0, 0), font=font)
                if len(parts) >= 4:
                    draw.text((650, y), parts[2].strip(), fill=(0, 0, 0), font=font)
                    draw.text((850, y), parts[3].strip(), fill=(0, 0, 0), font=font)
                else:
                    draw.text((650, y), parts[2].strip(), fill=(0, 0, 0), font=font)
            else:
                draw.text((80, y), line_str, fill=(0, 0, 0), font=font)
            y += 50
    else:
        width, height = 1200, 1600
        img = Image.new("RGB", (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        y = 50
        for line in lines:
            draw.text((60, y), line.rstrip("\n"), fill=(0, 0, 0))
            y += 35

    img.save(out_path)
    print(f"Generated {out_path} ({width}x{height})")

os.makedirs("benchmark_data", exist_ok=True)
os.makedirs("backend/tests/fixtures/ocr", exist_ok=True)
os.makedirs("tests/fixtures/ocr", exist_ok=True)

for txt_rel, png_rel in [
    ("backend/tests/fixtures/aster_cbc.txt", "benchmark_data/aster_cbc.png"),
    ("backend/tests/fixtures/labsmart_cbc.txt", "benchmark_data/labsmart_cbc.png"),
    ("backend/tests/fixtures/lft_complete.txt", "benchmark_data/lft_complete.png")
]:
    create_report_image(txt_rel, png_rel, png_rel)
    filename = os.path.basename(png_rel)
    create_report_image(txt_rel, f"backend/tests/fixtures/ocr/{filename}", filename)
    create_report_image(txt_rel, f"tests/fixtures/ocr/{filename}", filename)
