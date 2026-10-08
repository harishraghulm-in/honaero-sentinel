import { apiClient } from './client';

export interface Traceability { links: { reqId: string; description: string }[]; }

export const getTraceability = (projectId: string) => apiClient<Traceability>(`/projects/${projectId}/traceability`);