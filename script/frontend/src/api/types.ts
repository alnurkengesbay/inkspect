export type Detection = {
  label: string;
  confidence: number;
  bbox: [number, number, number, number];
};

export type QRDetection = {
  text: string;
  polygon: [number, number][];
};

export type PageResult = {
  page_name: string;
  source_url: string | null;
  annotated_url: string | null;
  heatmap_url: string | null;
  detections: Detection[];
  qr_codes: QRDetection[];
  requires_review: boolean;
};

export type JobSummary = {
  signature: boolean;
  stamp: boolean;
  qr: boolean;
};

export type Job = {
  job_id: string;
  status: "pending" | "running" | "completed" | "failed";
  created_at: string;
  completed_at: string | null;
  summary: JobSummary;
  pages: PageResult[];
  error?: string | null;
};
