import { apiClient } from './client';

export interface Source { id: string; filename: string; content: string; }

export const getSources = (projectId: string) => apiClient<Source[]>(`/projects/${projectId}/sources`);
export const createSource = (projectId: string, data: Partial<Source>) => apiClient<Source>(`/projects/${projectId}/sources`, { method: 'POST', body: JSON.stringify(data) });