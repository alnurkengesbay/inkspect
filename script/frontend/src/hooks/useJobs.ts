import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../api/client";
import type { Job } from "../api/types";

const JOBS_KEY = ["jobs"] as const;

export function useJobs() {
  const client = useQueryClient();

  const jobsQuery = useQuery({
    queryKey: JOBS_KEY,
    queryFn: async () => {
      const response = await api.get<Job[]>("/jobs");
      return response.data;
    },
    refetchInterval: 4000
  });

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      const response = await api.post<Job>("/jobs", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      return response.data;
    },
    onSuccess: () => {
      client.invalidateQueries({ queryKey: JOBS_KEY });
    }
  });

  return {
    jobsQuery,
    uploadMutation
  };
}
