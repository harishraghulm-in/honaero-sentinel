import React, { useState, useEffect, useRef } from 'react';
import { 
  Play, Square, Activity, Terminal, FileCode, 
  CheckCircle2, AlertCircle, Cpu, Clock, Filter, 
  CornerDownRight, RotateCcw, FileText, ChevronRight, 
  Layers, Check, ShieldCheck, ListOrdered, Sparkles, Sliders
} from 'lucide-react';
import type { ProjectFile, TestCase, ExecutionEvent, Diagnostic, 
  RunStatus, PerFileExecutionReport, TestFlowPreference 
 } from '../../types';

interface LiveVerificationViewProps {
  files: ProjectFile[];
  testCases: TestCase[];
  selectedFile?: ProjectFile;
  onSelectFile: (file: ProjectFile) => void;
  runStatus: RunStatus;
  progress: number;
  events: ExecutionEvent[];
  activeLine?: number;
  activeFunction?: string;
  onStartVerification: () => void;
  onCancelVerification: () => void;
  onResetVerification: () => void;
  isBackendConnected: boolean;
  perFileReports: PerFileExecutionReport[];
  executionOrder: ProjectFile[];
  flowPreference: TestFlowPreference;
  onFlowPreferenceChange: (pref: TestFlowPreference) => void;
  activeExecutionId?: string | null;
  projectId?: string;
  onRerunExecution?: (executionId: string) => void;
}

