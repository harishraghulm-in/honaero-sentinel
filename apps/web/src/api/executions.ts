import { apiClient } from './client';

export interface Execution {
  id: string;
  status: 'QUEUED' | 'BUILDING' | 'RUNNING' | 'PASS' | 'FAIL' | 'ERROR' | 'CANCELLED';
  testCaseId?: string;
  expectedResult?: string;
  actualResult?: string;
  logs?: string;
  compilerOutput?: string;
  exitCode?: number;
  crashed?: boolean;
  timeout?: boolean;
  timestamp?: string;
}

export interface ExecutionComparison {
  regressionCount: number;
  fixedCount: number;
  diffs: any[];
}

export const createExecution = (projectId: string, payload: any) => apiClient<Execution>(`/projects/${projectId}/executions`, { method: 'POST', body: JSON.stringify(payload) });
export const getExecution = (projectId: string, id: string) => apiClient<Execution>(`/projects/${projectId}/executions/${id}`);
export const getExecutions = (projectId: string) => apiClient<Execution[]>(`/projects/${projectId}/executions`);
export const compareExecutions = (projectId: string, idA: string, idB: string) => apiClient<ExecutionComparison>(`/projects/${projectId}/executions/compare?base=${idA}&target=${idB}`);