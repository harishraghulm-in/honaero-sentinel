import { apiClient } from './client';

export interface Evidence { freshness: 'CURRENT' | 'STALE' | 'INVALIDATED'; generatedAt: string; }

export const getEvidence = (projectId: string) => apiClient<Evidence>(`/projects/${projectId}/evidence`);
export const exportEvidence = (projectId: string) => apiClient<any>(`/projects/${projectId}/evidence/export`);