export const LiveVerificationView: React.FC<LiveVerificationViewProps> = ({
  files,
  testCases,
  selectedFile,
  onSelectFile,
  runStatus,
  progress,
  events,
  activeLine,
  activeFunction,
  onStartVerification,
  onCancelVerification,
  onResetVerification,
  isBackendConnected,
  perFileReports,
  executionOrder,
  flowPreference,
  onFlowPreferenceChange,
  activeExecutionId,
  projectId,
  onRerunExecution,
}) => {
  const [activeViewTab, setActiveViewTab] = useState<'events' | 'per_file_reports' | 'history'>('events');
  const [logFilter, setLogFilter] = useState<'all' | 'tests' | 'compiler' | 'diagnostics'>('all');
  const [autoScroll, setAutoScroll] = useState(true);
  const [inspectedReport, setInspectedReport] = useState<PerFileExecutionReport | null>(null);
  const [executionHistory, setExecutionHistory] = useState<any[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const logContainerRef = useRef<HTMLDivElement>(null);

  // Load execution history
  useEffect(() => {
    let isCancelled = false;
    const fetchHistory = async () => {
      if (!projectId || projectId.startsWith('proj-x35')) return;
      setIsLoadingHistory(true);
      try {
        const res = await fetch(`/api/v1/projects/${projectId}/executions`);
        if (res.ok) {
          const data = await res.json();
          if (!isCancelled && Array.isArray(data)) {
            setExecutionHistory(data);
          }
        }
      } catch (err) {
        console.warn('Failed to load execution history:', err);
      } finally {
        if (!isCancelled) setIsLoadingHistory(false);
      }
    };

    fetchHistory();
    return () => { isCancelled = true; };
  }, [projectId, runStatus]);

  // Auto scroll logs
  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [events, autoScroll]);

  // Update inspected report when new per-file reports arrive
  useEffect(() => {
    if (perFileReports.length > 0 && !inspectedReport) {
      setInspectedReport(perFileReports[perFileReports.length - 1]);
    }
  }, [perFileReports]);

  // Filter logs
  const filteredEvents = events.filter((e) => {
    if (logFilter === 'tests') return e.type.includes('test');
    if (logFilter === 'compiler') return e.type.includes('compilation');
    if (logFilter === 'diagnostics') return e.severity === 'error' || e.severity === 'warning';
    return true;
  });

  const lines = selectedFile?.content ? selectedFile.content.split('\n') : [];

  return (
    <div className="flex-1 flex flex-col bg-[#0B0E14] text-[#E6EDF3] overflow-hidden">
      {/* 1. TOP LIVE CONTROLLER BAR */}
      <div className="bg-[#161B22] border-b border-[#21262D] px-4 py-3 flex flex-wrap items-center justify-between gap-4 shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Activity size={18} className={runStatus === 'running' ? 'text-[#00E5FF] animate-pulse' : 'text-[#8B949E]'} />
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold text-white">
                  RUN-ID: {activeExecutionId ? `#${activeExecutionId}` : '#VR-2026-X35-0891'}
                </span>
                <span className="text-[9px] font-mono font-bold px-1.5 py-0.2 rounded border bg-cyan-950/60 text-cyan-400 border-cyan-800">
                  {flowPreference === 'ai_recommended' ? 'AI RECOMMENDED ORDER' : 'CUSTOM ORDER'}
                </span>
                <span className="text-[9px] font-mono text-emerald-400 bg-emerald-950/40 px-1.5 py-0.2 rounded border border-emerald-900">
                  NON-STOP FAULT LOGGING ACTIVE
                </span>
              </div>
              <div className="text-[10px] text-[#8B949E] font-mono mt-0.5">
                Target: PowerPC e500v2 · Testing Requirement Compliance & User Input Vectors
              </div>
            </div>
          </div>

          <div className="h-6 w-[1px] bg-[#21262D] hidden md:block" />

          {/* ACTIVE EXECUTION FOCUS POINTER */}
          {selectedFile && (
            <div className="hidden lg:flex items-center gap-2 px-3 py-1 bg-[#0B0E14] border border-[#21262D] rounded-md text-xs font-mono">
              <span className="text-[#8B949E]">Executing Module:</span>
              <span className="text-[#00E5FF] font-semibold truncate max-w-[180px]">
                {selectedFile.name}
              </span>
              {activeLine && (
                <span className="text-amber-400">
                  :L{activeLine}
                </span>
              )}
              {activeFunction && (
                <span className="text-[#CBD5E1]">
                  ({activeFunction})
                </span>
              )}
            </div>
          )}
        </div>

        {/* PROGRESS & CONTROLS */}
        <div className="flex items-center gap-4">
          {/* Progress gauge */}
          <div className="w-36 hidden sm:block">
            <div className="flex justify-between text-[10px] font-mono text-[#8B949E] mb-1">
              <span>Execution Progress</span>
              <span className="text-[#00E5FF] font-bold">{progress}%</span>
            </div>
            <div className="h-1.5 bg-[#0B0E14] rounded-full overflow-hidden border border-[#21262D]">
              <div
                className="h-full bg-[#00E5FF] transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            {runStatus === 'running' ? (
              <button
                onClick={onCancelVerification}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-amber-400 hover:bg-amber-300 text-black text-xs font-bold transition-colors shadow-sm cursor-pointer"
              >
                <Square size={12} fill="currentColor" />
                <span>Cancel</span>
              </button>
            ) : (
              <button
                onClick={onStartVerification}
                className="btn-aerospace-glow btn-shimmer flex items-center gap-1.5 px-4 py-1.5 rounded-md bg-[#00E5FF] hover:bg-cyan-300 text-black text-xs font-bold transition-all shadow-[0_0_15px_rgba(0,229,255,0.3)] cursor-pointer"
              >
                <Play size={12} fill="currentColor" />
                <span>Run Flow Verification</span>
              </button>
            )}

            <button
              onClick={onResetVerification}
              className="p-1.5 text-[#8B949E] hover:text-white rounded hover:bg-[#21262D] transition-colors"
              title="Reset verification state"
            >
              <RotateCcw size={15} />
            </button>
          </div>
        </div>
      </div>

      {/* 2. SPLIT WORKSPACE: ACTIVE SOURCE (LEFT) + RIGHT PANEL (EVENT STREAM / PER-FILE REPORTS) */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* LEFT / CENTER: SOURCE SYNCHRONIZATION WITH LINE HIGHLIGHT */}
        <div className="flex-1 flex flex-col bg-[#0B0E14] border-r border-[#21262D] overflow-hidden">
          {/* TAB BAR FOR SOURCE FILE */}
          <div className="h-9 bg-[#161B22] border-b border-[#21262D] px-4 flex items-center justify-between text-xs font-mono shrink-0">
            <div className="flex items-center gap-2">
              <FileCode size={14} className="text-[#00E5FF]" />
              <span className="font-semibold text-white">{selectedFile?.name || 'No file selected'}</span>
              {selectedFile && <span className="text-[#8B949E]">({selectedFile.path})</span>}
            </div>

            <div className="flex items-center gap-3 text-[11px] text-[#8B949E]">
              {activeLine && (
                <span className="text-[#00E5FF] flex items-center gap-1 font-semibold">
                  <CornerDownRight size={12} /> Testing Line {activeLine}
                </span>
              )}
              {selectedFile && (
                <span className={`px-1.5 py-0.2 rounded font-semibold ${
                  selectedFile.status === 'passed' ? 'text-emerald-400 bg-emerald-950/40' :
                  selectedFile.status === 'failed' ? 'text-rose-400 bg-rose-950/40' :
                  'text-[#8B949E]'
                }`}>
                  {selectedFile.status.toUpperCase()}
                </span>
              )}
            </div>
          </div>

            {/* CODE VIEWPORT: LINE BY LINE REAL-TIME EXECUTION */}
            <div className="flex-1 overflow-auto py-2 bg-[#0B0E14] font-mono text-[13px] leading-6">
              {lines.length === 0 ? (
                <div className="h-full flex items-center justify-center text-xs text-[#8B949E] font-mono">
                  {selectedFile ? 'Empty file content' : 'Select a source module to monitor verification execution.'}
                </div>
              ) : lines.map((line, idx) => {
                const lineNum = idx + 1;
                const isActive = activeLine === lineNum;
                const isErrorLine = selectedFile?.status === 'failed' && (activeLine === lineNum || idx === 0);

                return (
                  <div
                    key={idx}
                    className={`flex px-4 transition-colors ${
                      isActive
                        ? 'bg-cyan-950/50 border-l-2 border-[#00E5FF] text-white shadow-[inset_0_0_15px_rgba(0,229,255,0.2)]'
                        : isErrorLine
                        ? 'bg-rose-950/40 border-l-2 border-rose-500 text-rose-200'
                        : 'hover:bg-[#161B22]/50 text-[#CBD5E1]'
                    }`}
                  >
                    <span
                      className={`w-10 shrink-0 text-right pr-4 select-none ${
                        isActive ? 'text-[#00E5FF] font-bold' : isErrorLine ? 'text-rose-400 font-bold' : 'text-[#484F58]'
                      }`}
                    >
                      {lineNum}
                    </span>
                    <span className="whitespace-pre overflow-x-auto flex-1">
                      {line}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* REAL TESTING REQUIREMENTS & USER INPUT METRICS BANNER */}
            <div className="p-3 bg-[#0E131B] border-t border-[#21262D] flex items-center justify-between text-xs font-mono">
              <div className="flex items-center gap-3">
                <span className="text-[#8B949E]">Active Requirement Check:</span>
                <span className="text-white font-semibold">
                  DO-178C Deterministic Boundary Vector Validation
                </span>
              </div>

              <span className="text-[11px] text-[#00E5FF]">
                Continuous Multi-Line Execution Engine
              </span>
            </div>
        </div>

        {/* RIGHT COLUMN: SWITCHABLE TIMELINE LOG OR PER-FILE EXECUTION REPORTS */}
        <div className="w-[420px] flex flex-col bg-[#0E131B] shrink-0 overflow-hidden border-l border-[#21262D]">
          {/* QUEUE STATUS MINI BAR (SHOWS THE RECOMMENDED ORDER OF FILES) */}
          <div className="p-3 bg-[#161B22] border-b border-[#21262D] space-y-2 shrink-0">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-white font-heading">
                Flow Order ({executionOrder.length} Modules)
              </span>
              <span className="text-[10px] font-mono text-[#8B949E]">
                {perFileReports.length} Reports Generated
              </span>
            </div>

            <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
              {executionOrder.map((f, i) => (
                <button
                  key={f.id}
                  onClick={() => onSelectFile(f)}
                  className={`px-2 py-1 rounded text-[10px] font-mono font-medium shrink-0 border transition-all ${
                    selectedFile?.id === f.id
                      ? 'bg-[#21262D] border-[#00E5FF] text-white'
                      : f.status === 'passed'
                      ? 'bg-emerald-950/20 text-emerald-400 border-emerald-900/50'
                      : f.status === 'failed'
                      ? 'bg-rose-950/20 text-rose-400 border-rose-900/50'
                      : 'bg-[#0B0E14] text-[#8B949E] border-[#21262D]'
                  }`}
                >
                  <span className="text-[#00E5FF] mr-1">#{i + 1}</span>
                  {f.name.replace('.c', '').replace('.h', '')}
                </button>
              ))}
            </div>
          </div>

          {/* TAB SELECTOR: LIVE EVENT STREAM VS PER-FILE VERIFICATION REPORTS */}
          <div className="h-9 px-3 bg-[#161B22]/70 border-b border-[#21262D] flex items-center justify-between text-xs shrink-0">
            <div className="flex items-center gap-1">
              <button
                onClick={() => setActiveViewTab('events')}
                className={`px-2.5 py-1 rounded text-xs font-semibold transition-colors cursor-pointer ${
                  activeViewTab === 'events' ? 'bg-[#21262D] text-[#00E5FF]' : 'text-[#8B949E] hover:text-white'
                }`}
              >
                Event Timeline
              </button>
              <button
                onClick={() => setActiveViewTab('per_file_reports')}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-semibold transition-colors cursor-pointer ${
                  activeViewTab === 'per_file_reports' ? 'bg-[#21262D] text-[#00E5FF]' : 'text-[#8B949E] hover:text-white'
                }`}
              >
                <FileText size={12} />
                <span>Reports ({perFileReports.length})</span>
              </button>
              <button
                onClick={() => setActiveViewTab('history')}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-semibold transition-colors cursor-pointer ${
                  activeViewTab === 'history' ? 'bg-[#21262D] text-[#00E5FF]' : 'text-[#8B949E] hover:text-white'
                }`}
              >
                <Clock size={12} />
                <span>History ({executionHistory.length})</span>
              </button>
            </div>

            {activeViewTab === 'events' && (
              <div className="flex items-center gap-1 text-[10px]">
                <button
                  onClick={() => setLogFilter('all')}
                  className={`px-1.5 py-0.5 rounded cursor-pointer ${logFilter === 'all' ? 'bg-[#21262D] text-white' : 'text-[#8B949E]'}`}
                >
                  All
                </button>
                <button
                  onClick={() => setLogFilter('tests')}
                  className={`px-1.5 py-0.5 rounded cursor-pointer ${logFilter === 'tests' ? 'bg-[#21262D] text-[#00E5FF]' : 'text-[#8B949E]'}`}
                >
                  Tests
                </button>
                <button
                  onClick={() => setLogFilter('diagnostics')}
                  className={`px-1.5 py-0.5 rounded cursor-pointer ${logFilter === 'diagnostics' ? 'bg-[#21262D] text-rose-400' : 'text-[#8B949E]'}`}
                >
                  Errors
                </button>
              </div>
            )}
          </div>

          {/* CONTENT: EITHER LIVE LOGS, PER-FILE REPORTS, OR RUN HISTORY */}
          {activeViewTab === 'events' ? (
            <div
              ref={logContainerRef}
              className="flex-1 overflow-y-auto p-3 font-mono text-[11px] space-y-2 bg-[#0B0E14]"
            >
              {filteredEvents.map((ev) => (
                <div
                  key={ev.id}
                  className="p-2.5 rounded bg-[#161B22]/50 border border-[#21262D] leading-tight space-y-1"
                >
                  <div className="flex items-center justify-between text-[10px] text-[#8B949E]">
                    <span>[{ev.timestamp}]</span>
                    <span
                      className={`font-semibold uppercase ${
                        ev.severity === 'error' ? 'text-rose-400 font-bold' :
                        ev.severity === 'warning' ? 'text-amber-400' :
                        ev.severity === 'success' ? 'text-emerald-400' :
                        'text-[#00E5FF]'
                      }`}
                    >
                      {ev.severity}
                    </span>
                  </div>
                  <div className="text-[#E6EDF3] leading-relaxed">{ev.message}</div>
                  {ev.line && (
                    <div className="text-[10px] text-[#00E5FF]">
                      Source Loc: {ev.fileName || 'source'}:L{ev.line}
                    </div>
                  )}
                </div>
              ))}

              {filteredEvents.length === 0 && (
                <div className="text-center py-10 text-[#8B949E] text-xs">
                  No events logged. Click "Run Flow Verification" to begin testing.
                </div>
              )}
            </div>
          ) : activeViewTab === 'per_file_reports' ? (
            /* PER-FILE EXECUTION REPORTS VIEW */
            <div className="flex-1 overflow-y-auto p-3 space-y-3 bg-[#0B0E14]">
              {perFileReports.map((report) => (
                <div
                  key={report.fileId}
                  onClick={() => setInspectedReport(report)}
                  className={`p-3.5 rounded-lg border transition-all cursor-pointer ${
                    inspectedReport?.fileId === report.fileId
                      ? 'bg-[#161B22] border-[#00E5FF]/60 shadow-md'
                      : 'bg-[#0E131B] border-[#21262D] hover:border-[#30363D]'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono text-xs font-bold text-white">
                      {report.fileName}
                    </span>
                    <span
                      className={`text-[9px] font-mono font-bold px-1.5 py-0.2 rounded uppercase ${
                        report.status === 'passed' ? 'text-emerald-400 bg-emerald-950/40 border border-emerald-900' :
                        'text-rose-400 bg-rose-950/40 border border-rose-900'
                      }`}
                    >
                      {report.status.toUpperCase()}
                    </span>
                  </div>

                  <div className="text-[11px] text-[#8B949E] font-mono">
                    {report.filePath} · DO-178C {report.criticality}
                  </div>

                  {/* SUMMARY COUNTERS */}
                  <div className="grid grid-cols-3 gap-2 mt-2 pt-2 border-t border-[#21262D] text-[10px] font-mono">
                    <div>
                      <span className="text-[#8B949E] block">PASSED</span>
                      <span className="text-emerald-400 font-bold">{report.passedTests} cases</span>
                    </div>
                    <div>
                      <span className="text-[#8B949E] block">FAILED</span>
                      <span className="text-rose-400 font-bold">{report.failedTests} cases</span>
                    </div>
                    <div>
                      <span className="text-[#8B949E] block">LINES</span>
                      <span className="text-white font-bold">{report.linesExecuted}/{report.linesTotal}</span>
                    </div>
                  </div>

                  {/* SAVED ERRORS NOTICE (DID NOT STOP EXECUTION) */}
                  {report.savedErrors.length > 0 && (
                    <div className="mt-2.5 p-2 rounded bg-rose-950/30 border border-rose-900/50 text-[10px] text-rose-300">
                      <strong>Saved {report.savedErrors.length} Error(s) Without Halting:</strong>
                      <div className="truncate mt-0.5">
                        Line {report.savedErrors[0].line}: {report.savedErrors[0].message}
                      </div>
                    </div>
                  )}

                  {/* TESTED VECTORS PREVIEW */}
                  <div className="mt-2 space-y-1">
                    <span className="text-[9px] font-mono text-[#8B949E] uppercase block">
                      Requirement Vectors Tested:
                    </span>
                    {report.testedVectors.map((v) => (
                      <div key={v.testId} className="flex items-center justify-between text-[10px] font-mono">
                        <span className="text-[#CBD5E1] truncate">{v.requirementId}: {v.testTitle}</span>
                        <span className={v.passed ? "text-emerald-400 font-bold" : "text-rose-400 font-bold"}>
                          {v.passed ? 'PASS' : 'FAIL'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}

              {perFileReports.length === 0 && (
                <div className="text-center py-12 text-[#8B949E] text-xs">
                  No per-file execution reports yet. Run verification to generate individual reports for each file in sequence.
                </div>
              )}
            </div>
          ) : (
            /* RUN HISTORY TAB WITH RERUN ACTION */
            <div className="flex-1 overflow-y-auto p-3 space-y-3 bg-[#0B0E14]">
              {executionHistory.map((run) => (
                <div
                  key={run.id}
                  className="p-3.5 rounded-lg bg-[#0E131B] border border-[#21262D] space-y-2.5"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-white">
                        #{run.id.substring(0, 12)}
                      </span>
                      <span className={`text-[9px] font-mono font-bold px-1.5 py-0.2 rounded uppercase ${
                        run.status === 'PASSED' ? 'text-emerald-400 bg-emerald-950/40 border border-emerald-900' :
                        run.status === 'FAILED' ? 'text-rose-400 bg-rose-950/40 border border-rose-900' :
                        'text-[#8B949E] bg-[#161B22]'
                      }`}>
                        {run.status}
                      </span>
                    </div>

                    {onRerunExecution && (
                      <button
                        onClick={() => onRerunExecution(run.id)}
                        className="flex items-center gap-1 px-2.5 py-1 rounded bg-[#21262D] hover:bg-[#30363D] text-[10px] font-semibold text-[#00E5FF] border border-[#30363D] transition-colors cursor-pointer"
                        title="Rerun previous test configuration against current source revision"
                      >
                        <RotateCcw size={11} />
                        <span>Rerun on Current Code</span>
                      </button>
                    )}
                  </div>

                  <div className="text-[11px] text-[#8B949E] font-mono flex items-center justify-between">
                    <span>Duration: {(run.duration_ms || 0).toFixed(1)}ms</span>
                    <span>{run.created_at ? new Date(run.created_at).toLocaleTimeString() : 'Recorded'}</span>
                  </div>

                  {run.results_summary && (
                    <div className="p-2 rounded bg-black/40 text-[10px] font-mono text-[#CBD5E1] space-y-1">
                      <div>Passed: {run.results_summary.passed_count ?? 1} / {run.results_summary.total_count ?? 1} Vectors</div>
                      {run.results_summary.coverage_pct !== undefined && (
                        <div className="text-emerald-400">Achieved Coverage: {run.results_summary.coverage_pct}%</div>
                      )}
                    </div>
                  )}
                </div>
              ))}

              {executionHistory.length === 0 && (
                <div className="text-center py-12 text-[#8B949E] text-xs">
                  {isLoadingHistory ? 'Loading verification history...' : 'No prior execution runs recorded yet for this project.'}
                </div>
              )}
            </div>
          )}

          {/* LOG FOOTER CONTROLS */}
          <div className="p-2 bg-[#161B22] border-t border-[#21262D] flex items-center justify-between text-[10px] text-[#8B949E]">
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                className="rounded bg-[#0B0E14] border-[#30363D]"
              />
              <span>Auto-scroll stream</span>
            </label>
            <span className="font-mono">{filteredEvents.length} events logged</span>
          </div>
        </div>
      </div>
    </div>
  );
};
