import { apiClient } from './client';

export interface Dependency { id: string; name: string; }

export const getDependencies = (projectId: string) => apiClient<Dependency[]>(`/projects/${projectId}/dependencies`);
export const createDependency = (projectId: string, data: Partial<Dependency>) => apiClient<Dependency>(`/projects/${projectId}/dependencies`, { method: 'POST', body: JSON.stringify(data) });