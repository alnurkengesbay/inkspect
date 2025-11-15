from __future__ import annotations

from pathlib import Path
from typing import List

from pdf2image import convert_from_path

from app.core.config import settings


def pdf_to_images(pdf_path: Path, output_dir: Path, dpi: int = 200) -> List[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    kwargs = {"dpi": dpi}
    if settings.poppler_path:
        kwargs["poppler_path"] = str(settings.poppler_path)
    pages = convert_from_path(str(pdf_path), **kwargs)
    image_paths: List[Path] = []
    for index, page in enumerate(pages, start=1):
        out_path = output_dir / f"page_{index:03d}.jpg"
        page.save(out_path, "JPEG")
        image_paths.append(out_path)
    return image_paths
