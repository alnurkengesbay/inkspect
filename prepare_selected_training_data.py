import json
import shutil
from pathlib import Path
from typing import Dict, List

from PIL import Image


CLASS_MAP = {"signature": 0, "stamp": 1, "qr": 2}


def load_annotations(path: Path) -> Dict[str, Dict[str, Dict]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def convert_annotations(
    annotations_path: Path,
    images_root: Path,
    target_images: Path,
    target_labels: Path,
) -> None:
    annotations = load_annotations(annotations_path)
    target_images.mkdir(parents=True, exist_ok=True)
    target_labels.mkdir(parents=True, exist_ok=True)

    for pdf_name, pages in annotations.items():
        pdf_stem = Path(pdf_name).stem
        pdf_dir = images_root / pdf_stem
        if not pdf_dir.exists():
            print(f"[warn] Images for {pdf_name} not found in {pdf_dir}")
            continue

        for page_key, info in pages.items():
            try:
                page_index = int(page_key.split("_")[-1])
            except ValueError:
                print(f"[warn] Unexpected page key format: {page_key}")
                continue

            source_image = pdf_dir / f"page_{page_index:03d}.jpg"
            if not source_image.exists():
                print(f"[warn] Missing image: {source_image}")
                continue

            target_name = f"{pdf_stem}_page_{page_index:03d}"
            target_image_path = target_images / f"{target_name}.jpg"
            target_label_path = target_labels / f"{target_name}.txt"

            shutil.copy2(source_image, target_image_path)

            page_size = info.get("page_size", {})
            page_width = float(page_size.get("width", 1.0))
            page_height = float(page_size.get("height", 1.0))

            with Image.open(target_image_path) as img:
                img_width, img_height = img.size

            scale_x = img_width / page_width
            scale_y = img_height / page_height

            lines: List[str] = []
            for annotation_entry in info.get("annotations", []):
                annotation = next(iter(annotation_entry.values()))
                category = annotation.get("category")
                if category not in CLASS_MAP:
                    print(f"[warn] Unknown category {category} in {target_name}")
                    continue
                bbox = annotation.get("bbox", {})
                x = float(bbox.get("x", 0.0))
                y = float(bbox.get("y", 0.0))
                width = float(bbox.get("width", 0.0))
                height = float(bbox.get("height", 0.0))

                center_x = (x + width / 2.0) * scale_x
                center_y = (y + height / 2.0) * scale_y
                abs_width = width * scale_x
                abs_height = height * scale_y

                norm_x = center_x / img_width
                norm_y = center_y / img_height
                norm_w = abs_width / img_width
                norm_h = abs_height / img_height

                class_id = CLASS_MAP[category]
                lines.append(
                    f"{class_id} {norm_x:.6f} {norm_y:.6f} {norm_w:.6f} {norm_h:.6f}"
                )

            target_label_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    project_root = Path(__file__).resolve().parent
    annotations_path = project_root / "selected_annotations.json"
    images_root = project_root / "pdfs_jpeg"
    target_images = project_root / "dataset" / "images" / "annotated_pdfs"
    target_labels = project_root / "dataset" / "labels" / "annotated_pdfs"

    convert_annotations(annotations_path, images_root, target_images, target_labels)
    print("Done. Converted annotations copied into dataset/images/annotated_pdfs")


if __name__ == "__main__":
    main()
