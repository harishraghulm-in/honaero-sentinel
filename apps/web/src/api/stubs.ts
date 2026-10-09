import { apiClient } from './client';

export interface Stub { id: string; functionName: string; logic: string; }

export const getStubs = (projectId: string) => apiClient<Stub[]>(`/projects/${projectId}/stubs`);
export const createStub = (projectId: string, data: Partial<Stub>) => apiClient<Stub>(`/projects/${projectId}/stubs`, { method: 'POST', body: JSON.stringify(data) });