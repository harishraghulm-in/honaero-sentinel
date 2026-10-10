import { apiClient } from './client';

export interface Coverage {
  statement?: number;
  branch?: number;
  function?: number;
  available: boolean;
}

export const getCoverage = (projectId: string, executionId: string) => apiClient<Coverage>(`/projects/${projectId}/executions/${executionId}/coverage`);