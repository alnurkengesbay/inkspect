import clsx from "clsx";

type ConfidenceBadgeProps = {
  confidence: number;
};

export function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  const level =
    confidence >= 0.8 ? "high" : confidence >= 0.5 ? "medium" : "low";

  return (
    <span
      className={clsx("rounded px-2 py-1 text-xs font-semibold", {
        "bg-success/20 text-success": level === "high",
        "bg-yellow-500/20 text-yellow-200": level === "medium",
        "bg-danger/20 text-danger": level === "low"
      })}
    >
      {(confidence * 100).toFixed(0)}%
    </span>
  );
}
