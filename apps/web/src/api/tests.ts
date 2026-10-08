import { apiClient } from './client';

export interface TestSuite { id: string; name: string; }
export interface TestCase { id: string; suiteId: string; vector: any; }

export const getTestSuites = (projectId: string) => apiClient<TestSuite[]>(`/projects/${projectId}/test-suites`);
export const createTestSuite = (projectId: string, data: Partial<TestSuite>) => apiClient<TestSuite>(`/projects/${projectId}/test-suites`, { method: 'POST', body: JSON.stringify(data) });
export const getTestCases = (projectId: string) => apiClient<TestCase[]>(`/projects/${projectId}/test-cases`);
export const createTestCase = (projectId: string, data: Partial<TestCase>) => apiClient<TestCase>(`/projects/${projectId}/test-cases`, { method: 'POST', body: JSON.stringify(data) });