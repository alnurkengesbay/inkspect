import clsx from "clsx";

import type { Job } from "../api/types";
import { formatDistanceToNow } from "../utils/dates";

type JobTableProps = {
  jobs: Job[];
  selectedId: string | null;
  onSelect: (job: Job) => void;
};

const STATUS_STYLE: Record<Job["status"], string> = {
  pending: "bg-yellow-500/20 text-yellow-200",
  running: "bg-blue-500/20 text-blue-200",
  completed: "bg-success/20 text-success",
  failed: "bg-danger/20 text-danger"
};

export function JobTable({ jobs, selectedId, onSelect }: JobTableProps) {
  const renderPresence = (value: boolean) => (
    <span
      className={clsx(
        "inline-flex items-center rounded px-2 py-1 text-xs font-semibold",
        value ? "bg-success/20 text-success" : "bg-slate-700/50 text-slate-300"
      )}
    >
      {value ? "Есть" : "Нет"}
    </span>
  );

  return (
    <div className="overflow-hidden rounded-lg border border-slate-800 bg-slate-900">
      <table className="min-w-full table-fixed divide-y divide-slate-800">
        <thead className="bg-slate-800/60 text-left text-xs uppercase tracking-wide text-slate-400">
          <tr>
            <th className="w-24 px-4 py-3">Файл</th>
            <th className="w-28 px-4 py-3">Статус</th>
            <th className="w-24 px-4 py-3">Подписи</th>
            <th className="w-24 px-4 py-3">Печати</th>
            <th className="w-20 px-4 py-3">QR</th>
            <th className="px-4 py-3">Обновлено</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800 text-sm text-slate-200">
          {jobs.map((job) => (
            <tr
              key={job.job_id}
              className={clsx(
                "cursor-pointer transition hover:bg-slate-800/60",
                selectedId === job.job_id && "bg-slate-800"
              )}
              onClick={() => onSelect(job)}
            >
              <td className="px-4 py-3 font-medium text-slate-100">
                <span className="block truncate" title={job.job_id}>
                  {job.job_id.slice(0, 12)}
                </span>
              </td>
              <td className="px-4 py-3">
                <span
                  className={clsx(
                    "block truncate rounded px-2 py-1 text-center text-xs font-semibold",
                    STATUS_STYLE[job.status]
                  )}
                  title={job.status}
                >
                  {job.status.toUpperCase()}
                </span>
              </td>
              <td className="px-4 py-3">{renderPresence(job.summary.signature)}</td>
              <td className="px-4 py-3">{renderPresence(job.summary.stamp)}</td>
              <td className="px-4 py-3">{renderPresence(job.summary.qr)}</td>
              <td className="px-4 py-3 text-slate-400">
                <span className="block truncate" title={formatDistanceToNow(job.completed_at ?? job.created_at)}>
                  {formatDistanceToNow(job.completed_at ?? job.created_at)}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {jobs.length === 0 && (
        <div className="p-6 text-center text-sm text-slate-400">
          Загрузите первый документ, чтобы увидеть результаты анализа.
        </div>
      )}
    </div>
  );
}
