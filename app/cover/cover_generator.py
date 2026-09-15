import pymupdf
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFilter
import math, random

from app.book.book_model import BookModel, CoverStatus
from app.fonts.font_manager import FontManager
from app.utils.paths import get_output_dir, get_font_path
from app.utils.logging import get_logger

logger = get_logger(__name__)

class CoverGenerator:
    def __init__(self, font_name: str = "Noto Sans Bengali"):
        self.font_name = font_name
        self.font_manager = FontManager.get_instance()
        self.font_path = self.font_manager.get_font_path(font_name) or get_font_path("NotoSansBengali-Regular.ttf")

    def _create_artistic_background(self, width: int = 1200, height: int = 1800, seed_val: int = 42) -> Image.Image:
        """Generates an atmospheric, literary painting-style background image."""
        img = Image.new("RGB", (width, height), "#1a2a3a")
        draw = ImageDraw.Draw(img)

        # Color palettes for literary moods
        palettes = [
            [(26, 42, 58), (45, 74, 96), (139, 90, 43), (212, 163, 89)],  # Classic Deep Indigo & Warm Gold
            [(30, 20, 40), (70, 45, 85), (160, 80, 110), (230, 190, 150)], # Twilight Plum & Soft Cream
            [(15, 35, 30), (35, 75, 65), (120, 150, 110), (220, 210, 170)], # Atmospheric Sage & Warm Amber
        ]

        colors = palettes[seed_val % len(palettes)]

        # Background gradient
        for y in range(height):
            ratio = y / height
            r = int(colors[0][0] * (1 - ratio) + colors[1][0] * ratio)
            g = int(colors[0][1] * (1 - ratio) + colors[1][1] * ratio)
            b = int(colors[0][2] * (1 - ratio) + colors[1][2] * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Artistic painted shapes / atmospheric lighting blobs
        rng = random.Random(seed_val)
        for _ in range(6):
            cx = rng.randint(100, width - 100)
            cy = rng.randint(200, height - 300)
            rx = rng.randint(200, 450)
            ry = rng.randint(150, 350)
            color = rng.choice(colors[2:]) + (100,)
            draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=color[:3])

        # Soft blur for painted watercolor effect
        img = img.filter(ImageFilter.GaussianBlur(radius=35))
        return img

    def generate_cover(
        self,
        book: BookModel,
        output_dir: Optional[Path] = None,
        palette_seed: int = 42
    ) -> Tuple[Path, Path]:
        """
        Generates front cover PNG image and PDF document with exact metadata:
        - Book Title
        - Writer / Author Name
        - Translator Name ("Translated by [Translator]")
        """
        target_dir = output_dir or get_output_dir()
        target_dir.mkdir(parents=True, exist_ok=True)

        cover_stem = f"cover_{book.book_id}"
        cover_png_path = target_dir / f"{cover_stem}.png"
        cover_pdf_path = target_dir / f"{cover_stem}.pdf"

        # 1. Generate artistic background image
        bg_image = self._create_artistic_background(width=1200, height=1800, seed_val=palette_seed)
        bg_image.save(str(cover_png_path))

        # 2. Render exact metadata using PyMuPDF HTML box over canvas for flawless Bengali font shaping
        doc = pymupdf.open()
        page = doc.new_page(width=595.0, height=842.0)

        # Insert background artwork image onto full page rect
        rect_full = pymupdf.Rect(0, 0, 595.0, 842.0)
        page.insert_image(rect_full, filename=str(cover_png_path))

        archive = pymupdf.Archive(str(self.font_path.parent))

        translator_display = book.translator.strip() if book.translator.strip() else "Assigned Translator"

        css = f"""
        <style>
        @font-face {{
            font-family: CoverFont;
            src: url({self.font_path.name});
        }}
        .cover-box {{
            font-family: CoverFont;
            text-align: center;
            color: #ffffff;
            padding: 20px;
        }}
        .cover-title {{
            font-size: 30pt;
            font-weight: bold;
            color: #fceabb;
            margin-bottom: 15px;
            line-height: 1.3;
        }}
        .cover-author {{
            font-size: 18pt;
            color: #e2e8f0;
            margin-bottom: 25px;
            letter-spacing: 1px;
        }}
        .cover-divider {{
            width: 80px;
            height: 2px;
            background-color: #d4af37;
            margin: 20px auto;
        }}
        .cover-translator {{
            font-size: 14pt;
            color: #cbd5e1;
            margin-top: 30px;
            font-style: italic;
        }}
        </style>
        """

        html_content = f"""
        {css}
        <div class="cover-box">
            <div style="height: 120px;"></div>
            <div class="cover-title">{book.title.upper()}</div>
            <div class="cover-divider"></div>
            <div class="cover-author">{book.author}</div>
            <div style="height: 320px;"></div>
            <div class="cover-translator">Translated by<br/><b>{translator_display}</b></div>
        </div>
        """

        cover_rect = pymupdf.Rect(40, 40, 555, 802)
        page.insert_htmlbox(cover_rect, html_content, archive=archive)

        doc.save(str(cover_pdf_path))

        # Render combined page to high resolution PNG for cover image preview
        pix = page.get_pixmap(dpi=150)
        pix.save(str(cover_png_path))

        doc.close()

        # Update book record status
        book.cover_image_path = str(cover_png_path)
        book.cover_status = CoverStatus.GENERATED
        book.update_timestamp()

        logger.info(f"Generated book cover for '{book.title}' at {cover_png_path}")
        return cover_png_path, cover_pdf_path
