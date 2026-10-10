import { apiClient } from './client';

export interface TestSuite {
  id: string;
  name: string;
  description?: string;
}

export interface TestCaseInput {
  name: string;
  value: string | number | boolean;
  type?: string;
  range?: { min: number; max: number };
}

export interface TestCaseExpectedResult {
  name: string;
  value: string | number | boolean;
  assertion: 'eq' | 'neq' | 'gt' | 'lt' | 'gte' | 'lte' | 'approx';
}

export interface TestCase {
  id: string;
  suiteId: string;
  functionId: string;
  name: string;
  inputs: TestCaseInput[];
  expectedResults: TestCaseExpectedResult[];
}

export const getTestSuites = (projectId: string) => apiClient<TestSuite[]>(`/projects/${projectId}/test-suites`);
export const createTestSuite = (projectId: string, data: Partial<TestSuite>) => apiClient<TestSuite>(`/projects/${projectId}/test-suites`, { method: 'POST', body: JSON.stringify(data) });

export const getTestCases = (projectId: string, suiteId?: string) => {
  const url = suiteId ? `/projects/${projectId}/test-cases?suiteId=${suiteId}` : `/projects/${projectId}/test-cases`;
  return apiClient<TestCase[]>(url);
};

export const createTestCase = (projectId: string, data: Partial<TestCase>) => apiClient<TestCase>(`/projects/${projectId}/test-cases`, { method: 'POST', body: JSON.stringify(data) });
export const updateTestCase = (projectId: string, testCaseId: string, data: Partial<TestCase>) => apiClient<TestCase>(`/projects/${projectId}/test-cases/${testCaseId}`, { method: 'PUT', body: JSON.stringify(data) });
export const deleteTestCase = (projectId: string, testCaseId: string) => apiClient<void>(`/projects/${projectId}/test-cases/${testCaseId}`, { method: 'DELETE' });

export const suggestTestCases = (projectId: string, functionId: string) => apiClient<TestCase[]>(`/projects/${projectId}/suggest-tests`, { method: 'POST', body: JSON.stringify({ functionId }) });