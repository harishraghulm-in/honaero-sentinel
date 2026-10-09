import { apiClient } from './client';

export interface Execution { id: string; status: 'QUEUED' | 'BUILDING' | 'RUNNING' | 'PASS' | 'FAIL' | 'ERROR' | 'CANCELLED'; }

export const createExecution = (projectId: string, payload: any) => apiClient<Execution>(`/projects/${projectId}/executions`, { method: 'POST', body: JSON.stringify(payload) });
export const getExecution = (projectId: string, id: string) => apiClient<Execution>(`/projects/${projectId}/executions/${id}`);