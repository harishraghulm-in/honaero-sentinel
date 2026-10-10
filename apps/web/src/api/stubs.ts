import { apiClient } from './client';

export interface Stub {
  id: string;
  dependencyId: string;
  functionName: string;
  logic: string;
  type: 'mock' | 'fake' | 'proxy';
}

export const getStubs = (projectId: string) => apiClient<Stub[]>(`/projects/${projectId}/stubs`);
export const createStub = (projectId: string, data: Partial<Stub>) => apiClient<Stub>(`/projects/${projectId}/stubs`, { method: 'POST', body: JSON.stringify(data) });
export const updateStub = (projectId: string, stubId: string, data: Partial<Stub>) => apiClient<Stub>(`/projects/${projectId}/stubs/${stubId}`, { method: 'PUT', body: JSON.stringify(data) });
export const deleteStub = (projectId: string, stubId: string) => apiClient<void>(`/projects/${projectId}/stubs/${stubId}`, { method: 'DELETE' });