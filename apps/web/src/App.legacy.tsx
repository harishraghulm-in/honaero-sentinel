import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import Editor, { useMonaco } from '@monaco-editor/react';
import {
  Target, AlertTriangle, CheckCircle, Play, Code, Beaker, Folder, Search,
  Activity, PlaySquare, Network, FileText, X, Settings, Box, RefreshCw,
  GitCompare, ShieldCheck, Download, Bot, Layers, Check, ExternalLink, HelpCircle
} from 'lucide-react';
import { getProjects, createProject } from './api/projects';
import { getSources } from './api/sources';
import { getAnalysis, analyzeProject } from './api/analysis';
import { getTestCases, getTestSuites, suggestTestCases } from './api/tests';
import { getExecution, createExecution, getExecutions, compareExecutions, rerunExecution } from './api/executions';
import { getCoverage } from './api/coverage';
import { getMcdc } from './api/mcdc';
import { getEvidence } from './api/evidence';
import { getCompilerConfig, updateCompilerConfig, type CompilerConfig } from './api/config';
import {
  getAvailableModels,
  getAIStatus,
  setPreferredModel,
  extractRequirements,
  approveRequirement,
  generateTestProposals,
  approveTestProposal,
  generateScenarios,
  suggestFaultInjections,
  explainFailure,
  recommendCoverageGaps,
  generateAdaptiveRetest,
  optimizeTestSuite,
  suggestTraceability,
  recommendEnvironment,
  generateAIReport,
} from './api/ai';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useStudioStore } from './store/studio';

const vectorSchema = z.object({ pressure: z.number().int(), altitude: z.number().int() });
type TestVector = z.infer<typeof vectorSchema>;

