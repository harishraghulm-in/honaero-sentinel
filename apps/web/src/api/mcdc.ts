import { apiClient } from './client';

export interface MCDC { conditions: { id: string; description: string; evaluated: boolean }[]; gapAdvisor?: { suggestedVector: any } }

export const getMcdc = (projectId: string, executionId: string) => apiClient<MCDC>(`/projects/${projectId}/executions/${executionId}/mcdc`);