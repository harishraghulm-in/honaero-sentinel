import { apiClient } from './client';

export interface Diagnostic {
  id: string;
  file: string;
  line: number;
  column: number;
  severity: 'error' | 'warning' | 'info';
  message: string;
}

export interface DataType {
  id: string;
  name: string;
  type: string;
}

export interface FunctionNode {
  id: string;
  name: string;
  signature: string;
  file: string;
  startLine: number;
  endLine: number;
}

export interface AnalysisJob {
  status: 'queued' | 'running' | 'completed' | 'failed';
  progress: number; // 0 to 100
  currentFile?: string;
  currentLine?: number;
}

export interface AnalysisResult {
  id: string;
  job: AnalysisJob;
  functions: FunctionNode[];
  dataTypes: DataType[];
  diagnostics: Diagnostic[];
}

export const analyzeProject = (projectId: string) => apiClient<{ execution_id: string }>(`/projects/${projectId}/analyze`, { method: 'POST' });
export const getAnalysis = (projectId: string) => apiClient<AnalysisResult>(`/projects/${projectId}/analysis`);