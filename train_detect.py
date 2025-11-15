import argparse
from ultralytics import YOLO
from pdf2image import convert_from_path
import os


def train_model(
    data_path="data.yaml",
    model_name="yolov8n.pt",
    epochs=30,
    imgsz=640,
    project="runs_custom",
    name="sign_stamp_qr"
):
    model = YOLO(model_name)
    model.train(
        data=data_path,
        epochs=epochs,
        imgsz=imgsz,
        project=project,
        name=name,
        exist_ok=True
    )
    print("\n✅ Обучение закончено.")
    print(f"Модель лежит в: {project}/{name}/weights/best.pt")


def run_inference_on_images(
    weights_path,
    source,
    imgsz=640,
    conf=0.4,
    save_dir="inference_results"
):
    model = YOLO(weights_path)
    model.predict(
        source=source,
        imgsz=imgsz,
        conf=conf,
        save=True,
        project=save_dir,
        name="pred",
        exist_ok=True
    )
    print("\n✅ Инференс завершён.")
    print(f"Результаты сохранены в: {save_dir}/pred")


def run_inference_on_pdf(
    weights_path,
    pdf_path,
    imgsz=640,
    conf=0.4,
    save_dir="inference_results_pdf",
    dpi=200
):
    pages = convert_from_path(pdf_path, dpi=dpi)
    tmp_dir = "tmp_pdf_pages"
    os.makedirs(tmp_dir, exist_ok=True)

    image_paths = []
    for i, page in enumerate(pages):
        img_path = os.path.join(tmp_dir, f"page_{i+1}.jpg")
        page.save(img_path, "JPEG")
        image_paths.append(img_path)

    model = YOLO(weights_path)
    model.predict(
        source=image_paths,
        imgsz=imgsz,
        conf=conf,
        save=True,
        project=save_dir,
        name="pred",
        exist_ok=True
    )
    print("\n✅ Инференс по PDF завершён.")
    print(f"Размеченные страницы лежат в: {save_dir}/pred")


def main():
    parser = argparse.ArgumentParser(description="Train & run YOLO for signatures/stamps/QR")
    subparsers = parser.add_subparsers(dest="command", help="Команда")

    train_parser = subparsers.add_parser("train", help="Обучить модель")
    train_parser.add_argument("--data", type=str, default="data.yaml")
    train_parser.add_argument("--model", type=str, default="yolov8n.pt")
    train_parser.add_argument("--epochs", type=int, default=30)
    train_parser.add_argument("--imgsz", type=int, default=640)
    train_parser.add_argument("--project", type=str, default="runs_custom")
    train_parser.add_argument("--name", type=str, default="sign_stamp_qr")

    infer_img_parser = subparsers.add_parser("infer_img", help="Инференс на изображении/папке")
    infer_img_parser.add_argument("--weights", type=str, required=True)
    infer_img_parser.add_argument("--source", type=str, required=True)
    infer_img_parser.add_argument("--imgsz", type=int, default=640)
    infer_img_parser.add_argument("--conf", type=float, default=0.4)
    infer_img_parser.add_argument("--save_dir", type=str, default="inference_results")

    infer_pdf_parser = subparsers.add_parser("infer_pdf", help="Инференс на PDF")
    infer_pdf_parser.add_argument("--weights", type=str, required=True)
    infer_pdf_parser.add_argument("--pdf", type=str, required=True)
    infer_pdf_parser.add_argument("--imgsz", type=int, default=640)
    infer_pdf_parser.add_argument("--conf", type=float, default=0.4)
    infer_pdf_parser.add_argument("--save_dir", type=str, default="inference_results_pdf")
    infer_pdf_parser.add_argument("--dpi", type=int, default=200)

    args = parser.parse_args()

    if args.command == "train":
        train_model(
            data_path=args.data,
            model_name=args.model,
            epochs=args.epochs,
            imgsz=args.imgsz,
            project=args.project,
            name=args.name,
        )
    elif args.command == "infer_img":
        run_inference_on_images(
            weights_path=args.weights,
            source=args.source,
            imgsz=args.imgsz,
            conf=args.conf,
            save_dir=args.save_dir
        )
    elif args.command == "infer_pdf":
        run_inference_on_pdf(
            weights_path=args.weights,
            pdf_path=args.pdf,
            imgsz=args.imgsz,
            conf=args.conf,
            save_dir=args.save_dir,
            dpi=args.dpi
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
