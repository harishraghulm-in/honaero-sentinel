import { apiClient } from './client';

export interface AnalysisResult { id: string; functions: any[]; }

export const analyzeProject = (projectId: string) => apiClient<AnalysisResult>(`/projects/${projectId}/analyze`, { method: 'POST' });
export const getAnalysis = (projectId: string) => apiClient<AnalysisResult>(`/projects/${projectId}/analysis`);