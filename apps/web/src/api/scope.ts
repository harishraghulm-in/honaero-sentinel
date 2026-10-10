import { apiClient } from './client';

export interface Scope { id: string; selectedFunctions: string[]; }

export const getScope = (projectId: string) => apiClient<Scope>(`/projects/${projectId}/scope`);
export const updateScope = (projectId: string, data: Scope) => apiClient<Scope>(`/projects/${projectId}/scope`, { method: 'PUT', body: JSON.stringify(data) });