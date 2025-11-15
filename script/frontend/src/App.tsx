import { useCallback, useEffect, useMemo, useState } from "react";

import type { Job } from "./api/types";
import { JobTable } from "./components/JobTable";
import { JobViewer } from "./components/JobViewer";
import { UploadPanel } from "./components/UploadPanel";
import { useJobs } from "./hooks/useJobs";

export default function App() {
  const { jobsQuery, uploadMutation } = useJobs();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const jobs = jobsQuery.data ?? [];

  useEffect(() => {
    if (jobs.length === 0) {
      if (selectedId !== null) {
        setSelectedId(null);
      }
      return;
    }

  const hasSelection = selectedId ? jobs.some((job) => job.job_id === selectedId) : false;
    if (!hasSelection) {
      const latest = [...jobs].sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      )[0];
      setSelectedId(latest.job_id);
    }
  }, [jobs, selectedId]);

  const selectedJob = useMemo(() => {
    if (!selectedId) {
      return null;
    }
    return jobs.find((job) => job.job_id === selectedId) ?? null;
  }, [jobs, selectedId]);

  const handleSelect = useCallback((job: Job) => {
    setSelectedId(job.job_id);
  }, []);

  const uploadError = uploadMutation.isError ? describeError(uploadMutation.error) : null;
  const listError = jobsQuery.isError ? describeError(jobsQuery.error) : null;

  const handleUpload = useCallback(
    (file: File) => {
      uploadMutation.mutate(file);
    },
    [uploadMutation]
  );

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-8 sm:px-6 lg:px-8">
        <header className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wider text-accent">DocScan pipeline</p>
            <h1 className="text-3xl font-bold text-white">Панель аналитики документов</h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-300">
              Загружайте документы, отслеживайте состояние обработки, просматривайте распознанные подписи,
              печати и QR-коды, а также оценивайте тепловые карты для страниц, требующих проверки.
            </p>
          </div>
          <div className="flex gap-3 text-sm text-slate-400">
            {jobsQuery.isFetching ? (
              <span className="animate-pulse text-accent">Обновление данных…</span>
            ) : (
              <span>Всего задач: {jobs.length}</span>
            )}
          </div>
        </header>

        <UploadPanel
          onUpload={handleUpload}
          isUploading={uploadMutation.isPending}
          error={uploadError}
        />

        {listError && (
          <div className="rounded-md border border-danger/40 bg-danger/15 p-3 text-sm text-danger">
            Не удалось получить список задач: {listError}
          </div>
        )}

        <section className="flex flex-col gap-6">
          <div className="flex flex-col gap-4">
            {jobsQuery.isLoading && (
              <div className="rounded-lg border border-slate-800 bg-slate-900 p-6 text-sm text-slate-400">
                Загрузка задач…
              </div>
            )}
            <JobTable jobs={jobs} selectedId={selectedId} onSelect={handleSelect} />
          </div>
          {selectedJob && <JobViewer job={selectedJob} />}
        </section>
      </div>
    </div>
  );
}

function describeError(error: unknown): string {
  if (!error) {
    return "";
  }

  if (typeof error === "string") {
    return error;
  }

  if (error instanceof Error) {
    return error.message;
  }

  if (typeof error === "object" && error !== null) {
    if ("message" in error && typeof (error as { message?: unknown }).message === "string") {
      return (error as { message: string }).message;
    }
  }

  return "Произошла неизвестная ошибка";
}
