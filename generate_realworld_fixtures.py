import os
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import fitz  # PyMuPDF

os.makedirs("benchmark_data/multipage", exist_ok=True)
os.makedirs("benchmark_data/realworld", exist_ok=True)

# 1. Multi-Page Scanned and Digital PDFs Generator
def create_pdf(page_count, is_scanned=True, out_path=""):
    doc = fitz.open()
    base_img_path = "benchmark_data/aster_cbc.png"
    base_pil = Image.open(base_img_path)

    for i in range(page_count):
        if is_scanned:
            # Create image page
            img_byte_arr = open(base_img_path, "rb").read()
            rect = fitz.Rect(0, 0, base_pil.width, base_pil.height)
            page = doc.new_page(width=base_pil.width, height=base_pil.height)
            page.insert_image(rect, stream=img_byte_arr)
        else:
            # Digital text page
            page = doc.new_page(width=600, height=800)
            text_content = open("backend/tests/fixtures/aster_cbc.txt", "r", encoding="utf-8").read()
            page.insert_text(fitz.Point(50, 50), text_content, fontsize=11)

    doc.save(out_path)
    doc.close()
    print(f"Generated PDF: {out_path} ({page_count} pages, scanned={is_scanned})")

create_pdf(1, is_scanned=True, out_path="benchmark_data/multipage/scanned_1p.pdf")
create_pdf(3, is_scanned=True, out_path="benchmark_data/multipage/scanned_3p.pdf")
create_pdf(5, is_scanned=True, out_path="benchmark_data/multipage/scanned_5p.pdf")
create_pdf(10, is_scanned=True, out_path="benchmark_data/multipage/scanned_10p.pdf")
create_pdf(3, is_scanned=False, out_path="benchmark_data/multipage/digital_3p.pdf")


# 2. Real-World Image Quality Variations Generator
src_img = Image.open("benchmark_data/aster_cbc.png").convert("RGB")

# A. Clean Report
src_img.save("benchmark_data/realworld/A_clean_report.png")

# B. Phone Photograph (slight perspective / affine skew)
w, h = src_img.size
coeffs = [1, 0.05, 0, 0.03, 1, 0, 0, 0]
phone_img = src_img.transform((w, h), Image.Transform.AFFINE, (1, 0.03, -10, 0.02, 1, -10))
phone_img.save("benchmark_data/realworld/B_phone_photograph.png")

# C. Low-light Photograph (dimmed brightness & contrast)
enh_bri = ImageEnhance.Brightness(src_img)
dim_img = enh_bri.enhance(0.55)
enh_con = ImageEnhance.Contrast(dim_img)
low_light_img = enh_con.enhance(0.75)
low_light_img.save("benchmark_data/realworld/C_low_light.png")

# D. Slightly Blurry Image (mild Gaussian blur)
blurry_img = src_img.filter(ImageFilter.GaussianBlur(radius=1.2))
blurry_img.save("benchmark_data/realworld/D_blurry.png")

# E. Rotated Report (8 degrees rotation)
rotated_img = src_img.rotate(8, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=(255, 255, 255))
rotated_img.save("benchmark_data/realworld/E_rotated_8deg.png")

# F. Shadowed Report (gradient shadow across page)
shadow_img = src_img.copy()
np_img = np.array(shadow_img, dtype=np.float32)
h_arr, w_arr = np_img.shape[:2]
gradient = np.linspace(0.4, 1.0, w_arr).reshape(1, w_arr, 1)
np_shadowed = np.clip(np_img * gradient, 0, 255).astype(np.uint8)
Image.fromarray(np_shadowed).save("benchmark_data/realworld/F_shadowed.png")

# G. Compressed Image (high JPEG compression / WhatsApp artifacts)
src_img.save("benchmark_data/realworld/G_compressed.jpg", "JPEG", quality=28)

# H. Small Text (downscaled 50% then upscaled)
small_w, small_h = int(w * 0.5), int(h * 0.5)
small_img = src_img.resize((small_w, small_h), Image.Resampling.BILINEAR)
small_img.save("benchmark_data/realworld/H_small_text.png")

print("Generated all real-world test variations in benchmark_data/realworld/")
