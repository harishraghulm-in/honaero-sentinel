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

export interface AnalysisParameter {
  name: string;
  type: string;
}

export interface AnalysisCondition {
  id: string;
  expression: string;
  variable_references?: string[];
}

export interface AnalysisDecision {
  id: string;
  expression: string;
  line_number?: number;
  conditions?: AnalysisCondition[];
}

export interface FunctionNode {
  id: string;
  name: string;
  return_type?: string;
  signature?: string;
  file?: string;
  startLine?: number;
  endLine?: number;
  parameters?: AnalysisParameter[];
  decisions?: AnalysisDecision[];
  is_target_under_test?: boolean;
}

export interface AnalysisJob {
  status: 'queued' | 'running' | 'completed' | 'failed';
  progress: number; // 0 to 100
  currentFile?: string;
  currentLine?: number;
}

export interface AnalysisResult {
  id?: string;
  project_id?: string;
  total_sources?: number;
  job?: AnalysisJob;
  functions?: FunctionNode[];
  dependencies?: any[];
  dataTypes?: DataType[];
  diagnostics?: Diagnostic[];
}

export const analyzeProject = (projectId: string) => apiClient<{ execution_id: string }>(`/projects/${projectId}/analyze`, { method: 'POST' });
export const getAnalysis = (projectId: string) => apiClient<AnalysisResult>(`/projects/${projectId}/analysis`);