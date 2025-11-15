import { ChangeEvent, useRef } from "react";

const ACCEPT = ".pdf,.png,.jpg,.jpeg,.bmp,.tif,.tiff,.zip";

type UploadPanelProps = {
  onUpload: (file: File) => void;
  isUploading: boolean;
  error: string | null;
};

export function UploadPanel({ onUpload, isUploading, error }: UploadPanelProps) {
  const fileInput = useRef<HTMLInputElement | null>(null);

  const onSelectFile = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      onUpload(file);
      event.target.value = "";
    }
  };

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 p-6 shadow-xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">Новый анализ</h2>
          <p className="mt-1 text-sm text-slate-300">
            Загрузите PDF, изображение или ZIP-архив. Файлы будут автоматически разбиты по страницам и проанализированы.
          </p>
        </div>
        <button
          type="button"
          className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white shadow hover:bg-blue-500"
          onClick={() => fileInput.current?.click()}
          disabled={isUploading}
        >
          {isUploading ? "Загрузка..." : "Выбрать файл"}
        </button>
      </div>
      <input
        ref={fileInput}
        type="file"
        accept={ACCEPT}
        onChange={onSelectFile}
        className="hidden"
      />
      {error && (
        <p className="mt-3 text-sm text-danger">
          Ошибка загрузки: {error}
        </p>
      )}
    </div>
  );
}
