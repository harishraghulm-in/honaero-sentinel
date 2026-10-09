import { apiClient } from './client';

export interface AIModel {
  id: string;
  name: string;
  provider: 'NVIDIA_NIM' | string;
  available: boolean;
  contextWindow?: number;
  description?: string;
}

export interface AIProviderStatus {
  provider: string;
  isConfigured: boolean;
  baseUrl: string;
  activeModel: string;
  liveCallTested: boolean;
  details: Record<string, any>;
}

export interface AIResponse<T> {
  suggestionId: string;
  modelUsed: string;
  isLiveCall?: boolean;
  content: T;
  confidenceScore?: number;
  disclaimer: string;
  timestamp?: string;
}

export interface AIRequirementProposal {
  proposalId: string;
  identifier: string;
  title: string;
  description: string;
  section?: string;
  parameters: string[];
  constraints: string[];
  expectedBehavior: string;
  boundaryConditions: string[];
  provenance: 'EXPLICIT_REQUIREMENT' | 'DERIVED_FROM_SOURCE' | 'TESTER_CONSTRAINT' | 'AI_INFERRED';
  uncertainties: string[];
  status: 'PROPOSED' | 'APPROVED' | 'REJECTED' | 'EDITED';
}

export interface AITestCaseProposal {
  proposalId: string;
  name: string;
  targetFunctionId?: string;
  targetFunctionName?: string;
  category: string;
  inputs: Record<string, any>;
  expectedOutputs: Record<string, any>;
  hasApprovedOracle: boolean;
  rationale: string;
  requirementIds: string[];
  suggestedAssertions?: any[];
  uncertainties: string[];
  provenance: string;
  status: 'PROPOSED' | 'APPROVED' | 'REJECTED' | 'EDITED';
}

export interface AIScenarioStep {
  stepIndex: number;
  flightPhase: string;
  inputs: Record<string, any>;
  expectedState: string;
  durationSeconds: number;
}

export interface AIScenarioSequenceProposal {
  proposalId: string;
  scenarioName: string;
  targetFunction: string;
  flightPhase: string;
  steps: AIScenarioStep[];
  rationale: string;
  status: 'PROPOSED' | 'APPROVED' | 'REJECTED';
}

export interface AIFaultInjectionProposal {
  proposalId: string;
  targetFunction: string;
  faultType: string;
  targetParameter: string;
  faultParameters: Record<string, any>;
  rationale: string;
  impactAnalysis: string;
  status: 'PROPOSED' | 'APPROVED' | 'REJECTED';
}

export interface AIFailureExplanation {
  executionId: string;
  verdict: string;
  observedEvidence: Record<string, any>;
  possibleCauses: string[];
  suggestedRemediation: string[];
  confidenceScore: number;
  supportingLogReferences: string[];
}

export interface AICoverageGapRecommendation {
  gapId: string;
  decisionId: string;
  conditionId?: string;
  sourceLocation: string;
  uncoveredOutcome: string;
  gapDescription: string;
  proposedVector: Record<string, any>;
  targetedBranch: string;
  rationale: string;
  uncertainty?: string;
}

export interface AIAdaptiveRetestProposal {
  originalExecutionId: string;
  investigationGoal: string;
  diagnosticTestProposals: AITestCaseProposal[];
  rationale: string;
}

export interface AITestSuiteOptimization {
  totalTestsBefore: number;
  recommendedTestsAfter: number;
  redundantTestIds: string[];
  essentialTestIds: string[];
  preservedCategories: string[];
  rationale: string;
  estimatedExecutionTimeReductionPct: number;
}

export interface AITraceabilityProposal {
  proposalId: string;
  requirementId: string;
  functionId: string;
  testCaseId?: string;
  confidenceScore: number;
  rationale: string;
  status: 'PROPOSED' | 'APPROVED' | 'REJECTED';
}

export interface AIEnvironmentRecommendation {
  recommendedFlags: string[];
  recommendedDefines: string[];
  recommendedIncludeDirs: string[];
  stubsNeeded: string[];
  sanitizersRecommended: string[];
  rationale: string;
}

