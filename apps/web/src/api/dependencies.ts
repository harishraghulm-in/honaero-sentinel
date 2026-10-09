import { apiClient } from './client';

export interface Dependency {
  id: string;
  name: string;
  type: 'function' | 'global_variable' | 'type';
  file: string;
  isResolved: boolean;
}

export const getDependencies = (projectId: string) => apiClient<Dependency[]>(`/projects/${projectId}/dependencies`);
export const createDependency = (projectId: string, data: Partial<Dependency>) => apiClient<Dependency>(`/projects/${projectId}/dependencies`, { method: 'POST', body: JSON.stringify(data) });
export const updateDependency = (projectId: string, depId: string, data: Partial<Dependency>) => apiClient<Dependency>(`/projects/${projectId}/dependencies/${depId}`, { method: 'PUT', body: JSON.stringify(data) });