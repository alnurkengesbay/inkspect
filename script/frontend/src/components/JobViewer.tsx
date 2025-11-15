import clsx from "clsx";
import { ChangeEvent, FC, Fragment, useEffect, useMemo, useState } from "react";

import type { Job, PageResult } from "../api/types";
import { ConfidenceBadge } from "./ConfidenceBadge";

type JobViewerProps = {
  job: Job | null;
};

const MIN_DISPLAY_CONFIDENCE = 0.35;
const SECTION_BADGE_STYLE: Record<string, string> = {
  danger: "bg-danger/20 text-danger",
  success: "bg-success/20 text-success"
};
type SectionTone = keyof typeof SECTION_BADGE_STYLE;
type SectionBlock = {
  key: string;
  title: string;
  tone: SectionTone;
  pages: PageResult[];
};

type DocumentGroup = {
  name: string;
  pages: PageResult[];
};

export function JobViewer({ job }: JobViewerProps) {
  const [viewHeatmap, setViewHeatmap] = useState(false);
  const [activeDoc, setActiveDoc] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  useEffect(() => {
    setActiveDoc(null);
    setPreviewUrl(null);
  }, [job?.job_id]);

  const pages = job?.pages ?? [];
  const documents = useMemo(() => groupByDocument(pages), [pages]);
  const selectedDoc = activeDoc ?? documents[0]?.name ?? null;
  const activePages = useMemo(() => {
    if (!selectedDoc) {
      return [];
    }
    return documents.find((doc) => doc.name === selectedDoc)?.pages ?? [];
  }, [selectedDoc, documents]);

  const { reviewPages, autoPages } = useMemo(() => splitPages(activePages), [activePages]);
  const sections = useMemo<SectionBlock[]>(
    () =>
      [
        { key: "review", title: "Требуют проверки", tone: "danger", pages: reviewPages },
        { key: "auto", title: "Обработано автоматически", tone: "success", pages: autoPages }
      ].filter((section) => section.pages.length > 0),
    [reviewPages, autoPages]
  );

  if (!job) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900 p-6 text-sm text-slate-400">
        Выберите задачу, чтобы увидеть результаты распознавания.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-100">Документы ({documents.length})</h2>
          <p className="text-xs text-slate-400">
            Выберите документ, чтобы увидеть все страницы и разметку.
          </p>
        </div>
        <label className="flex items-center gap-2 text-sm text-slate-300">
          <input
            type="checkbox"
            className="accent-accent"
            checked={viewHeatmap}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              setViewHeatmap(event.target.checked)
            }
          />
          Показать heatmap
        </label>
      </div>

      <div className="grid gap-4 lg:grid-cols-[300px_minmax(0,1fr)]">
        <aside className="min-w-0 rounded-lg border border-slate-800 bg-slate-900 p-3 text-sm text-slate-200">
          {documents.length === 0 && <p className="text-slate-400">Документов нет.</p>}
          {documents.map((doc) => {
            const total = doc.pages.length;
            const reviewCount = doc.pages.filter((page) => page.requires_review).length;
            return (
              <Fragment key={doc.name}>
                <button
                  type="button"
                  onClick={() => setActiveDoc(doc.name)}
                  className={clsx(
                    "flex w-full min-w-0 flex-col gap-1 rounded px-3 py-2 text-left transition",
                    selectedDoc === doc.name
                      ? "bg-slate-800 text-slate-100"
                      : "hover:bg-slate-800/60 text-slate-300"
                  )}
                >
                  <span className="break-words font-semibold" title={doc.name}>
                    {doc.name}
                  </span>
                  <span className="text-xs text-slate-400">
                    Страниц: {total} • Требует проверки: {reviewCount}
                  </span>
                </button>
              </Fragment>
            );
          })}
        </aside>

  <section className="min-w-0 space-y-4">
          {sections.length === 0 && (
            <div className="rounded-lg border border-slate-800 bg-slate-900 p-6 text-sm text-slate-400">
              Страницы отсутствуют.
            </div>
          )}

          {sections.map((section) => (
            <div key={section.key} className="space-y-4">
              <div className="flex items-center justify-between text-sm text-slate-300">
                <h3 className="text-base font-semibold text-slate-100">
                  {section.title} ({section.pages.length})
                </h3>
                <span
                  className={clsx(
                    "rounded px-2 py-1 text-xs font-semibold",
                    SECTION_BADGE_STYLE[section.tone]
                  )}
                >
                  {section.tone === "danger" ? "Требует проверки" : "Авто"}
                </span>
              </div>
              <div className="grid gap-4 sm:grid-cols-2 2xl:grid-cols-3">
                {section.pages.map((page: PageResult) => (
                  <PageCard
                    key={page.page_name}
                    page={page}
                    showHeatmap={viewHeatmap}
                    onPreview={setPreviewUrl}
                  />
                ))}
              </div>
            </div>
          ))}
        </section>
      </div>

      {previewUrl && (
        <button
          type="button"
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/90 p-6"
          onClick={() => setPreviewUrl(null)}
        >
          <img
            src={previewUrl}
            alt="preview"
            className="max-h-[90vh] max-w-[90vw] rounded-xl border border-slate-700 bg-slate-900 object-contain shadow-2xl"
          />
        </button>
      )}
    </div>
  );
}

