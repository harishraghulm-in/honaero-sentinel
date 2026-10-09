import { apiClient } from './client';

export interface CompilerConfig {
  compiler: string;
  version: string;
  flags: string[];
  includePaths: string[];
  buildProfile: 'debug' | 'release' | 'coverage';
}

export const getCompilerConfig = (projectId: string) => apiClient<CompilerConfig>(`/projects/${projectId}/config`);
export const updateCompilerConfig = (projectId: string, data: Partial<CompilerConfig>) => apiClient<CompilerConfig>(`/projects/${projectId}/config`, { method: 'PUT', body: JSON.stringify(data) });