// Client API Calls
export const getAvailableModels = () => apiClient<AIModel[]>('/ai/models');
export const getAIStatus = () => apiClient<AIProviderStatus>('/ai/status');
export const setPreferredModel = (projectId: string, modelId: string) =>
  apiClient<{ status: string; modelId: string }>(`/projects/${projectId}/ai/model`, {
    method: 'PUT',
    body: JSON.stringify({ modelId }),
  });

export const extractRequirements = (projectId: string, sourceId?: string, document?: string) =>
  apiClient<AIResponse<AIRequirementProposal[]>>(`/projects/${projectId}/ai/requirements`, {
    method: 'POST',
    body: JSON.stringify({ sourceId, document }),
  });

export const approveRequirement = (projectId: string, payload: {
  proposalId: string;
  identifier: string;
  title: string;
  description: string;
  section?: string;
  acceptanceCriteria?: string;
}) =>
  apiClient<{ status: string; requirementId: string; identifier: string }>(
    `/projects/${projectId}/ai/requirements/approve`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    }
  );

export const generateTestProposals = (projectId: string, functionId?: string, category: string = 'ALL') =>
  apiClient<AIResponse<AITestCaseProposal[]>>(`/projects/${projectId}/ai/test-proposals`, {
    method: 'POST',
    body: JSON.stringify({ functionId, category }),
  });

export const approveTestProposal = (projectId: string, payload: {
  proposalId: string;
  testSuiteId?: string;
  targetFunctionId?: string;
  name: string;
  inputs: Record<string, any>;
  expectedOutputs: Record<string, any>;
}) =>
  apiClient<{ status: string; testCaseId: string; name: string }>(
    `/projects/${projectId}/ai/test-proposals/approve`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    }
  );

export const generateScenarios = (projectId: string, functionId?: string, flightPhase: string = 'ALL') =>
  apiClient<AIResponse<AIScenarioSequenceProposal[]>>(`/projects/${projectId}/ai/scenarios`, {
    method: 'POST',
    body: JSON.stringify({ functionId, flightPhase }),
  });

export const suggestFaultInjections = (projectId: string, functionId?: string) =>
  apiClient<AIResponse<AIFaultInjectionProposal[]>>(`/projects/${projectId}/ai/faults`, {
    method: 'POST',
    body: JSON.stringify({ functionId }),
  });

export const explainFailure = (projectId: string, executionId?: string, failure_logs?: string) =>
  apiClient<AIResponse<AIFailureExplanation>>(`/projects/${projectId}/ai/explain`, {
    method: 'POST',
    body: JSON.stringify({ executionId, failure_logs }),
  });

export const recommendCoverageGaps = (projectId: string, executionId?: string) =>
  apiClient<AIResponse<AICoverageGapRecommendation[]>>(
    `/projects/${projectId}/ai/coverage-gaps${executionId ? `?executionId=${executionId}` : ''}`,
    {
      method: 'POST',
    }
  );

export const generateAdaptiveRetest = (projectId: string, executionId?: string) =>
  apiClient<AIResponse<AIAdaptiveRetestProposal>>(`/projects/${projectId}/ai/adaptive-retest`, {
    method: 'POST',
    body: JSON.stringify({ executionId }),
  });

export const optimizeTestSuite = (projectId: string) =>
  apiClient<AIResponse<AITestSuiteOptimization>>(`/projects/${projectId}/ai/test-suite-optimization`, {
    method: 'POST',
  });

export const suggestTraceability = (projectId: string) =>
  apiClient<AIResponse<AITraceabilityProposal[]>>(`/projects/${projectId}/ai/traceability-suggestions`, {
    method: 'POST',
  });

export const recommendEnvironment = (projectId: string) =>
  apiClient<AIResponse<AIEnvironmentRecommendation>>(`/projects/${projectId}/ai/environment-recommendations`, {
    method: 'POST',
  });

export const generateAIReport = (projectId: string) =>
  apiClient<AIResponse<string>>(`/projects/${projectId}/ai/report`, { method: 'POST' });
