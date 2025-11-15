from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path
from typing import Iterable, List

SUPPORTED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
SUPPORTED_PDF_EXT = ".pdf"


def extract_zip(archive_path: Path, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "r") as archive:
        archive.extractall(target_dir)
    return target_dir


def iter_supported_files(root: Path) -> Iterable[Path]:
    candidates: List[Path] = []
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_EXTS.union({SUPPORTED_PDF_EXT}):
            candidates.append(path)
    for path in sorted(candidates, key=lambda p: _natural_key(p.relative_to(root).as_posix())):
        yield path


def copy_file(src: Path, dst: Path) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    return Path(shutil.copy2(src, dst))


def is_pdf(path: Path) -> bool:
    return path.suffix.lower() == SUPPORTED_PDF_EXT


def is_image(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_IMAGE_EXTS


_natural_pattern = re.compile(r"(\d+)")


def _natural_key(value: str) -> tuple:
    parts = _natural_pattern.split(value.lower())
    key = []
    for part in parts:
        if part.isdigit():
            key.append(int(part))
        else:
            key.append(part)
    return tuple(key)
