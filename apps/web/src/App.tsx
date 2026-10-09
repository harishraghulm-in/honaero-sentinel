import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import Editor, { useMonaco } from '@monaco-editor/react';
import { Target, AlertTriangle, CheckCircle, Upload, Play, Code, Beaker, Folder, Search, FileDown, Sparkles, Activity, TerminalSquare, SlidersHorizontal, PackageOpen, LayoutDashboard, PlaySquare, Network, FileText, ChevronRight, X, Maximize2, Minimize2, PlayCircle, Settings, Box } from 'lucide-react';
import { getProjects, createProject } from './api/projects';
import { getSources, createSource } from './api/sources';
import { getAnalysis, analyzeProject } from './api/analysis';
import { getTestCases, getTestSuites, suggestTestCases } from './api/tests';
import { getDependencies } from './api/dependencies';
import { getExecution, createExecution, getExecutions } from './api/executions';
import { getCoverage } from './api/coverage';
import { getMcdc } from './api/mcdc';
import { getTraceability } from './api/traceability';
import { getEvidence, exportEvidence } from './api/evidence';
import { getAvailableModels, extractRequirements, suggestFaultInjections, explainFailure, recommendStubs, generateAIReport } from './api/ai';
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
    selectedFunctionId, setSelectedFunctionId,
    selectedTestSuiteId, setSelectedTestSuiteId,
    editorSelection, setEditorSelection
  } = useStudioStore();

  const editorRef = useRef<any>(null);
  const monaco = useMonaco();
  const decorationsRef = useRef<string[]>([]);
  const [panelHeight, setPanelHeight] = useState(250);

  // Fallback active pane
  useEffect(() => {
    if (!['explorer', 'search', 'analysis', 'tests', 'runs', 'coverage', 'reports'].includes(activePane)) {
      setActivePane('explorer');
    }
  }, [activePane, setActivePane]);

  const { data: projects, refetch: refetchProjects } = useQuery({ queryKey: ['projects'], queryFn: () => getProjects(), retry: false });
  const { data: sources, isLoading: sourcesLoading, refetch: refetchSources } = useQuery({ queryKey: ['sources', projectId], queryFn: () => getSources(projectId!), enabled: !!projectId, retry: false });
  const { data: aiModels } = useQuery({ queryKey: ['aiModels'], queryFn: () => getAvailableModels(), retry: false });

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

  const analyzeProjectMutation = useMutation({ mutationFn: () => analyzeProject(projectId!), onSuccess: () => { refetchAnalysis(); setBottomPanelTab('problems'); } });

  const { data: execution, isError: execError } = useQuery({
    queryKey: ['execution', projectId, executionId], queryFn: () => getExecution(projectId!, executionId!),
    enabled: !!executionId && !!projectId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'QUEUED' || status === 'BUILDING' || status === 'RUNNING') return 1000;
      return false;
    }, retry: false
  });

  const isComplete = execution ? ['PASS', 'FAIL', 'ERROR', 'CANCELLED'].includes(execution.status) : false;
  const { data: coverage } = useQuery({ queryKey: ['coverage', projectId, executionId], queryFn: () => getCoverage(projectId!, executionId!), enabled: isComplete && !!projectId, retry: false });

  const executeMutation = useMutation({
    mutationFn: (vector: TestVector) => createExecution(projectId!, vector),
    onSuccess: (data) => {
      if (data && data.id) { setExecutionId(data.id); setBottomPanelTab('test-results'); }
    }
  });

  const { register, handleSubmit, formState: { errors } } = useForm<TestVector>({ resolver: zodResolver(vectorSchema) });

  const activeSource = sources?.find(s => s.id === selectedSourceId);

  useEffect(() => {
    if (editorRef.current && monaco && analysis?.diagnostics && selectedSourceId) {
      const newDecorations = analysis.diagnostics
        .filter(d => d.file === selectedSourceId)
        .map(d => ({
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

  return (
    <div className="flex flex-col h-screen w-screen bg-ide-bg text-ide-text-primary overflow-hidden text-[13px]">
      {/* TOP MENU BAR */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-ide-activity border-b border-ide-border shrink-0">
        <div className="flex items-center gap-4">
          <span className="font-semibold flex items-center gap-2 text-ide-text-primary tracking-wide"><Target size={16} className="text-ide-accent"/> HONAERO SENTINEL</span>
          <div className="h-4 w-px bg-ide-border"></div>
          <div className="flex items-center gap-2 text-ide-text-secondary hover:text-ide-text-primary cursor-pointer">
            <Box size={14}/>
            <select value={projectId || ''} onChange={(e) => setProjectId(e.target.value)} className="bg-transparent border-none outline-none appearance-none cursor-pointer pr-4">
              <option value="">Select Project ▾</option>
              {projects?.map((p: any) => <option key={p.id} value={p.id}>{p.id}</option>)}
            </select>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => projectId && analyzeProjectMutation.mutate()} disabled={!projectId || analyzeProjectMutation.isPending} className="flex items-center gap-1.5 px-3 py-1 rounded bg-ide-border hover:bg-ide-elevated text-ide-text-primary transition-colors disabled:opacity-50"><Code size={14}/> Analyze</button>
          <button disabled={!projectId} className="flex items-center gap-1.5 px-3 py-1 rounded bg-ide-action hover:bg-blue-500 text-white transition-colors disabled:opacity-50"><Play size={14}/> Run</button>
          <button className="text-ide-text-secondary hover:text-ide-text-primary"><Settings size={16}/></button>
        </div>
      </div>

      {/* MAIN WORKSPACE */}
      <div className="flex flex-1 overflow-hidden">
        {/* ACTIVITY BAR */}
        <div className="w-12 bg-ide-activity flex flex-col items-center py-2 shrink-0 border-r border-ide-border gap-2">
          <ActivityBtn id="explorer" icon={<Folder size={20}/>} title="Explorer" activePane={activePane} setActivePane={setActivePane} />
          <ActivityBtn id="search" icon={<Search size={20}/>} title="Search" activePane={activePane} setActivePane={setActivePane} />
          <ActivityBtn id="analysis" icon={<Activity size={20}/>} title="Source Analysis" activePane={activePane} setActivePane={setActivePane} />
          <ActivityBtn id="tests" icon={<Beaker size={20}/>} title="Test Explorer" activePane={activePane} setActivePane={setActivePane} />
          <ActivityBtn id="runs" icon={<PlaySquare size={20}/>} title="Verification Runs" activePane={activePane} setActivePane={setActivePane} />
          <ActivityBtn id="coverage" icon={<Network size={20}/>} title="Coverage" activePane={activePane} setActivePane={setActivePane} />
          <ActivityBtn id="reports" icon={<FileText size={20}/>} title="Reports" activePane={activePane} setActivePane={setActivePane} />
        </div>

        {/* SIDEBAR */}
        <div className="w-64 bg-ide-sidebar border-r border-ide-border flex flex-col shrink-0 overflow-hidden">
          <div className="px-4 py-2 font-medium tracking-wide text-[11px] uppercase text-ide-text-secondary">{activePane}</div>
          <div className="flex-1 overflow-y-auto px-2 pb-2">
            {activePane === 'explorer' && (
              <div className="space-y-4">
                {!projectId ? (
                  <div className="p-3 text-ide-text-secondary text-center">
                    <p className="mb-3">No project selected.</p>
                    <button onClick={() => createProjectMutation.mutate('New Project')} className="bg-ide-accent text-ide-bg px-3 py-1.5 rounded w-full font-medium">Create Project</button>
                  </div>
                ) : (
                  <div>
                    <div className="text-xs font-semibold mb-2 px-2">SOURCES</div>
                    {sourcesLoading ? <div className="px-2 text-ide-text-secondary">Loading...</div> : sources?.map((s: any) => (
                      <div key={s.id} onClick={() => setSelectedSourceId(s.id)} className={`cursor-pointer px-2 py-1.5 rounded flex items-center gap-2 ${selectedSourceId === s.id ? 'bg-ide-elevated text-ide-accent' : 'hover:bg-ide-elevated text-ide-text-primary'}`}>
                        <FileText size={14}/> {s.filename}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            {activePane === 'analysis' && (
               <div className="p-2 space-y-4">
                 <button onClick={() => projectId && analyzeProjectMutation.mutate()} disabled={!projectId} className="w-full bg-ide-elevated hover:bg-ide-border px-3 py-2 rounded flex items-center justify-center gap-2 disabled:opacity-50"><Activity size={14}/> Run Full Analysis</button>
                 {analysis?.job && (
                   <div className="text-xs text-ide-text-secondary">
                     Status: <span className="text-ide-text-primary">{analysis.job.status}</span>
                   </div>
                 )}
               </div>
            )}
            {activePane === 'tests' && (
              <div className="p-2 space-y-4">
                <div className="text-xs font-semibold">MANUAL TEST</div>
                <form onSubmit={handleSubmit((d) => executeMutation.mutate(d))} className="space-y-3">
                  <div>
                    <label className="block text-xs mb-1 text-ide-text-secondary">Pressure</label>
                    <input type="number" {...register('pressure', { valueAsNumber: true })} className="w-full bg-ide-bg border border-ide-border rounded px-2 py-1 text-ide-text-primary outline-none focus:border-ide-accent" />
                  </div>
                  <div>
                    <label className="block text-xs mb-1 text-ide-text-secondary">Altitude</label>
                    <input type="number" {...register('altitude', { valueAsNumber: true })} className="w-full bg-ide-bg border border-ide-border rounded px-2 py-1 text-ide-text-primary outline-none focus:border-ide-accent" />
                  </div>
                  <button type="submit" disabled={!projectId || executeMutation.isPending} className="w-full bg-ide-action hover:bg-blue-500 text-white px-3 py-1.5 rounded font-medium disabled:opacity-50 flex items-center justify-center gap-2">
                    <Play size={14} /> Execute
                  </button>
                </form>
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
                  <Code size={14} className="text-ide-accent"/> {activeSource.filename}
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
                  onMount={(editor) => { editorRef.current = editor; }}
                  options={{ minimap: { enabled: true, scale: 0.75 }, scrollBeyondLastLine: false, fontSize: 13, fontFamily: 'var(--font-mono)' }}
                />
              ) : (
                <div className="h-full flex items-center justify-center text-ide-text-secondary flex-col gap-4">
                  <Target size={48} className="opacity-20"/>
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
                  <PanelTab id="problems" title="Problems" current={bottomPanelTab} set={setBottomPanelTab} count={analysis?.diagnostics?.length}/>
                  <PanelTab id="terminal" title="Terminal" current={bottomPanelTab} set={setBottomPanelTab}/>
                  <PanelTab id="test-results" title="Test Results" current={bottomPanelTab} set={setBottomPanelTab}/>
                  <PanelTab id="coverage" title="Coverage" current={bottomPanelTab} set={setBottomPanelTab}/>
                  <PanelTab id="output" title="Output" current={bottomPanelTab} set={setBottomPanelTab}/>
                </div>
                <button onClick={() => setBottomPanelOpen(false)} className="p-1 text-ide-text-secondary hover:text-ide-text-primary rounded"><X size={14}/></button>
              </div>
              <div className="flex-1 overflow-auto p-3 bg-ide-bg">
                {bottomPanelTab === 'problems' && (
                  <div>
                    {!analysis?.diagnostics?.length ? <p className="text-ide-text-secondary">No problems detected.</p> : (
                      <div className="space-y-1">
                        {analysis.diagnostics.map((d: any, i: number) => (
                          <div key={i} onClick={() => handleDiagnosticClick(d.file, d.line)} className="flex gap-3 p-1 hover:bg-ide-elevated cursor-pointer rounded items-start">
                            {d.severity === 'error' ? <AlertTriangle size={14} className="text-ide-error shrink-0 mt-0.5"/> : <AlertTriangle size={14} className="text-ide-warning shrink-0 mt-0.5"/>}
                            <div>
                              <span className="text-ide-text-primary">{d.message}</span>
                              <span className="text-ide-text-secondary ml-2">[{d.line}:{d.column || 1}]</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
                {bottomPanelTab === 'terminal' && (
                  <div className="font-mono text-[12px] text-ide-text-secondary">
                    <p className="text-ide-accent">{'>'} HONAERO SENTINEL CONSOLE</p>
                    <p>Ready.</p>
                  </div>
                )}
                {bottomPanelTab === 'test-results' && (
                  <div>
                    {!execution ? <p className="text-ide-text-secondary">No verification run selected.</p> : (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2 font-medium">
                          Status: <span className={execution.status === 'PASS' ? 'text-ide-success' : execution.status === 'FAIL' ? 'text-ide-error' : 'text-ide-warning'}>{execution.status}</span>
                        </div>
                        {execution.expectedResult !== undefined && (
                          <div className="grid grid-cols-2 gap-4">
                            <div className="bg-ide-panel border border-ide-border p-2 rounded"><span className="text-ide-text-secondary text-xs uppercase block">Expected</span><code className="text-ide-text-primary">{execution.expectedResult}</code></div>
                            <div className="bg-ide-panel border border-ide-border p-2 rounded"><span className="text-ide-text-secondary text-xs uppercase block">Actual</span><code className="text-ide-text-primary">{execution.actualResult}</code></div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
                {bottomPanelTab === 'coverage' && (
                  <div>
                    {!coverage ? <p className="text-ide-text-secondary">No coverage data available for this run.</p> : (
                      <div className="grid grid-cols-3 gap-4">
                        <div className="bg-ide-panel border border-ide-border p-3 rounded text-center">
                          <div className="text-2xl font-semibold text-ide-accent">{coverage.statement}%</div>
                          <div className="text-xs text-ide-text-secondary uppercase mt-1">Statement</div>
                        </div>
                        <div className="bg-ide-panel border border-ide-border p-3 rounded text-center">
                          <div className="text-2xl font-semibold text-ide-accent">{coverage.branch}%</div>
                          <div className="text-xs text-ide-text-secondary uppercase mt-1">Branch</div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
                {bottomPanelTab === 'output' && (
                  <div className="font-mono text-[12px] text-ide-text-secondary">
                    [API] Connection established.<br/>
                    {analysis?.job?.status && `[Analysis] Status: ${analysis.job.status}\n`}
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
          <span className="flex items-center gap-1"><CheckCircle size={12}/> Ready</span>
          {projectId && <span className="opacity-80">Project: {projectId}</span>}
          {activeSource && <span className="opacity-80">C/C++</span>}
        </div>
        <div className="flex items-center gap-4 opacity-80">
          <span>UTF-8</span>
          <span>{analysis?.diagnostics?.length || 0} Problems</span>
        </div>
      </div>
    </div>
  );
}

function ActivityBtn({ id, icon, title, activePane, setActivePane }: { id: string, icon: React.ReactNode, title: string, activePane: string, setActivePane: any }) {
  const active = activePane === id;
  return (
    <button
      onClick={() => setActivePane(id)}
      title={title}
      className={`p-2.5 relative flex items-center justify-center transition-colors ${active ? 'text-ide-text-primary' : 'text-ide-text-secondary hover:text-ide-text-primary'}`}
    >
      {active && <div className="absolute left-0 top-0 bottom-0 w-[2px] bg-ide-accent"></div>}
      {icon}
    </button>
  );
}

function PanelTab({ id, title, current, set, count }: { id: string, title: string, current: string, set: any, count?: number }) {
  const active = current === id;
  return (
    <button
      onClick={() => set(id)}
      className={`px-3 py-1.5 text-[11px] uppercase tracking-wide border-b-2 transition-colors flex items-center gap-1.5 ${active ? 'border-ide-accent text-ide-text-primary' : 'border-transparent text-ide-text-secondary hover:text-ide-text-primary'}`}
    >
      {title} {count !== undefined && count > 0 && <span className="bg-ide-elevated text-ide-text-primary px-1.5 rounded-full text-[10px]">{count}</span>}
    </button>
  );
}
