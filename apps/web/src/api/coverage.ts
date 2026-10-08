import { apiClient } from './client';

export interface Coverage { statement: number; decision: number; }

export const getCoverage = (projectId: string, executionId: string) => apiClient<Coverage>(`/projects/${projectId}/executions/${executionId}/coverage`);