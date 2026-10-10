export type DalLevel = 'DAL-A' | 'DAL-B' | 'DAL-C' | 'DAL-D' | 'Unknown';

export type FileVerificationStatus = 'idle' | 'running' | 'passed' | 'failed' | 'blocked';

export type RunStatus = 'idle' | 'running' | 'completed' | 'paused' | 'cancelled';

export interface ProjectStats {
  discoveredFiles: number;
  totalFunctions: number;
  requirementCount: number;
  testCaseCount: number;
  passRate: number;
  mcDcCoverage: number;
  compilationErrors: number;
  runtimeErrors: number;
}

export interface Project {
  id: string;
  name: string;
  codeName: string;
  description: string;
  dalLevel: DalLevel;
  branch: string;
  toolchain: string;
  stats: ProjectStats;
  isBackendConnected: boolean;
  indexedTimestamp: string;
}

export interface ProjectFile {
  id: string;
  name: string;
  path: string;
  directory: string;
  language: 'C' | 'C++' | 'Header' | 'Ada';
  linesCount: number;
  functionsCount: number;
  priorityScore: number; // 0.00 - 1.00
  criticality: DalLevel;
  cyclomaticComplexity: number;
  coveragePercent: number;
  status: FileVerificationStatus;
  scoreReliability?: 'computed' | 'estimated';
  priorityRationale: {
    summary: string;
    determinismType: 'deterministic' | 'ai_heuristic' | 'hybrid';
    factors: string[];
  };
  content: string;
}

export interface Requirement {
  id: string;
  title: string;
  standard: 'DO-178C' | 'DO-254';
  criticality: DalLevel;
  description: string;
  documentSource: string;
  page: number;
  linkedFileIds: string[];
  linkedTestIds: string[];
  reviewStatus: 'Approved' | 'Under Review' | 'Draft';
  coverageStatus: 'Fully Covered' | 'Partially Covered' | 'Uncovered';
}

export interface TestVectorField {
  name: string;
  label: string;
  type: 'float' | 'int' | 'boolean' | 'enum' | 'string';
  currentValue: string | number | boolean;
  unit?: string;
  min?: number;
  max?: number;
  enumOptions?: string[];
  description: string;
  isBoundaryCase?: boolean;
}

export interface TestCase {
  id: string;
  title: string;
  requirementId: string;
  fileId: string;
  objective: string;
  preconditions: string;
  vectorSchema: TestVectorField[];
  expectedResult: string;
  boundaryCases: string[];
  isNegativeTest: boolean;
  status: 'approved' | 'proposal' | 'rejected';
  lastRunStatus: 'passed' | 'failed' | 'not_run';
  observedResult?: string;
  executionDurationMs?: number;
  sourceFunction: string;
}

export interface ExecutionEvent {
  id: string;
  timestamp: string;
  type: 'run_started' | 'file_queued' | 'compilation_started' | 'compilation_passed' | 'test_started' | 'test_passed' | 'test_failed' | 'diagnostic' | 'coverage' | 'run_completed' | 'run_cancelled';
  message: string;
  fileId?: string;
  fileName?: string;
  testId?: string;
  line?: number;
  severity: 'info' | 'warning' | 'error' | 'success';
  isSimulation: boolean;
}

export interface Diagnostic {
  id: string;
  severity: 'fatal' | 'error' | 'warning' | 'info';
  category: 'assertion_failure' | 'compiler_error' | 'runtime_crash' | 'coverage_gap' | 'boundary_overflow' | 'toolchain_failure';
  filePath: string;
  line: number;
  column?: number;
  functionName?: string;
  testId?: string;
  requirementId?: string;
  message: string;
  rawTrace: string;
  timestamp: string;
}

export type TestFlowPreference = 'ai_recommended' | 'custom_order';

export interface TestedVectorResult {
  testId: string;
  testTitle: string;
  requirementId: string;
  passed: boolean;
  inputsUsed: Record<string, any>;
  expectedOutput: string;
  observedOutput: string;
  executionMs: number;
  assertionLine?: number;
}

export interface PerFileExecutionReport {
  fileId: string;
  fileName: string;
  filePath: string;
  criticality: DalLevel;
  totalTests: number;
  passedTests: number;
  failedTests: number;
  linesTotal: number;
  linesExecuted: number;
  coverageAchieved: number;
  savedErrors: Diagnostic[];
  testedVectors: TestedVectorResult[];
  status: 'passed' | 'failed';
  completedTimestamp: string;
}

export interface VerificationReportSummary {
  runId: string;
  timestamp: string;
  durationMs: number;
  targetPlatform: string;
  toolchain: string;
  filesDiscovered: number;
  filesTested: number;
  testsPassed: number;
  testsFailed: number;
  testsBlocked: number;
  testsSkipped: number;
  testsUntested: number;
  statementCoverage: number;
  branchCoverage: number;
  mcDcCoverage: number;
  status: 'PASSED' | 'FAILED' | 'INCOMPLETE';
  perFileReports?: PerFileExecutionReport[];
}
