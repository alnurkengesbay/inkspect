import argparse
import os
import re
from pathlib import Path

from pdf2image import convert_from_path


def convert_pdf_to_jpeg(
    pdf_path: Path,
    output_root: Path,
    dpi: int = 200,
    poppler_path: Path | None = None,
) -> None:
    """Split a PDF into JPEG pages; multi-page PDFs get a dedicated folder."""
    if not pdf_path.exists() or not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    poppler_bin = poppler_path or _detect_poppler_from_env()
    poppler_kwargs = {"poppler_path": str(poppler_bin)} if poppler_bin else {}

    pages = convert_from_path(str(pdf_path), dpi=dpi, **poppler_kwargs)
    if not pages:
        print(f"⚠️ Файл пустой: {pdf_path}")
        return

    # Multi-page PDFs go into a folder named after the PDF file.
    output_root = output_root or pdf_path.parent
    target_dir = output_root / pdf_path.stem
    target_dir.mkdir(parents=True, exist_ok=True)

    for index, page in enumerate(pages, start=1):
        jpeg_path = target_dir / f"page_{index:03d}.jpg"
        page.save(jpeg_path, "JPEG")

    print(f"\n✅ Сохранено страниц: {len(pages)}")
    print(f"🗂️ Файлы лежат в: {target_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert PDFs into JPEG pages"
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to a PDF file or directory containing PDFs",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Root output folder (defaults to alongside each PDF)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="Rendering DPI for PDF pages (default: 200)",
    )
    parser.add_argument(
        "--poppler",
        type=Path,
        default=None,
        help="Path to Poppler bin directory (defaults to POPPLER_PATH env)",
    )
    return parser.parse_args()


def handle_path(path: Path, output_root: Path, dpi: int, poppler: Path | None) -> None:
    if path.is_file() and path.suffix.lower() == ".pdf":
        convert_pdf_to_jpeg(path, output_root, dpi, poppler)
    elif path.is_dir():
        pdf_files = sorted(
            (p for p in path.iterdir() if p.suffix.lower() == ".pdf"),
            key=_natural_key,
        )
        if not pdf_files:
            print(f"⚠️ PDF не найден в каталоге: {path}")
            return
        for pdf_file in pdf_files:
            convert_pdf_to_jpeg(pdf_file, output_root, dpi, poppler)
    else:
        raise FileNotFoundError(f"Путь должен указывать на PDF или каталог: {path}")


def main() -> None:
    args = parse_args()
    handle_path(args.input, args.out, args.dpi, args.poppler)


def _detect_poppler_from_env() -> Path | None:
    env_path = os.environ.get("POPPLER_PATH")
    if not env_path:
        return None
    path = Path(env_path)
    if path.exists():
        return path
    print(f"⚠️ POPPLER_PATH указан, но путь не найден: {path}")
    return None


_natural_pattern = re.compile(r"(\d+)")


def _natural_key(path: Path) -> tuple:
    parts = _natural_pattern.split(path.stem.lower())
    key = []
    for part in parts:
        if part.isdigit():
            key.append(int(part))
        else:
            key.append(part)
    return tuple(key)


if __name__ == "__main__":
    main()