function deriveDocumentName(page: PageResult): string {
  if (page.source_url) {
    const parts = page.source_url.split("/").filter(Boolean);
    const pagesIndex = parts.indexOf("pages");
    if (pagesIndex >= 0 && pagesIndex < parts.length - 1) {
      const docParts = parts.slice(pagesIndex + 1, parts.length - 1);
      if (docParts.length > 0) {
        return docParts.join("/");
      }
      return parts[parts.length - 1].replace(/\.[^./]+$/, "");
    }
  }
  return page.page_name.replace(/\.[^./]+$/, "");
}

function groupByDocument(pages: PageResult[]): DocumentGroup[] {
  const buckets = pages.reduce<Record<string, PageResult[]>>((acc, page) => {
    const name = deriveDocumentName(page);
    if (!acc[name]) {
      acc[name] = [];
    }
    acc[name].push(page);
    return acc;
  }, {});
  return Object.entries(buckets)
    .map(([name, docPages]) => ({
      name,
      pages: docPages.sort((a, b) => a.page_name.localeCompare(b.page_name))
    }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

function splitPages(pages: PageResult[]) {
  const sorted = [...pages].sort((a, b) => a.page_name.localeCompare(b.page_name));
  return {
    reviewPages: sorted.filter((page) => page.requires_review),
    autoPages: sorted.filter((page) => !page.requires_review)
  };
}

type PageCardProps = {
  page: PageResult;
  showHeatmap: boolean;
  onPreview: (url: string | null) => void;
};

const PageCard: FC<PageCardProps> = ({ page, showHeatmap, onPreview }: PageCardProps) => {
  const imageUrl = showHeatmap ? page.heatmap_url ?? page.annotated_url : page.annotated_url;
  const filteredDetections = useMemo(
    () =>
      page.detections.filter((det) => det.confidence >= MIN_DISPLAY_CONFIDENCE),
    [page.detections]
  );
  const showEmpty = page.detections.length === 0 && page.qr_codes.length === 0;

  return (
    <div className="flex h-full flex-col rounded-xl border border-slate-800 bg-slate-900 shadow-lg">
      <div className="flex items-center justify-between gap-3 border-b border-slate-800 px-4 py-2 text-sm text-slate-300">
        <span className="truncate font-semibold text-slate-100" title={page.page_name}>
          {page.page_name}
        </span>
      </div>
      {imageUrl ? (
        <img
          src={imageUrl}
          alt={page.page_name}
          className="max-h-[420px] w-full cursor-zoom-in bg-slate-950 object-contain"
          onClick={() => onPreview(imageUrl)}
        />
      ) : (
        <div className="p-6 text-center text-sm text-slate-400">Нет визуализации</div>
      )}
      <div className="space-y-3 border-t border-slate-800 p-4 text-sm text-slate-200">
        {showEmpty && <p className="text-slate-400">Объекты не найдены.</p>}
        {filteredDetections.map((det: PageResult["detections"][number]) => (
          <div
            key={`${det.label}-${det.bbox.join("-")}`}
            className="flex items-center justify-between gap-3"
          >
            <div className="min-w-0">
              <p className="truncate font-medium text-slate-100" title={det.label}>
                {det.label}
              </p>
              <p className="text-xs text-slate-400" title={`BBox: ${det.bbox.join(", ")}`}>
                BBox: {det.bbox.join(", ")}
              </p>
            </div>
            <ConfidenceBadge confidence={det.confidence} />
          </div>
        ))}
        {page.qr_codes.map((qr: PageResult["qr_codes"][number]) => (
          <div
            key={qr.text}
            className="rounded border border-slate-700 bg-slate-900/60 p-3"
          >
            <p className="text-xs uppercase tracking-wide text-slate-400">QR</p>
            <p className="mt-1 break-words text-sm text-slate-100" title={qr.text}>
              {qr.text}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};
