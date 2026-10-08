import { apiClient } from './client';

export interface Project { id: string; name: string; }

export const getProjects = () => apiClient<Project[]>('/projects');
export const getProject = (id: string) => apiClient<Project>(`/projects/${id}`);
export const createProject = (data: Partial<Project>) => apiClient<Project>('/projects', { method: 'POST', body: JSON.stringify(data) });