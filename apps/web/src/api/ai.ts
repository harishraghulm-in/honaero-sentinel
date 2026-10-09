import { apiClient } from './client';

export interface AIModel {
  id: string;
  name: string;
  provider: 'NVIDIA_NIM' | 'OTHER';
  available: boolean;
}

export interface AIResponse<T> {
  suggestionId: string;
  modelUsed: string;
  content: T;
  confidenceScore?: number;
  disclaimer: string;
}

export interface FaultInjectionSuggestion {
  targetLine: number;
  faultType: string;
  codeModification: string;
  rationale: string;
}

export const getAvailableModels = () => apiClient<AIModel[]>('/ai/models');
export const setPreferredModel = (projectId: string, modelId: string) => apiClient<void>(`/projects/${projectId}/ai/model`, { method: 'PUT', body: JSON.stringify({ modelId }) });

export const extractRequirements = (projectId: string, sourceId: string) => apiClient<AIResponse<string[]>>(`/projects/${projectId}/ai/requirements`, { method: 'POST', body: JSON.stringify({ sourceId }) });
export const suggestFaultInjections = (projectId: string, functionId: string) => apiClient<AIResponse<FaultInjectionSuggestion[]>>(`/projects/${projectId}/ai/faults`, { method: 'POST', body: JSON.stringify({ functionId }) });
export const explainFailure = (projectId: string, executionId: string) => apiClient<AIResponse<string>>(`/projects/${projectId}/ai/explain`, { method: 'POST', body: JSON.stringify({ executionId }) });
export const recommendStubs = (projectId: string) => apiClient<AIResponse<any[]>>(`/projects/${projectId}/ai/stubs`, { method: 'POST' });
export const generateAIReport = (projectId: string) => apiClient<AIResponse<string>>(`/projects/${projectId}/ai/report`, { method: 'POST' });

