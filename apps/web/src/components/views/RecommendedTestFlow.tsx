import React from 'react';
import { 
  GitBranch, Sparkles, Sliders, ArrowRight, Play, 
  ArrowUp, ArrowDown, CheckCircle2, AlertCircle, Shield, 
  FileCode, Cpu, Check, Layers, Clock, AlertTriangle, RefreshCw
} from 'lucide-react';
import type { ProjectFile, TestFlowPreference } from '../../types';

interface RecommendedTestFlowProps {
  files: ProjectFile[];
  flowPreference: TestFlowPreference;
  onFlowPreferenceChange: (pref: TestFlowPreference) => void;
  executionOrder: ProjectFile[];
  onReorderFiles: (newOrder: ProjectFile[]) => void;
  onStartVerification: () => void;
  isVerifying: boolean;
  selectedFile?: ProjectFile;
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}

export const RecommendedTestFlow: React.FC<RecommendedTestFlowProps> = ({
  files,
  flowPreference,
  onFlowPreferenceChange,
  executionOrder,
  onReorderFiles,
  onStartVerification,
  isVerifying,
  selectedFile,
  isLoading = false,
  error = null,
  onRetry,
}) => {
  // Move item up in custom order
  const handleMoveUp = (index: number) => {
    if (index === 0) return;
    const updated = [...executionOrder];
    const temp = updated[index];
    updated[index] = updated[index - 1];
    updated[index - 1] = temp;
    onReorderFiles(updated);
  };

  // Move item down in custom order
  const handleMoveDown = (index: number) => {
    if (index === executionOrder.length - 1) return;
    const updated = [...executionOrder];
    const temp = updated[index];
    updated[index] = updated[index + 1];
    updated[index + 1] = temp;
    onReorderFiles(updated);
  };

  return (
    <div className="rounded-xl bg-[#161B22] border border-[#21262D] p-5 space-y-4 shadow-sm">
      {/* HEADER & FLOW PREFERENCE SELECTION */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-[#21262D]">
        <div>
          <div className="flex items-center gap-2">
            <GitBranch size={17} className="text-[#00E5FF]" />
            <h3 className="text-base font-bold text-white font-heading">
              Recommended Test Flow
            </h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#00E5FF]/10 text-[#00E5FF] border border-[#00E5FF]/20">
              Execution Sequence
            </span>
          </div>
          <p className="text-xs text-[#8B949E] mt-1 leading-relaxed">
            Specifies the prioritized file sequence for automated requirement assertions, dynamic input testing, and DO-178C validation.
          </p>
        </div>

        {/* FLOW BRANCH SELECTOR */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2">
          <span className="text-[10px] font-mono uppercase text-[#8B949E] tracking-wider font-semibold mr-1">
            Flow Selection:
          </span>

          <div className="flex items-center p-0.5 bg-[#0B0E14] rounded-lg border border-[#30363D]">
            {/* BRANCH 1: AI RECOMMENDED */}
            <button
              onClick={() => onFlowPreferenceChange('ai_recommended')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                flowPreference === 'ai_recommended'
                  ? 'bg-[#161B22] text-[#00E5FF] shadow-sm border border-[#00E5FF]/30'
                  : 'text-[#8B949E] hover:text-white'
              }`}
            >
              <Sparkles size={13} className={flowPreference === 'ai_recommended' ? "text-[#00E5FF]" : "text-[#8B949E]"} />
              <span>AI Recommended Priority</span>
            </button>

            {/* BRANCH 2: CUSTOM ENGINEER ORDER */}
            <button
              onClick={() => onFlowPreferenceChange('custom_order')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                flowPreference === 'custom_order'
                  ? 'bg-[#161B22] text-[#00E5FF] shadow-sm border border-[#00E5FF]/30'
                  : 'text-[#8B949E] hover:text-white'
              }`}
            >
              <Sliders size={13} className={flowPreference === 'custom_order' ? "text-[#00E5FF]" : "text-[#8B949E]"} />
              <span>Custom Engineer Order</span>
            </button>
          </div>
        </div>
      </div>

      {/* FLOW BRANCH DESCRIPTION BANNER */}
      <div className="p-3 rounded-lg bg-[#0B0E14] border border-[#21262D] flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          {flowPreference === 'ai_recommended' ? (
            <>
              <span className="w-2 h-2 rounded-full bg-[#00E5FF] shadow-[0_0_8px_rgba(0,229,255,0.8)]" />
              <span className="text-[#CBD5E1]">
                <strong>Priority Ordering Active:</strong> Sequenced by safety criticality, complexity risk, and test failure history.
              </span>
            </>
          ) : (
            <>
              <span className="w-2 h-2 rounded-full bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.8)]" />
              <span className="text-[#CBD5E1]">
                <strong>Custom Engineer Order Active:</strong> Manual pipeline sequence configured. Use arrow buttons below to customize file test sequence.
              </span>
            </>
          )}
        </div>

        <span className="text-[10px] font-mono text-[#8B949E]">
          {executionOrder.length} {executionOrder.length === 1 ? 'file' : 'files'} scheduled
        </span>
      </div>

      {/* LOADING STATE */}
      {isLoading && (
        <div className="p-8 rounded-lg bg-[#0B0E14] border border-[#21262D] text-center space-y-2">
          <RefreshCw size={20} className="mx-auto text-[#00E5FF] animate-spin" />
          <div className="text-xs text-white font-medium">Analyzing project files & computing priority sequence...</div>
          <div className="text-[11px] text-[#8B949E]">Fetching file tree AST and verified prioritization rankings.</div>
        </div>
      )}

      {/* ERROR STATE */}
      {!isLoading && error && (
        <div className="p-4 rounded-lg bg-rose-950/40 border border-rose-800/60 text-xs text-rose-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle size={16} className="text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
          {onRetry && (
            <button
              onClick={onRetry}
              className="px-2.5 py-1 rounded bg-rose-900/60 hover:bg-rose-800 text-[11px] font-semibold text-rose-100 flex items-center gap-1 transition-colors"
            >
              <RefreshCw size={12} />
              <span>Retry</span>
            </button>
          )}
        </div>
      )}

      {/* EMPTY STATE */}
      {!isLoading && !error && executionOrder.length === 0 && (
        <div className="p-8 rounded-lg bg-[#0B0E14] border border-[#21262D] text-center space-y-2">
          <FileCode size={24} className="mx-auto text-[#8B949E]" />
          <div className="text-xs text-white font-semibold">No source files available in current project</div>
          <div className="text-[11px] text-[#8B949E]">
            Import a C/C++ archive (.zip, .c, .h) or select a project with source files to generate a recommended execution sequence.
          </div>
        </div>
      )}

      {/* SEQUENCED FLOW CARDS (STEP-BY-STEP FLOW OF FILES TO EXECUTE IN ORDER) */}
      {!isLoading && !error && executionOrder.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-[10px] font-mono uppercase text-[#8B949E] px-2">
            <span>Execution Order Sequence</span>
            <span>Priority & Criticality</span>
          </div>

          <div className="grid grid-cols-1 gap-2">
            {executionOrder.map((file, idx) => {
              const isFirst = idx === 0;
              const isLast = idx === executionOrder.length - 1;
              const isCurrentlySelected = selectedFile?.id === file.id;
              const stepNumber = String(idx + 1).padStart(2, '0');
              const isEstimate = file.scoreReliability === 'estimated';

              return (
                <div
                  key={file.id}
                  className={`p-3 rounded-lg border flex items-center justify-between transition-all ${
                    isCurrentlySelected
                      ? 'bg-[#161B22] border-[#00E5FF]/60 shadow-sm'
                      : 'bg-[#0B0E14] border-[#21262D] hover:border-[#30363D]'
                  }`}
                >
                  {/* LEFT: STEP NUMBER & FILE INFO */}
                  <div className="flex items-center gap-3 min-w-0 pr-3">
                    <div className="w-7 h-7 rounded-md bg-[#161B22] border border-[#30363D] flex items-center justify-center font-mono text-xs font-bold text-[#00E5FF] shrink-0">
                      {stepNumber}
                    </div>

                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-semibold text-white truncate">
                          {file.name}
                        </span>
                        <span className="text-[10px] font-mono text-[#8B949E] truncate hidden sm:inline">
                          ({file.path})
                        </span>
                      </div>
                      <div className="text-[11px] text-[#8B949E] mt-0.5 line-clamp-1">
                        {file.priorityRationale?.summary || 'Standard module verification'}
                      </div>
                    </div>
                  </div>

                  {/* RIGHT: METRICS & REORDER ACTIONS */}
                  <div className="flex items-center gap-2 sm:gap-3 shrink-0">
                    {/* Criticality Badge */}
                    <span
                      title={file.criticality ? `DO-178C ${file.criticality}` : 'No verified requirement DAL classification'}
                      className="text-[10px] font-mono font-bold text-white px-2 py-0.5 bg-[#161B22] border border-[#21262D] rounded"
                    >
                      {file.criticality || 'Unknown'}
                    </span>

                    {/* Priority Score Badge */}
                    <div className="flex items-center gap-1">
                      <span className="text-xs font-mono font-bold text-[#00E5FF] px-2 py-0.5 bg-[#00E5FF]/10 rounded border border-[#00E5FF]/20">
                        P: {file.priorityScore.toFixed(2)}
                      </span>
                      {isEstimate && (
                        <span
                          title="Estimated score based on AST static attributes (source lines, complexity, language). Real verification history not yet recorded."
                          className="text-[9px] font-mono uppercase px-1 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        >
                          est
                        </span>
                      )}
                    </div>

                    {/* CUSTOM REORDER CONTROLS (ONLY IN CUSTOM ORDER BRANCH) */}
                    {flowPreference === 'custom_order' && (
                      <div className="flex items-center gap-1 border-l border-[#21262D] pl-2">
                        <button
                          onClick={() => handleMoveUp(idx)}
                          disabled={isFirst}
                          className="p-1 rounded hover:bg-[#21262D] text-[#8B949E] hover:text-white disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed"
                          title="Move up in order"
                        >
                          <ArrowUp size={13} />
                        </button>
                        <button
                          onClick={() => handleMoveDown(idx)}
                          disabled={isLast}
                          className="p-1 rounded hover:bg-[#21262D] text-[#8B949E] hover:text-white disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed"
                          title="Move down in order"
                        >
                          <ArrowDown size={13} />
                        </button>
                      </div>
                    )}

                    {/* STATUS ICON */}
                    <div className="w-6 text-center">
                      {file.status === 'passed' && (
                        <span title="Passed" className="inline-flex items-center justify-center">
                          <CheckCircle2 size={14} className="text-emerald-400" />
                        </span>
                      )}
                      {file.status === 'failed' && (
                        <span title="Failed" className="inline-flex items-center justify-center">
                          <AlertCircle size={14} className="text-rose-400" />
                        </span>
                      )}
                      {file.status === 'idle' && (
                        <span className="text-[10px] text-[#8B949E] font-mono" title="Not assessed">
                          —
                        </span>
                      )}
                      {file.status === 'running' && (
                        <span title="Verifying" className="inline-flex items-center justify-center">
                          <RefreshCw size={14} className="text-cyan-400 animate-spin" />
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* EXECUTION TRIGGER IN RECOMMENDED ORDER */}
      {executionOrder.length > 0 && (
        <div className="pt-3 border-t border-[#21262D] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="text-xs text-[#8B949E]">
            Ready to verify? The harness will test each module against requirements in this exact flow.
          </div>

          <button
            onClick={onStartVerification}
            disabled={isVerifying}
            className="btn-aerospace-glow btn-shimmer flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#00E5FF] hover:bg-cyan-300 text-black text-xs font-bold transition-all shrink-0 cursor-pointer disabled:opacity-50"
          >
            <Play size={14} fill="currentColor" />
            <span>
              {isVerifying ? 'Verifying Flow...' : `Run Verification in ${flowPreference === 'ai_recommended' ? 'AI Recommended' : 'Custom'} Order`}
            </span>
          </button>
        </div>
      )}
    </div>
  );
};