export default function App() {
  const {
    activePane, setActivePane,
    bottomPanelOpen, setBottomPanelOpen,
    bottomPanelTab, setBottomPanelTab,
    executionId, setExecutionId,
    projectId, setProjectId,
    selectedSourceId, setSelectedSourceId,
  } = useStudioStore();

  const editorRef = useRef<any>(null);
  const monaco = useMonaco();
  const decorationsRef = useRef<string[]>([]);
  const [panelHeight, setPanelHeight] = useState(250);

  // Modals state
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [showAiModal, setShowAiModal] = useState(false);
  const [showCompareModal, setShowCompareModal] = useState(false);
  const [compareBaseId, setCompareBaseId] = useState<string>('');
  const [compareTargetId, setCompareTargetId] = useState<string>('');
  const [compareResult, setCompareResult] = useState<any>(null);
  const [aiPromptType, setAiPromptType] = useState<string>('requirements');
  const [aiOutput, setAiOutput] = useState<any>(null);
  const [aiLoading, setAiLoading] = useState<boolean>(false);
  const [selectedAiModel, setSelectedAiModel] = useState<string>('meta/llama-3.3-70b-instruct');
  const [aiActionMessage, setAiActionMessage] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Config modal state
  const [cfgFlags, setCfgFlags] = useState<string>('-O0 -g --coverage -fprofile-arcs -ftest-coverage');
  const [cfgProfile, setCfgProfile] = useState<'debug' | 'release' | 'coverage'>('coverage');

  // Fallback active pane
  useEffect(() => {
    if (!['explorer', 'search', 'analysis', 'tests', 'runs', 'coverage', 'reports'].includes(activePane)) {
      setActivePane('explorer');
    }
  }, [activePane, setActivePane]);

  // Queries
  const { data: projects, refetch: refetchProjects } = useQuery({ queryKey: ['projects'], queryFn: () => getProjects(), retry: false });
  const { data: sources, isLoading: sourcesLoading, refetch: refetchSources } = useQuery({ queryKey: ['sources', projectId], queryFn: () => getSources(projectId!), enabled: !!projectId, retry: false });
  const { data: aiModels } = useQuery({ queryKey: ['aiModels'], queryFn: () => getAvailableModels(), retry: false });
  const { data: aiStatus, refetch: refetchAiStatus } = useQuery({ queryKey: ['aiStatus'], queryFn: () => getAIStatus(), retry: false });

  const createProjectMutation = useMutation({
    mutationFn: (name: string) => createProject({ name }),
    onSuccess: (data) => { setProjectId(data.id); refetchProjects(); setActivePane('explorer'); }
  });

  const { data: analysis, refetch: refetchAnalysis } = useQuery({
    queryKey: ['analysis', projectId], queryFn: () => getAnalysis(projectId!),
    enabled: !!projectId,
    refetchInterval: (query) => {
      const status = query.state.data?.job?.status;
      if (status === 'queued' || status === 'running') return 1000;
      return false;
    }, retry: false
  });

  const analyzeProjectMutation = useMutation({
    mutationFn: () => analyzeProject(projectId!),
    onSuccess: () => { refetchAnalysis(); setBottomPanelTab('problems'); }
  });

  const { data: executionsList, refetch: refetchExecutions } = useQuery({
    queryKey: ['executions', projectId],
    queryFn: () => getExecutions(projectId!),
    enabled: !!projectId,
    retry: false
  });

  const { data: execution } = useQuery({
    queryKey: ['execution', projectId, executionId],
    queryFn: () => getExecution(projectId!, executionId!),
    enabled: !!executionId && !!projectId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'QUEUED' || status === 'BUILDING' || status === 'RUNNING') return 1000;
      return false;
    }, retry: false
  });

  const isComplete = execution ? ['PASS', 'FAIL', 'ERROR', 'CANCELLED', 'PASSED', 'FAILED', 'BUILD_FAILED', 'TIMEOUT'].includes(execution.status) : false;
  const { data: coverage } = useQuery({
    queryKey: ['coverage', projectId, executionId],
    queryFn: () => getCoverage(projectId!, executionId!),
    enabled: isComplete && !!projectId,
    retry: false
  });

  const { data: mcdcData } = useQuery({
    queryKey: ['mcdc', projectId, executionId],
    queryFn: () => getMcdc(projectId!, executionId!),
    enabled: isComplete && !!projectId,
    retry: false
  });

  const { data: evidenceData, refetch: refetchEvidence } = useQuery({
    queryKey: ['evidence', projectId],
    queryFn: () => getEvidence(projectId!),
    enabled: !!projectId,
    retry: false
  });

  const { data: testSuites } = useQuery({
    queryKey: ['testSuites', projectId],
    queryFn: () => getTestSuites(projectId!),
    enabled: !!projectId,
    retry: false
  });

  const { data: testCases, refetch: refetchTestCases } = useQuery({
    queryKey: ['testCases', projectId],
    queryFn: () => getTestCases(projectId!),
    enabled: !!projectId,
    retry: false
  });

  const { data: compilerConfig, refetch: refetchConfig } = useQuery({
    queryKey: ['config', projectId],
    queryFn: () => getCompilerConfig(projectId!),
    enabled: !!projectId,
    retry: false
  });

  useEffect(() => {
    if (compilerConfig) {
      setCfgFlags(compilerConfig.flags?.join(' ') || '-O0 -g --coverage -fprofile-arcs -ftest-coverage');
      setCfgProfile(compilerConfig.buildProfile || 'coverage');
    }
  }, [compilerConfig]);

  const executeMutation = useMutation({
    mutationFn: (vector: TestVector) => createExecution(projectId!, vector),
    onSuccess: (data) => {
      if (data && data.id) {
        setExecutionId(data.id);
        setBottomPanelTab('test-results');
        refetchExecutions();
        refetchEvidence();
      }
    }
  });

  const rerunMutation = useMutation({
    mutationFn: (id: string) => rerunExecution(projectId!, id),
    onSuccess: (data) => {
      if (data && data.id) {
        setExecutionId(data.id);
        setBottomPanelTab('test-results');
        refetchExecutions();
        refetchEvidence();
      }
    }
  });

  const suggestTestsMutation = useMutation({
    mutationFn: () => suggestTestCases(projectId!, ''),
    onSuccess: () => {
      refetchTestCases();
      refetchExecutions();
    }
  });

  const updateConfigMutation = useMutation({
    mutationFn: (data: Partial<CompilerConfig>) => updateCompilerConfig(projectId!, data),
    onSuccess: () => {
      refetchConfig();
      setShowConfigModal(false);
    }
  });

  const { register, handleSubmit, setValue } = useForm<TestVector>({
    resolver: zodResolver(vectorSchema),
    defaultValues: { pressure: 950, altitude: 5000 }
  });

  const activeSource = sources?.find(s => s.id === selectedSourceId);

  // Automatically select first source if none selected
  useEffect(() => {
    if (!selectedSourceId && sources && sources.length > 0) {
      setSelectedSourceId(sources[0].id);
    }
  }, [sources, selectedSourceId, setSelectedSourceId]);

  useEffect(() => {
    if (editorRef.current && monaco && analysis?.diagnostics && selectedSourceId) {
      const newDecorations = analysis.diagnostics
        .filter((d: any) => d.file === selectedSourceId)
        .map((d: any) => ({
          range: new monaco.Range(d.line, d.column || 1, d.line, d.column ? d.column + 5 : 100),
          options: {
            isWholeLine: !d.column,
            className: 'diagnostic-marker',
            hoverMessage: { value: `**${d.severity}**: ${d.message}` },
            glyphMarginClassName: 'diagnostic-glyph'
          }
        }));
      decorationsRef.current = editorRef.current.deltaDecorations(decorationsRef.current, newDecorations);
    }
  }, [analysis, selectedSourceId, monaco]);

  const handleDiagnosticClick = (sourceId: string, line: number) => {
    setSelectedSourceId(sourceId);
    if (editorRef.current) {
      editorRef.current.revealLineInCenter(line);
      editorRef.current.setPosition({ lineNumber: line, column: 1 });
    }
  };

  const handleRunComparison = async () => {
    if (!projectId || !compareBaseId || !compareTargetId) return;
    try {
      const res = await compareExecutions(projectId, compareBaseId, compareTargetId);
      setCompareResult(res);
    } catch (err: any) {
      setCompareResult({ error: err.message });
    }
  };

  const handleTriggerAi = async () => {
    if (!projectId) return;
    setAiLoading(true);
    setAiOutput(null);
    setAiActionMessage('');
    try {
      let res: any = null;
      if (aiPromptType === 'requirements') {
        res = await extractRequirements(projectId, selectedSourceId || undefined);
      } else if (aiPromptType === 'tests') {
        res = await generateTestProposals(projectId, '');
      } else if (aiPromptType === 'scenarios') {
        res = await generateScenarios(projectId, '');
      } else if (aiPromptType === 'faults') {
        res = await suggestFaultInjections(projectId, '');
      } else if (aiPromptType === 'explain') {
        res = await explainFailure(projectId, executionId || '');
      } else if (aiPromptType === 'coverage-gaps') {
        res = await recommendCoverageGaps(projectId, executionId || undefined);
      } else if (aiPromptType === 'adaptive-retest') {
        res = await generateAdaptiveRetest(projectId, executionId || undefined);
      } else if (aiPromptType === 'optimize') {
        res = await optimizeTestSuite(projectId);
      } else if (aiPromptType === 'traceability') {
        res = await suggestTraceability(projectId);
      } else if (aiPromptType === 'environment') {
        res = await recommendEnvironment(projectId);
      } else if (aiPromptType === 'report') {
        res = await generateAIReport(projectId);
      }
      setAiOutput(res);
    } catch (err: any) {
      setAiOutput({ content: `Error: ${err.message}` });
    } finally {
      setAiLoading(false);
    }
  };

  const handleApproveRequirement = async (req: any) => {
    if (!projectId) return;
    try {
      await approveRequirement(projectId, {
        proposalId: req.proposalId || req.id,
        identifier: req.identifier,
        title: req.title || req.identifier,
        description: req.description,
        section: req.section,
        acceptanceCriteria: req.expectedBehavior,
      });
      setAiActionMessage(`Requirement ${req.identifier} approved and saved into project.`);
    } catch (err: any) {
      setAiActionMessage(`Failed to approve requirement: ${err.message}`);
    }
  };

  const handleApproveTestProposal = async (tc: any) => {
    if (!projectId) return;
    try {
      await approveTestProposal(projectId, {
        proposalId: tc.proposalId || tc.id,
        name: tc.name,
        inputs: tc.inputs || {},
        expectedOutputs: tc.expectedOutputs || {},
        targetFunctionId: tc.targetFunctionId,
        testSuiteId: testSuites && testSuites.length > 0 ? testSuites[0].id : undefined,
      });
      setAiActionMessage(`Test case "${tc.name}" promoted to executable test suite.`);
      refetchTestCases();
    } catch (err: any) {
      setAiActionMessage(`Failed to promote test proposal: ${err.message}`);
    }
  };

  const handleSelectModel = async (modelId: string) => {
    setSelectedAiModel(modelId);
    if (projectId) {
      try {
        await setPreferredModel(projectId, modelId);
      } catch (e) {
        // ignore
      }
    }
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-ide-bg text-ide-text-primary overflow-hidden text-[13px]">
      {/* TOP MENU BAR */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-ide-activity border-b border-ide-border shrink-0">
        <div className="flex items-center gap-4">
          <span className="font-semibold flex items-center gap-2 text-ide-text-primary tracking-wide">
            <Target size={16} className="text-ide-accent" /> HONAERO SENTINEL
          </span>
          <div className="h-4 w-px bg-ide-border"></div>
          <div className="flex items-center gap-2 text-ide-text-secondary hover:text-ide-text-primary cursor-pointer">
            <Box size={14} />
            <select
              value={projectId || ''}
              onChange={(e) => setProjectId(e.target.value)}
              className="bg-ide-panel border border-ide-border rounded px-2 py-0.5 outline-none cursor-pointer text-ide-text-primary"
            >
              <option value="">Select Project ▾</option>
              {projects?.map((p: any) => (
                <option key={p.id} value={p.id}>
                  {p.name || p.id}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => projectId && analyzeProjectMutation.mutate()}
            disabled={!projectId || analyzeProjectMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-1 rounded bg-ide-border hover:bg-ide-elevated text-ide-text-primary transition-colors disabled:opacity-50"
            title="Run deterministic C/C++ AST analysis"
          >
            <Code size={14} /> {analyzeProjectMutation.isPending ? 'Analyzing...' : 'Analyze'}
          </button>
          <button
            onClick={() => {
              if (projectId) {
                setActivePane('tests');
                setBottomPanelOpen(true);
                setBottomPanelTab('test-results');
              }
            }}
            disabled={!projectId}
            className="flex items-center gap-1.5 px-3 py-1 rounded bg-ide-action hover:bg-blue-500 text-white transition-colors disabled:opacity-50"
            title="Configure and run verification test"
          >
            <Play size={14} /> Run Test
          </button>
          <button
            onClick={() => setShowConfigModal(true)}
            disabled={!projectId}
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-ide-panel border border-ide-border text-ide-text-secondary hover:text-ide-text-primary disabled:opacity-50"
            title="Compiler & Toolchain Configuration"
          >
            <Settings size={14} /> Compiler
          </button>
          <button
            onClick={() => setShowAiModal(true)}
            disabled={!projectId}
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-ide-panel border border-ide-border text-ide-accent hover:bg-ide-elevated disabled:opacity-50"
            title="AI Verification Assistant (NVIDIA NIM)"
          >
            <Bot size={14} /> AI Assistant
          </button>
        </div>
      </div>

      {/* MAIN WORKSPACE */}
      <div className="flex flex-1 overflow-hidden">
        {/* ACTIVITY BAR */}
        <div className="w-12 bg-ide-activity flex flex-col items-center py-2 shrink-0 border-r border-ide-border gap-2">
          <ActivityBtn id="explorer" icon={<Folder size={20} />} title="Explorer" activePane={activePane} setActivePane={setActivePane} />
          <ActivityBtn id="analysis" icon={<Activity size={20} />} title="Source Analysis & AST" activePane={activePane} setActivePane={setActivePane} />
          <ActivityBtn id="tests" icon={<Beaker size={20} />} title="Test Cases & Suites" activePane={activePane} setActivePane={setActivePane} />
          <ActivityBtn id="runs" icon={<PlaySquare size={20} />} title="Verification Run History" activePane={activePane} setActivePane={setActivePane} />
          <ActivityBtn id="coverage" icon={<Network size={20} />} title="Coverage & MC/DC" activePane={activePane} setActivePane={setActivePane} />
          <ActivityBtn id="reports" icon={<FileText size={20} />} title="DO-178C Evidence & Reports" activePane={activePane} setActivePane={setActivePane} />
          <ActivityBtn id="search" icon={<Search size={20} />} title="Search" activePane={activePane} setActivePane={setActivePane} />
        </div>

        {/* SIDEBAR */}
        <div className="w-72 bg-ide-sidebar border-r border-ide-border flex flex-col shrink-0 overflow-hidden">
          <div className="px-4 py-2 font-medium tracking-wide text-[11px] uppercase text-ide-text-secondary border-b border-ide-border">
            {activePane}
          </div>
          <div className="flex-1 overflow-y-auto px-3 py-2 space-y-4">
            {/* EXPLORER PANE */}
            {activePane === 'explorer' && (
              <div className="space-y-4">
                {!projectId ? (
                  <div className="p-3 text-ide-text-secondary text-center">
                    <p className="mb-3">No project selected.</p>
                    <button
                      onClick={() => createProjectMutation.mutate('Cabin Pressure Controller')}
                      className="bg-ide-accent text-ide-bg px-3 py-1.5 rounded w-full font-medium"
                    >
                      Create Project
                    </button>
                  </div>
                ) : (
                  <div>
                    <div className="text-xs font-semibold mb-2 px-1 text-ide-text-secondary">PROJECT SOURCES</div>
                    {sourcesLoading ? (
                      <div className="px-2 text-ide-text-secondary">Loading sources...</div>
                    ) : (
                      sources?.map((s: any) => (
                        <div
                          key={s.id}
                          onClick={() => setSelectedSourceId(s.id)}
                          className={`cursor-pointer px-2 py-1.5 rounded flex items-center justify-between mb-1 ${
                            selectedSourceId === s.id ? 'bg-ide-elevated text-ide-accent font-medium' : 'hover:bg-ide-elevated text-ide-text-primary'
                          }`}
                        >
                          <span className="flex items-center gap-2">
                            <FileText size={14} /> {s.filename}
                          </span>
                          {s.is_target && (
                            <span className="text-[10px] bg-ide-border px-1.5 py-0.5 rounded text-ide-text-secondary">Target</span>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            )}

            {/* ANALYSIS PANE */}
            {activePane === 'analysis' && (
              <div className="space-y-4">
                <button
                  onClick={() => projectId && analyzeProjectMutation.mutate()}
                  disabled={!projectId || analyzeProjectMutation.isPending}
                  className="w-full bg-ide-elevated hover:bg-ide-border px-3 py-2 rounded flex items-center justify-center gap-2 font-medium disabled:opacity-50"
                >
                  <Activity size={14} /> {analyzeProjectMutation.isPending ? 'Analyzing AST...' : 'Run AST Analysis'}
                </button>

                {analysis?.functions && analysis.functions.length > 0 && (
                  <div>
                    <div className="text-xs font-semibold mb-2 text-ide-text-secondary">EXTRACTED FUNCTIONS</div>
                    {analysis.functions.map((fn: any) => (
                      <div key={fn.id} className="p-2 bg-ide-panel border border-ide-border rounded mb-2 space-y-1">
                        <div className="font-mono text-xs text-ide-accent font-semibold flex items-center justify-between">
                          <span>{fn.name}</span>
                          <span className="text-[10px] text-ide-text-secondary font-normal">{fn.return_type}</span>
                        </div>
                        {fn.parameters && fn.parameters.length > 0 && (
                          <div className="text-[11px] text-ide-text-secondary">
                            Params: {fn.parameters.map((p: any) => `${p.type} ${p.name}`).join(', ')}
                          </div>
                        )}
                        {fn.decisions && fn.decisions.length > 0 && (
                          <div className="mt-2 pt-1 border-t border-ide-border text-[11px]">
                            <div className="font-semibold text-ide-text-secondary mb-1">Decisions & Conditions:</div>
                            {fn.decisions.map((d: any) => (
                              <div key={d.id} className="font-mono text-[11px] text-sky-400 bg-ide-bg p-1 rounded mb-1">
                                <div>{d.id}: {d.expression}</div>
                                {d.conditions?.map((c: any) => (
                                  <div key={c.id} className="text-ide-text-secondary text-[10px] pl-2">
                                    • {c.id}: {c.expression}
                                  </div>
                                ))}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {analysis?.dependencies && analysis.dependencies.length > 0 && (
                  <div>
                    <div className="text-xs font-semibold mb-2 text-ide-text-secondary">DEPENDENCIES</div>
                    {analysis.dependencies.map((dep: any) => (
                      <div key={dep.id} className="p-2 bg-ide-panel border border-ide-border rounded mb-1 flex items-center justify-between text-xs">
                        <span className="font-mono">{dep.name}</span>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] ${dep.mode === 'STUB' ? 'bg-amber-900/40 text-amber-300' : 'bg-emerald-900/40 text-emerald-300'}`}>
                          {dep.mode}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* TESTS PANE */}
            {activePane === 'tests' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-semibold text-ide-text-secondary">TEST CASES</div>
                  <button
                    onClick={() => suggestTestsMutation.mutate()}
                    disabled={!projectId || suggestTestsMutation.isPending}
                    className="text-[11px] text-ide-accent hover:underline disabled:opacity-50"
                    title="Synthesize boundary vectors"
                  >
                    + Suggest Vectors
                  </button>
                </div>

                {testCases && testCases.length > 0 && (
                  <div className="space-y-1.5 max-h-48 overflow-y-auto">
                    {testCases.map((tc: any) => (
                      <div
                        key={tc.id}
                        className="p-2 bg-ide-panel border border-ide-border rounded hover:bg-ide-elevated cursor-pointer text-xs"
                        onClick={() => {
                          if (tc.inputs && tc.inputs.length > 0) {
                            for (const inp of tc.inputs) {
                              if (inp.name === 'pressure') setValue('pressure', Number(inp.value));
                              if (inp.name === 'altitude') setValue('altitude', Number(inp.value));
                            }
                          }
                        }}
                      >
                        <div className="font-medium text-ide-text-primary">{tc.name}</div>
                        {tc.inputs && (
                          <div className="text-[11px] text-ide-text-secondary font-mono mt-0.5">
                            {tc.inputs.map((i: any) => `${i.name}=${i.value}`).join(', ')}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                <div className="pt-2 border-t border-ide-border">
                  <div className="text-xs font-semibold mb-2 text-ide-text-secondary">EXECUTE TEST VECTOR</div>
                  <form onSubmit={handleSubmit((d) => executeMutation.mutate(d))} className="space-y-3">
                    <div>
                      <label className="block text-xs mb-1 text-ide-text-secondary">Pressure (hPa)</label>
                      <input
                        type="number"
                        {...register('pressure', { valueAsNumber: true })}
                        className="w-full bg-ide-bg border border-ide-border rounded px-2 py-1 text-ide-text-primary outline-none focus:border-ide-accent font-mono text-xs"
                      />
                    </div>
                    <div>
                      <label className="block text-xs mb-1 text-ide-text-secondary">Altitude (ft)</label>
                      <input
                        type="number"
                        {...register('altitude', { valueAsNumber: true })}
                        className="w-full bg-ide-bg border border-ide-border rounded px-2 py-1 text-ide-text-primary outline-none focus:border-ide-accent font-mono text-xs"
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={!projectId || executeMutation.isPending}
                      className="w-full bg-ide-action hover:bg-blue-500 text-white px-3 py-1.5 rounded font-medium disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                      <Play size={14} /> {executeMutation.isPending ? 'Executing Harness...' : 'Execute Vector'}
                    </button>
                  </form>
                </div>
              </div>
            )}

            {/* RUNS PANE */}
            {activePane === 'runs' && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-semibold text-ide-text-secondary">VERIFICATION RUNS</div>
                  <button
                    onClick={() => {
                      if (executionsList && executionsList.length >= 2) {
                        setCompareBaseId(executionsList[1].id);
                        setCompareTargetId(executionsList[0].id);
                      }
                      setShowCompareModal(true);
                    }}
                    disabled={!executionsList || executionsList.length < 2}
                    className="text-[11px] text-ide-accent hover:underline flex items-center gap-1 disabled:opacity-50"
                  >
                    <GitCompare size={12} /> Compare
                  </button>
                </div>

                {!executionsList || executionsList.length === 0 ? (
                  <p className="text-ide-text-secondary text-xs">No verification runs executed yet.</p>
                ) : (
                  executionsList.map((run: any) => {
                    const isSelected = executionId === run.id;
                    const verdict = run.verdict || (run.status === 'PASSED' ? 'PASS' : run.status === 'FAILED' ? 'FAIL' : 'ERROR');
                    const badgeColor =
                      verdict === 'PASS'
                        ? 'bg-emerald-900/50 text-emerald-300 border-emerald-700'
                        : verdict === 'FAIL'
                        ? 'bg-rose-900/50 text-rose-300 border-rose-700'
                        : 'bg-amber-900/50 text-amber-300 border-amber-700';

                    return (
                      <div
                        key={run.id}
                        onClick={() => {
                          setExecutionId(run.id);
                          setBottomPanelOpen(true);
                          setBottomPanelTab('test-results');
                        }}
                        className={`p-2.5 rounded border cursor-pointer transition-colors ${
                          isSelected ? 'bg-ide-elevated border-ide-accent' : 'bg-ide-panel border-ide-border hover:bg-ide-elevated'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-mono text-xs font-semibold text-ide-text-primary">
                            Run #{run.id?.slice(0, 8)}
                          </span>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${badgeColor}`}>
                            {verdict}
                          </span>
                        </div>
                        <div className="text-[11px] text-ide-text-secondary flex items-center justify-between">
                          <span>{run.created_at ? new Date(run.created_at).toLocaleTimeString() : 'N/A'}</span>
                          <span>{run.duration_ms ? `${Math.round(run.duration_ms)}ms` : ''}</span>
                        </div>
                        <div className="mt-2 flex items-center justify-end">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              rerunMutation.mutate(run.id);
                            }}
                            disabled={rerunMutation.isPending}
                            className="text-[10px] text-ide-accent hover:underline flex items-center gap-1"
                            title="Rerun historical test using recorded inputs creating new run"
                          >
                            <RefreshCw size={10} /> Rerun
                          </button>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            )}

            {/* COVERAGE PANE */}
            {activePane === 'coverage' && (
              <div className="space-y-4">
                <div className="text-xs font-semibold text-ide-text-secondary">STRUCTURAL METRICS</div>
                {!coverage ? (
                  <p className="text-ide-text-secondary text-xs">Run a test to inspect coverage data.</p>
                ) : (
                  <div className="space-y-3">
                    <div className="p-3 bg-ide-panel border border-ide-border rounded">
                      <div className="flex justify-between text-xs mb-1">
                        <span>Statement Coverage</span>
                        <span className="font-bold text-ide-accent">{coverage.statement ?? 0}%</span>
                      </div>
                      <div className="w-full bg-ide-border h-2 rounded overflow-hidden">
                        <div className="bg-ide-accent h-full" style={{ width: `${coverage.statement ?? 0}%` }}></div>
                      </div>
                    </div>

                    <div className="p-3 bg-ide-panel border border-ide-border rounded">
                      <div className="flex justify-between text-xs mb-1">
                        <span>Branch Coverage</span>
                        <span className="font-bold text-ide-accent">{coverage.branch ?? 0}%</span>
                      </div>
                      <div className="w-full bg-ide-border h-2 rounded overflow-hidden">
                        <div className="bg-ide-accent h-full" style={{ width: `${coverage.branch ?? 0}%` }}></div>
                      </div>
                    </div>
                  </div>
                )}

                {mcdcData && (
                  <div className="pt-2 border-t border-ide-border">
                    <div className="text-xs font-semibold mb-2 text-ide-text-secondary">MC/DC CONDITIONS</div>
                    {mcdcData.conditions?.map((c: any) => (
                      <div key={c.id} className="p-2 bg-ide-panel border border-ide-border rounded mb-1 text-xs font-mono">
                        <div className="flex justify-between">
                          <span className="font-bold text-ide-text-primary">{c.id}</span>
                          <span className={c.evaluated ? 'text-emerald-400' : 'text-amber-400'}>
                            {c.evaluated ? 'EVALUATED' : 'UNTESTED'}
                          </span>
                        </div>
                        <div className="text-[11px] text-ide-text-secondary mt-0.5">{c.description}</div>
                      </div>
                    ))}
                    {mcdcData.gapAdvisor && (
                      <div className="mt-3 p-2 bg-amber-950/30 border border-amber-800 rounded text-xs">
                        <div className="font-semibold text-amber-300">MC/DC Gap Advisor</div>
                        <div className="text-[11px] text-amber-200 mt-1">Candidate Vector Recommendation:</div>
                        <pre className="font-mono text-[10px] mt-1 text-ide-text-primary">
                          {JSON.stringify(mcdcData.gapAdvisor.suggestedVector, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* REPORTS PANE */}
            {activePane === 'reports' && (
              <div className="space-y-4">
                <div className="text-xs font-semibold text-ide-text-secondary">DO-178C VERIFICATION EVIDENCE</div>
                {!evidenceData ? (
                  <p className="text-ide-text-secondary text-xs">No evidence records available.</p>
                ) : (
                  <div className="space-y-3">
                    <div className="p-3 bg-ide-panel border border-ide-border rounded space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium">Freshness:</span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            evidenceData.freshness === 'CURRENT'
                              ? 'bg-emerald-900/50 text-emerald-300 border border-emerald-700'
                              : 'bg-amber-900/50 text-amber-300 border border-amber-700'
                          }`}
                        >
                          {evidenceData.freshness}
                        </span>
                      </div>
                      <div className="text-[11px] text-ide-text-secondary">
                        Generated: {evidenceData.generatedAt ? new Date(evidenceData.generatedAt).toLocaleString() : 'N/A'}
                      </div>
                      {evidenceData.source_checksum && (
                        <div className="text-[10px] font-mono text-ide-text-secondary truncate">
                          SHA256: {evidenceData.source_checksum.slice(0, 16)}...
                        </div>
                      )}
                    </div>

                    <div className="space-y-2">
                      <a
                        href={`/api/v1/projects/${projectId}/evidence/export?format=json`}
                        download
                        className="w-full bg-ide-elevated hover:bg-ide-border p-2 rounded flex items-center justify-center gap-2 text-xs font-medium text-ide-text-primary"
                      >
                        <Download size={14} /> Export Evidence JSON
                      </a>
                      <a
                        href={`/api/v1/projects/${projectId}/evidence/export?format=md`}
                        download
                        className="w-full bg-ide-elevated hover:bg-ide-border p-2 rounded flex items-center justify-center gap-2 text-xs font-medium text-ide-text-primary"
                      >
                        <FileText size={14} /> Export DO-178C Markdown
                      </a>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* SEARCH PANE */}
            {activePane === 'search' && (
              <div className="space-y-3">
                <input
                  type="text"
                  placeholder="Search project sources..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-ide-bg border border-ide-border rounded px-2 py-1 text-xs text-ide-text-primary outline-none focus:border-ide-accent"
                />
                {searchQuery && (
                  <div className="text-xs text-ide-text-secondary">
                    {sources
                      ?.filter((s: any) => s.content?.toLowerCase().includes(searchQuery.toLowerCase()))
                      .map((s: any) => (
                        <div
                          key={s.id}
                          onClick={() => setSelectedSourceId(s.id)}
                          className="p-1.5 hover:bg-ide-elevated rounded cursor-pointer"
                        >
                          <div className="font-semibold text-ide-accent">{s.filename}</div>
                          <div className="text-[11px] truncate">Matches query '{searchQuery}'</div>
                        </div>
                      ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* EDITOR & BOTTOM PANEL */}
        <div className="flex flex-col flex-1 overflow-hidden bg-ide-bg">
          {/* EDITOR AREA */}
          <div className="flex-1 flex flex-col overflow-hidden">
            <div className="flex bg-ide-panel border-b border-ide-border shrink-0">
              {activeSource ? (
                <div className="px-4 py-2 border-r border-ide-border bg-ide-bg border-t-2 border-t-ide-accent flex items-center gap-2">
                  <Code size={14} className="text-ide-accent" /> {activeSource.filename}
                </div>
              ) : (
                <div className="px-4 py-2 text-ide-text-secondary">No File Open</div>
              )}
            </div>
            <div className="flex-1 overflow-hidden">
              {activeSource ? (
                <Editor
                  height="100%"
                  defaultLanguage="c"
                  theme="vs-dark"
                  value={activeSource.content}
                  onMount={(editor) => {
                    editorRef.current = editor;
                  }}
                  options={{
                    minimap: { enabled: true, scale: 0.75 },
                    scrollBeyondLastLine: false,
                    fontSize: 13,
                    fontFamily: 'var(--font-mono)',
                  }}
                />
              ) : (
                <div className="h-full flex items-center justify-center text-ide-text-secondary flex-col gap-4">
                  <Target size={48} className="opacity-20" />
                  <p>Select a source file to view</p>
                </div>
              )}
            </div>
          </div>

          {/* BOTTOM PANEL */}
          {bottomPanelOpen && (
            <div style={{ height: panelHeight }} className="flex flex-col shrink-0 border-t border-ide-border bg-ide-panel">
              <div
                className="h-1 cursor-row-resize bg-ide-border hover:bg-ide-accent active:bg-ide-accent w-full shrink-0"
                onMouseDown={(e) => {
                  const startY = e.clientY;
                  const startHeight = panelHeight;
                  const onMouseMove = (moveEvent: MouseEvent) => {
                    const newHeight = Math.max(100, Math.min(600, startHeight - (moveEvent.clientY - startY)));
                    setPanelHeight(newHeight);
                  };
                  const onMouseUp = () => {
                    document.removeEventListener('mousemove', onMouseMove);
                    document.removeEventListener('mouseup', onMouseUp);
                  };
                  document.addEventListener('mousemove', onMouseMove);
                  document.addEventListener('mouseup', onMouseUp);
                }}
              />
              <div className="flex items-center justify-between px-2 bg-ide-panel border-b border-ide-border shrink-0">
                <div className="flex">
                  <PanelTab id="test-results" title="Test Verdict & Results" current={bottomPanelTab} set={setBottomPanelTab} />
                  <PanelTab id="terminal" title="Terminal & Logs" current={bottomPanelTab} set={setBottomPanelTab} />
                  <PanelTab id="problems" title="Problems" current={bottomPanelTab} set={setBottomPanelTab} count={analysis?.diagnostics?.length} />
                  <PanelTab id="coverage" title="Coverage" current={bottomPanelTab} set={setBottomPanelTab} />
                  <PanelTab id="output" title="Output" current={bottomPanelTab} set={setBottomPanelTab} />
                </div>
                <button onClick={() => setBottomPanelOpen(false)} className="p-1 text-ide-text-secondary hover:text-ide-text-primary rounded">
                  <X size={14} />
                </button>
              </div>
              <div className="flex-1 overflow-auto p-3 bg-ide-bg">
                {bottomPanelTab === 'test-results' && (
                  <div>
                    {!execution ? (
                      <p className="text-ide-text-secondary text-xs">No verification run selected. Submit a test vector or select from run history.</p>
                    ) : (
                      <div className="space-y-3">
                        <div className="flex items-center gap-4">
                          <div className="flex items-center gap-2 font-medium text-sm">
                            Verdict:
                            <span
                              className={`px-2.5 py-0.5 rounded font-bold text-xs ${
                                execution.verdict === 'PASS' || execution.status === 'PASS' || execution.status === 'PASSED'
                                  ? 'bg-emerald-900/50 text-emerald-300 border border-emerald-700'
                                  : execution.verdict === 'FAIL' || execution.status === 'FAIL' || execution.status === 'FAILED'
                                  ? 'bg-rose-900/50 text-rose-300 border border-rose-700'
                                  : 'bg-amber-900/50 text-amber-300 border border-amber-700'
                              }`}
                            >
                              {execution.verdict || execution.status}
                            </span>
                          </div>
                          {execution.duration_ms !== undefined && (
                            <span className="text-ide-text-secondary text-xs">Duration: {Math.round(execution.duration_ms)}ms</span>
                          )}
                          {execution.exit_code !== undefined && (
                            <span className="text-ide-text-secondary text-xs">Exit Code: {execution.exit_code}</span>
                          )}
                        </div>

                        {execution.expectedResult !== undefined && (
                          <div className="grid grid-cols-2 gap-4 max-w-lg">
                            <div className="bg-ide-panel border border-ide-border p-2.5 rounded">
                              <span className="text-ide-text-secondary text-[11px] uppercase block mb-1">Expected Output</span>
                              <code className="text-ide-text-primary font-mono text-sm">{execution.expectedResult}</code>
                            </div>
                            <div className="bg-ide-panel border border-ide-border p-2.5 rounded">
                              <span className="text-ide-text-secondary text-[11px] uppercase block mb-1">Actual Output</span>
                              <code className="text-ide-text-primary font-mono text-sm">{execution.actualResult}</code>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {bottomPanelTab === 'terminal' && (
                  <div className="font-mono text-[12px] text-ide-text-secondary space-y-2">
                    <p className="text-ide-accent">{'>'} HONAERO SENTINEL EXECUTION WORKER LOGS</p>
                    {execution?.logs ? (
                      <pre className="whitespace-pre-wrap text-ide-text-primary bg-ide-panel p-2 rounded">{execution.logs}</pre>
                    ) : execution?.compilerOutput ? (
                      <pre className="whitespace-pre-wrap text-amber-300 bg-ide-panel p-2 rounded">{execution.compilerOutput}</pre>
                    ) : (
                      <p className="text-ide-text-secondary">Ready. Test outputs and compiler diagnostics appear here.</p>
                    )}
                  </div>
                )}

                {bottomPanelTab === 'problems' && (
                  <div>
                    {!analysis?.diagnostics?.length ? (
                      <p className="text-ide-text-secondary text-xs">No problems detected.</p>
                    ) : (
                      <div className="space-y-1">
                        {analysis.diagnostics.map((d: any, i: number) => (
                          <div
                            key={i}
                            onClick={() => handleDiagnosticClick(d.file, d.line)}
                            className="flex gap-3 p-1.5 hover:bg-ide-elevated cursor-pointer rounded items-start"
                          >
                            <AlertTriangle
                              size={14}
                              className={`shrink-0 mt-0.5 ${d.severity === 'error' ? 'text-ide-error' : 'text-ide-warning'}`}
                            />
                            <div>
                              <span className="text-ide-text-primary">{d.message}</span>
                              <span className="text-ide-text-secondary ml-2">
                                [{d.line}:{d.column || 1}]
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {bottomPanelTab === 'coverage' && (
                  <div>
                    {!coverage ? (
                      <p className="text-ide-text-secondary text-xs">No coverage data available for this run.</p>
                    ) : (
                      <div className="grid grid-cols-3 gap-4 max-w-xl">
                        <div className="bg-ide-panel border border-ide-border p-3 rounded text-center">
                          <div className="text-2xl font-semibold text-ide-accent">{coverage.statement ?? 0}%</div>
                          <div className="text-xs text-ide-text-secondary uppercase mt-1">Statement Coverage</div>
                        </div>
                        <div className="bg-ide-panel border border-ide-border p-3 rounded text-center">
                          <div className="text-2xl font-semibold text-ide-accent">{coverage.branch ?? 0}%</div>
                          <div className="text-xs text-ide-text-secondary uppercase mt-1">Branch Coverage</div>
                        </div>
                        <div className="bg-ide-panel border border-ide-border p-3 rounded text-center">
                          <div className="text-2xl font-semibold text-ide-accent">{coverage.function ?? 100}%</div>
                          <div className="text-xs text-ide-text-secondary uppercase mt-1">Function Coverage</div>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {bottomPanelTab === 'output' && (
                  <div className="font-mono text-[12px] text-ide-text-secondary space-y-1">
                    <p>[API] Connected to Honaero Sentinel Backend.</p>
                    {projectId && <p>[Project] Active Project ID: {projectId}</p>}
                    {executionId && <p>[Execution] Active Run ID: {executionId}</p>}
                    {analysis?.job?.status && <p>[Analysis] Status: {analysis.job.status}</p>}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* STATUS BAR */}
      <div className="h-6 bg-ide-accent text-ide-bg flex items-center justify-between px-3 text-[11px] font-medium shrink-0">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1">
            <CheckCircle size={12} /> Ready
          </span>
          {projectId && <span className="opacity-80">Project: {projectId.slice(0, 8)}</span>}
          {activeSource && <span className="opacity-80">File: {activeSource.filename}</span>}
        </div>
        <div className="flex items-center gap-4 opacity-80">
          <span>GCC 16.2.0 (DO-178C Hermetic)</span>
          <span>UTF-8</span>
          <span>{analysis?.diagnostics?.length || 0} Problems</span>
        </div>
      </div>

      {/* COMPILER CONFIG MODAL */}
      {showConfigModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-ide-panel border border-ide-border rounded-lg max-w-md w-full p-4 space-y-4 shadow-xl">
            <div className="flex justify-between items-center border-b border-ide-border pb-2">
              <span className="font-semibold text-sm flex items-center gap-2">
                <Settings size={16} className="text-ide-accent" /> Toolchain Configuration
              </span>
              <button onClick={() => setShowConfigModal(false)} className="text-ide-text-secondary hover:text-ide-text-primary">
                <X size={16} />
              </button>
            </div>
            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-ide-text-secondary mb-1">Compiler</label>
                <input
                  type="text"
                  disabled
                  value="gcc (MinGW-W64 16.2.0)"
                  className="w-full bg-ide-bg border border-ide-border rounded p-1.5 text-ide-text-secondary"
                />
              </div>
              <div>
                <label className="block text-ide-text-secondary mb-1">Compiler & Coverage Flags</label>
                <input
                  type="text"
                  value={cfgFlags}
                  onChange={(e) => setCfgFlags(e.target.value)}
                  className="w-full bg-ide-bg border border-ide-border rounded p-1.5 font-mono text-ide-text-primary"
                />
              </div>
              <div>
                <label className="block text-ide-text-secondary mb-1">Build Profile</label>
                <select
                  value={cfgProfile}
                  onChange={(e: any) => setCfgProfile(e.target.value)}
                  className="w-full bg-ide-bg border border-ide-border rounded p-1.5 text-ide-text-primary"
                >
                  <option value="coverage">Coverage (-O0 -g --coverage)</option>
                  <option value="debug">Debug (-O0 -g)</option>
                  <option value="release">Release (-O2)</option>
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-ide-border">
              <button onClick={() => setShowConfigModal(false)} className="px-3 py-1.5 rounded bg-ide-border text-ide-text-primary text-xs">
                Cancel
              </button>
              <button
                onClick={() => {
                  updateConfigMutation.mutate({
                    flags: cfgFlags.split(' ').filter(Boolean),
                    buildProfile: cfgProfile,
                  });
                }}
                disabled={updateConfigMutation.isPending}
                className="px-3 py-1.5 rounded bg-ide-action text-white text-xs font-medium"
              >
                Save Configuration
              </button>
            </div>
          </div>
        </div>
      )}

      {/* RUN COMPARISON MODAL */}
      {showCompareModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-ide-panel border border-ide-border rounded-lg max-w-lg w-full p-4 space-y-4 shadow-xl">
            <div className="flex justify-between items-center border-b border-ide-border pb-2">
              <span className="font-semibold text-sm flex items-center gap-2">
                <GitCompare size={16} className="text-ide-accent" /> Regression Analysis & Run Comparison
              </span>
              <button onClick={() => setShowCompareModal(false)} className="text-ide-text-secondary hover:text-ide-text-primary">
                <X size={16} />
              </button>
            </div>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <label className="block text-ide-text-secondary mb-1">Base Run (Baseline)</label>
                <select
                  value={compareBaseId}
                  onChange={(e) => setCompareBaseId(e.target.value)}
                  className="w-full bg-ide-bg border border-ide-border rounded p-1.5 text-ide-text-primary"
                >
                  {executionsList?.map((r: any) => (
                    <option key={r.id} value={r.id}>
                      #{r.id.slice(0, 8)} ({r.verdict || r.status})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-ide-text-secondary mb-1">Target Run (Current)</label>
                <select
                  value={compareTargetId}
                  onChange={(e) => setCompareTargetId(e.target.value)}
                  className="w-full bg-ide-bg border border-ide-border rounded p-1.5 text-ide-text-primary"
                >
                  {executionsList?.map((r: any) => (
                    <option key={r.id} value={r.id}>
                      #{r.id.slice(0, 8)} ({r.verdict || r.status})
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <button
              onClick={handleRunComparison}
              className="w-full bg-ide-action hover:bg-blue-500 text-white p-2 rounded text-xs font-medium"
            >
              Compare Runs
            </button>
            {compareResult && (
              <div className="p-3 bg-ide-bg border border-ide-border rounded text-xs space-y-2">
                <div className="flex gap-4">
                  <span className="text-rose-400 font-semibold">Regressions: {compareResult.regressionCount ?? 0}</span>
                  <span className="text-emerald-400 font-semibold">Fixes: {compareResult.fixedCount ?? 0}</span>
                </div>
                {compareResult.diffs && compareResult.diffs.length > 0 ? (
                  <div className="space-y-1">
                    {compareResult.diffs.map((d: any, idx: number) => (
                      <div key={idx} className="font-mono text-[11px] p-1 bg-ide-panel rounded">
                        [{d.type}] {d.attribute}: <span className="text-rose-300">{d.base}</span> → <span className="text-emerald-300">{d.target}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-ide-text-secondary">No differences detected between selected runs.</p>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* AI ASSISTANT MODAL */}
      {showAiModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-ide-panel border border-ide-border rounded-lg max-w-3xl w-full p-5 space-y-4 shadow-2xl max-h-[90vh] flex flex-col">
            <div className="flex justify-between items-center border-b border-ide-border pb-3 shrink-0">
              <div className="flex items-center gap-3">
                <span className="font-semibold text-sm flex items-center gap-2">
                  <Bot size={18} className="text-ide-accent" /> AI Assistant Studio (NVIDIA NIM)
                </span>
                <span
                  className={`text-[10px] px-2 py-0.5 rounded-full font-medium border ${
                    aiStatus?.isConfigured
                      ? 'bg-emerald-950/40 text-emerald-300 border-emerald-700'
                      : 'bg-amber-950/40 text-amber-300 border-amber-700'
                  }`}
                >
                  {aiStatus?.isConfigured ? 'NVIDIA NIM: Connected' : 'NVIDIA NIM: Deterministic Fallback'}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <select
                  value={selectedAiModel}
                  onChange={(e) => handleSelectModel(e.target.value)}
                  className="bg-ide-bg border border-ide-border rounded px-2 py-1 text-xs outline-none text-ide-text-primary"
                >
                  {aiModels?.map((m: any) => (
                    <option key={m.id} value={m.id}>
                      {m.name}
                    </option>
                  )) || (
                    <option value="meta/llama-3.3-70b-instruct">Meta Llama 3.3 70B</option>
                  )}
                </select>
                <button onClick={() => setShowAiModal(false)} className="text-ide-text-secondary hover:text-ide-text-primary">
                  <X size={18} />
                </button>
              </div>
            </div>

            <div className="overflow-x-auto pb-1 shrink-0">
              <div className="flex gap-1.5 text-xs whitespace-nowrap">
                {[
                  { id: 'requirements', label: 'Requirements' },
                  { id: 'tests', label: 'Test Proposals' },
                  { id: 'scenarios', label: 'Flight Scenarios' },
                  { id: 'faults', label: 'Fault Injection' },
                  { id: 'explain', label: 'Diagnostics' },
                  { id: 'coverage-gaps', label: 'Coverage Gaps' },
                  { id: 'adaptive-retest', label: 'Adaptive Retest' },
                  { id: 'optimize', label: 'Suite Optimizer' },
                  { id: 'traceability', label: 'Traceability' },
                  { id: 'environment', label: 'Toolchain' },
                  { id: 'report', label: 'Report Draft' },
                ].map((t) => (
                  <button
                    key={t.id}
                    onClick={() => {
                      setAiPromptType(t.id);
                      setAiOutput(null);
                      setAiActionMessage('');
                    }}
                    className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
                      aiPromptType === t.id ? 'bg-ide-accent text-ide-bg' : 'bg-ide-border text-ide-text-primary hover:bg-ide-elevated'
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="p-2.5 bg-amber-950/20 border border-amber-900/40 rounded text-[11px] text-amber-200 shrink-0">
              <strong>DO-178C Deterministic Guardrail:</strong> AI output represents advisory candidate proposals. Ground truth verification is strictly established through deterministic compilation, test harness execution, and GCOV/MC/DC measurement.
            </div>

            {aiActionMessage && (
              <div className="p-2 bg-emerald-950/30 border border-emerald-800/50 rounded text-xs text-emerald-300 flex items-center gap-2 shrink-0">
                <Check size={14} /> {aiActionMessage}
              </div>
            )}

            <button
              onClick={handleTriggerAi}
              disabled={aiLoading || !projectId}
              className="w-full bg-ide-action hover:bg-blue-500 text-white p-2 rounded text-xs font-medium disabled:opacity-50 shrink-0"
            >
              {aiLoading ? 'Querying Model / Synthesizing Proposals...' : `Generate ${aiPromptType.toUpperCase()} Proposal`}
            </button>

            <div className="flex-1 overflow-y-auto min-h-0 space-y-3 pr-1">
              {aiOutput ? (
                <div className="space-y-3">
                  <div className="flex justify-between text-[11px] text-ide-text-secondary pb-1 border-b border-ide-border">
                    <span>Model: {aiOutput.modelUsed || selectedAiModel} ({aiOutput.isLiveCall ? 'Live NIM Call' : 'Deterministic Provenance Fallback'})</span>
                    {aiOutput.confidenceScore && <span>Confidence Score: {Math.round(aiOutput.confidenceScore * 100)}%</span>}
                  </div>

                  {/* Requirements List */}
                  {aiPromptType === 'requirements' && Array.isArray(aiOutput.content) && (
                    <div className="space-y-2">
                      {aiOutput.content.map((req: any, idx: number) => (
                        <div key={idx} className="p-3 bg-ide-bg border border-ide-border rounded space-y-2">
                          <div className="flex justify-between items-start">
                            <div>
                              <span className="font-mono font-bold text-xs text-sky-400">{req.identifier}</span>
                              <span className="ml-2 font-semibold text-xs text-ide-text-primary">{req.title}</span>
                            </div>
                            <span className="text-[10px] bg-ide-elevated px-1.5 py-0.5 rounded text-ide-text-secondary border border-ide-border">
                              {req.provenance || 'AI_INFERRED'}
                            </span>
                          </div>
                          <p className="text-xs text-ide-text-secondary">{req.description}</p>
                          {req.constraints && req.constraints.length > 0 && (
                            <div className="text-[11px] text-amber-300 font-mono">
                              Constraints: {req.constraints.join(', ')}
                            </div>
                          )}
                          <div className="flex justify-end pt-1">
                            <button
                              onClick={() => handleApproveRequirement(req)}
                              className="px-2.5 py-1 bg-emerald-700 hover:bg-emerald-600 text-white rounded text-[11px] font-medium flex items-center gap-1"
                            >
                              <Check size={12} /> Approve Requirement
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Test Proposals */}
                  {aiPromptType === 'tests' && Array.isArray(aiOutput.content) && (
                    <div className="space-y-2">
                      {aiOutput.content.map((tc: any, idx: number) => (
                        <div key={idx} className="p-3 bg-ide-bg border border-ide-border rounded space-y-2">
                          <div className="flex justify-between items-start">
                            <div>
                              <span className="font-mono font-semibold text-xs text-ide-accent">{tc.name}</span>
                              <span className="ml-2 text-[10px] bg-ide-elevated px-1.5 py-0.5 rounded text-ide-text-secondary">
                                {tc.category}
                              </span>
                            </div>
                            <span className="text-[10px] text-ide-text-secondary">
                              Oracle: {tc.hasApprovedOracle ? 'Grounded' : 'Unresolved'}
                            </span>
                          </div>
                          <div className="grid grid-cols-2 gap-2 text-[11px] font-mono bg-ide-panel p-2 rounded">
                            <div>Inputs: {JSON.stringify(tc.inputs)}</div>
                            <div>Expected: {JSON.stringify(tc.expectedOutputs)}</div>
                          </div>
                          {tc.rationale && <p className="text-[11px] text-ide-text-secondary">{tc.rationale}</p>}
                          <div className="flex justify-end pt-1">
                            <button
                              onClick={() => handleApproveTestProposal(tc)}
                              className="px-2.5 py-1 bg-ide-action hover:bg-blue-600 text-white rounded text-[11px] font-medium flex items-center gap-1"
                            >
                              <PlaySquare size={12} /> Promote to Test Suite
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Scenarios */}
                  {aiPromptType === 'scenarios' && Array.isArray(aiOutput.content) && (
                    <div className="space-y-3">
                      {aiOutput.content.map((sc: any, idx: number) => (
                        <div key={idx} className="p-3 bg-ide-bg border border-ide-border rounded space-y-2">
                          <div className="font-semibold text-xs text-ide-accent">{sc.scenarioName} ({sc.flightPhase})</div>
                          <p className="text-[11px] text-ide-text-secondary">{sc.rationale}</p>
                          <div className="space-y-1">
                            {sc.steps?.map((st: any, sIdx: number) => (
                              <div key={sIdx} className="text-[11px] font-mono p-1 bg-ide-panel rounded flex justify-between">
                                <span>Step {st.stepIndex} ({st.flightPhase}): {JSON.stringify(st.inputs)}</span>
                                <span className="text-emerald-300">{st.expectedState}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Failure Diagnostics */}
                  {aiPromptType === 'explain' && aiOutput.content && (
                    <div className="p-3 bg-ide-bg border border-ide-border rounded space-y-2 text-xs">
                      <div className="font-semibold text-rose-300">Run: {aiOutput.content.executionId} (Verdict: {aiOutput.content.verdict})</div>
                      {aiOutput.content.possibleCauses && (
                        <div>
                          <div className="font-semibold text-ide-text-primary mb-1">Identified Potential Causes:</div>
                          <ul className="list-disc pl-4 space-y-0.5 text-ide-text-secondary text-[11px]">
                            {aiOutput.content.possibleCauses.map((c: string, cIdx: number) => (
                              <li key={cIdx}>{c}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {aiOutput.content.suggestedRemediation && (
                        <div>
                          <div className="font-semibold text-emerald-300 mb-1">Suggested Remediation:</div>
                          <ul className="list-disc pl-4 space-y-0.5 text-ide-text-secondary text-[11px]">
                            {aiOutput.content.suggestedRemediation.map((r: string, rIdx: number) => (
                              <li key={rIdx}>{r}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Coverage Gaps */}
                  {aiPromptType === 'coverage-gaps' && Array.isArray(aiOutput.content) && (
                    <div className="space-y-2">
                      {aiOutput.content.map((gap: any, gIdx: number) => (
                        <div key={gIdx} className="p-3 bg-ide-bg border border-ide-border rounded space-y-1 text-xs">
                          <div className="font-semibold text-amber-300">{gap.sourceLocation}</div>
                          <p className="text-ide-text-secondary text-[11px]">{gap.gapDescription}</p>
                          <div className="font-mono text-[11px] p-1 bg-ide-panel rounded text-sky-300">
                            Recommended Vector: {JSON.stringify(gap.proposedVector)} ({gap.targetedBranch})
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Default / Report / Optimization fallback */}
                  {!['requirements', 'tests', 'scenarios', 'explain', 'coverage-gaps'].includes(aiPromptType) && (
                    <pre className="font-mono text-[11px] text-ide-text-primary whitespace-pre-wrap p-3 bg-ide-bg border border-ide-border rounded">
                      {typeof aiOutput.content === 'string'
                        ? aiOutput.content
                        : JSON.stringify(aiOutput.content, null, 2)}
                    </pre>
                  )}
                </div>
              ) : (
                <div className="p-6 text-center text-ide-text-secondary text-xs">
                  Select a category above and click generate to query the AI model.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ActivityBtn({
  id,
  icon,
  title,
  activePane,
  setActivePane,
}: {
  id: string;
  icon: React.ReactNode;
  title: string;
  activePane: string;
  setActivePane: any;
}) {
  const active = activePane === id;
  return (
    <button
      onClick={() => setActivePane(id)}
      title={title}
      className={`p-2.5 relative flex items-center justify-center transition-colors ${
        active ? 'text-ide-text-primary' : 'text-ide-text-secondary hover:text-ide-text-primary'
      }`}
    >
      {active && <div className="absolute left-0 top-0 bottom-0 w-[2px] bg-ide-accent"></div>}
      {icon}
    </button>
  );
}

function PanelTab({
  id,
  title,
  current,
  set,
  count,
}: {
  id: string;
  title: string;
  current: string;
  set: any;
  count?: number;
}) {
  const active = current === id;
  return (
    <button
      onClick={() => set(id)}
      className={`px-3 py-1.5 text-[11px] uppercase tracking-wide border-b-2 transition-colors flex items-center gap-1.5 ${
        active ? 'border-ide-accent text-ide-text-primary font-medium' : 'border-transparent text-ide-text-secondary hover:text-ide-text-primary'
      }`}
    >
      {title}{' '}
      {count !== undefined && count > 0 && (
        <span className="bg-ide-elevated text-ide-text-primary px-1.5 rounded-full text-[10px]">{count}</span>
      )}
    </button>
  );
}
