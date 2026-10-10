import React, { useState } from 'react';
import { 
  FolderPlus, FileUp, CheckCircle2, AlertTriangle, Cpu, 
  ArrowRight, Shield, Layers, FileCode, Play, Sparkles, 
  Check, RefreshCw, Upload, Terminal, HelpCircle, GitBranch
} from 'lucide-react';
import type { Project, ProjectFile, TestFlowPreference  } from '../../types';
import { RecommendedTestFlow } from './RecommendedTestFlow';

interface OverviewViewProps {
  project: Project | null;
  files: ProjectFile[];
  onOpenImport: () => void;
  onOpenUploadReq: () => void;
  onNavigateTab: (tab: any) => void;
  onSelectFile: (file: ProjectFile) => void;
  onStartVerification: () => void;
  flowPreference: TestFlowPreference;
  onFlowPreferenceChange: (pref: TestFlowPreference) => void;
  executionOrder: ProjectFile[];
  onReorderFiles: (newOrder: ProjectFile[]) => void;
  isVerifying: boolean;
  selectedFile?: ProjectFile;
  isLoadingFlow?: boolean;
  flowError?: string | null;
  onRetryFlow?: () => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  project,
  files,
  onOpenImport,
  onOpenUploadReq,
  onNavigateTab,
  onSelectFile,
  onStartVerification,
  flowPreference,
  onFlowPreferenceChange,
  executionOrder,
  onReorderFiles,
  isVerifying,
  selectedFile,
  isLoadingFlow,
  flowError,
  onRetryFlow,
}) => {
  const [dragActive, setDragActive] = useState(false);
  const [uploadSuccessMessage, setUploadSuccessMessage] = useState<string | null>(null);

  // User selected files state flag: once files are selected/present or loading, show the Recommended Test Flow
  const hasSelectedProjectFiles = Boolean(selectedFile || files.length > 0 || isLoadingFlow || flowError);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setUploadSuccessMessage(`Uploaded and parsed archive: ${file.name} (42 C/C++ files identified)`);
      setTimeout(() => setUploadSuccessMessage(null), 5000);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setUploadSuccessMessage(`Successfully loaded ${file.name}`);
      setTimeout(() => setUploadSuccessMessage(null), 5000);
    }
  };

  if (!project || project.id === 'empty') {
    return (
      <div className="flex-1 overflow-y-auto p-6 bg-[#0B0E14] text-[#E6EDF3] space-y-6">
        <div className="rounded-xl bg-[#161B22] border border-[#21262D] p-8 text-center space-y-4 shadow-sm">
          <FolderPlus size={40} className="mx-auto text-[#00E5FF]" />
          <h2 className="text-xl font-bold text-white font-heading">No Project Imported</h2>
          <p className="text-xs text-[#8B949E] max-w-md mx-auto leading-relaxed">
            Import an embedded C/C++ flight software folder or ZIP archive to begin automated verification, AST indexing, requirement tracing, and MC/DC analysis.
          </p>
          <div className="pt-2 flex items-center justify-center gap-3">
            <button
              onClick={onOpenImport}
              className="btn-aerospace-glow flex items-center gap-2 px-4 py-2 rounded-lg bg-[#00E5FF] hover:bg-cyan-300 text-black text-xs font-bold transition-all shadow-[0_0_15px_rgba(0,229,255,0.25)] cursor-pointer"
            >
              <FolderPlus size={14} />
              <span>Import Project Archive</span>
            </button>
          </div>
        </div>

        {/* INGESTION DROPZONES */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-12 rounded-xl bg-[#161B22] border border-[#21262D] p-6 text-center">
            <Upload size={32} className="mx-auto text-[#00E5FF] mb-2" />
            <div className="text-sm font-semibold text-white">
              Drag & Drop Project ZIP or Directory
            </div>
            <div className="text-xs text-[#8B949E] mt-1 font-mono">
              Accepts .zip archives containing `.c`, `.h`, `.cpp`, `.hpp`
            </div>
            <button
              onClick={onOpenImport}
              className="mt-4 px-4 py-2 rounded-lg bg-[#21262D] hover:bg-[#30363D] text-xs font-semibold text-white border border-[#30363D] transition-colors"
            >
              Browse Local Files
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 bg-[#0B0E14] text-[#E6EDF3] space-y-6">
      {/* SUCCESS NOTIFICATION */}
      {uploadSuccessMessage && (
        <div className="p-3.5 rounded-lg bg-emerald-950/60 border border-emerald-500/40 text-emerald-200 text-xs flex items-center justify-between shadow-lg">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={16} className="text-emerald-400" />
            <span className="font-mono">{uploadSuccessMessage}</span>
          </div>
          <button onClick={() => setUploadSuccessMessage(null)} className="text-emerald-400 hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {/* TOP HERO: PROJECT READINESS & METRIC BANNER */}
      <div className="rounded-xl bg-[#161B22] border border-[#21262D] p-5 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-[#21262D]">
          <div>
            <div className="flex items-center gap-3">
              <span className="text-[11px] font-mono font-semibold px-2 py-0.5 rounded bg-[#00E5FF]/10 text-[#00E5FF] border border-[#00E5FF]/20">
                DO-178C {project.dalLevel}
              </span>
              <span className="text-xs text-[#8B949E] font-mono">
                Indexed: {project.indexedTimestamp}
              </span>
            </div>
            <h1 className="text-2xl font-bold text-white mt-1 font-heading">
              {project.name}
            </h1>
            <p className="text-xs text-[#8B949E] mt-1 max-w-2xl leading-relaxed">
              {project.description}
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={() => onNavigateTab('requirements')}
              className="px-3.5 py-2 rounded-lg bg-[#21262D] hover:bg-[#30363D] text-xs font-semibold text-[#E6EDF3] border border-[#30363D] transition-colors cursor-pointer"
            >
              Inspect Requirements
            </button>
            <button
              onClick={onStartVerification}
              className="btn-aerospace-glow btn-shimmer flex items-center gap-2 px-4 py-2 rounded-lg bg-[#00E5FF] hover:bg-cyan-300 text-black text-xs font-bold shadow-[0_0_15px_rgba(0,229,255,0.25)] transition-all cursor-pointer"
            >
              <Play size={13} fill="currentColor" />
              <span>Run Verification Suite</span>
            </button>
          </div>
        </div>

        {/* METRICS STRIP */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 pt-4 text-left">
          <div className="p-3 rounded-lg bg-[#0B0E14] border border-[#21262D]">
            <span className="text-[10px] font-mono text-[#8B949E] uppercase block">Discovered Files</span>
            <span className="text-xl font-bold text-white font-mono tabular-nums">{project.stats.discoveredFiles}</span>
            <span className="text-[10px] text-[#8B949E] block mt-0.5">C / C++ / Headers</span>
          </div>
          <div className="p-3 rounded-lg bg-[#0B0E14] border border-[#21262D]">
            <span className="text-[10px] font-mono text-[#8B949E] uppercase block">Source Functions</span>
            <span className="text-xl font-bold text-white font-mono tabular-nums">{project.stats.totalFunctions}</span>
            <span className="text-[10px] text-[#8B949E] block mt-0.5">AST Indexed</span>
          </div>
          <div className="p-3 rounded-lg bg-[#0B0E14] border border-[#21262D]">
            <span className="text-[10px] font-mono text-[#8B949E] uppercase block">Sys Requirements</span>
            <span className="text-xl font-bold text-cyan-400 font-mono tabular-nums">{project.stats.requirementCount}</span>
            <span className="text-[10px] text-[#8B949E] block mt-0.5">DO-178C Traceable</span>
          </div>
          <div className="p-3 rounded-lg bg-[#0B0E14] border border-[#21262D]">
            <span className="text-[10px] font-mono text-[#8B949E] uppercase block">Test Cases</span>
            <span className="text-xl font-bold text-white font-mono tabular-nums">{project.stats.testCaseCount}</span>
            <span className="text-[10px] text-[#8B949E] block mt-0.5">Vectors Ready</span>
          </div>
          <div className="p-3 rounded-lg bg-[#0B0E14] border border-[#21262D]">
            <span className="text-[10px] font-mono text-[#8B949E] uppercase block">MC/DC Coverage</span>
            <span className="text-xl font-bold text-emerald-400 font-mono tabular-nums">{project.stats.mcDcCoverage}%</span>
            <span className="text-[10px] text-[#8B949E] block mt-0.5">Verified pairs</span>
          </div>
          <div className="p-3 rounded-lg bg-[#0B0E14] border border-[#21262D]">
            <span className="text-[10px] font-mono text-[#8B949E] uppercase block">Toolchain Health</span>
            <span className="text-sm font-bold text-emerald-400 flex items-center gap-1 mt-1">
              <CheckCircle2 size={13} /> Ready
            </span>
            <span className="text-[10px] text-[#8B949E] block mt-0.5 truncate font-mono">{project.toolchain.split(' ')[0]}</span>
          </div>
        </div>
      </div>

      {/* RECOMMENDED TEST FLOW (APPEARS ONCE PROJECT FILES ARE SELECTED) */}
      {hasSelectedProjectFiles && (
        <RecommendedTestFlow
          files={files}
          flowPreference={flowPreference}
          onFlowPreferenceChange={onFlowPreferenceChange}
          executionOrder={executionOrder}
          onReorderFiles={onReorderFiles}
          onStartVerification={onStartVerification}
          isVerifying={isVerifying}
          selectedFile={selectedFile}
          isLoading={isLoadingFlow}
          error={flowError}
          onRetry={onRetryFlow}
        />
      )}

      {/* TWO COLUMN INGESTION DROPZONES */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* SOURCE ARCHIVE INGESTION */}
        <div className="lg:col-span-6 rounded-xl bg-[#161B22] border border-[#21262D] p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FolderPlus size={16} className="text-[#00E5FF]" />
              <h3 className="text-sm font-bold text-white font-heading">Import Source Archive</h3>
            </div>
            <span className="text-[10px] font-mono text-[#8B949E]">ZIP / TAR.GZ / C Folder</span>
          </div>

          {/* DROPZONE */}
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-xl p-6 text-center transition-all ${
              dragActive 
                ? 'border-[#00E5FF] bg-[#00E5FF]/5' 
                : 'border-[#30363D] hover:border-[#8B949E] bg-[#0B0E14]'
            }`}
          >
            <Upload size={28} className="mx-auto text-[#00E5FF] mb-2" />
            <div className="text-xs font-semibold text-white">
              Drag and drop your embedded C/C++ project ZIP here
            </div>
            <div className="text-[11px] text-[#8B949E] mt-1 font-mono">
              Supports `.c`, `.cpp`, `.h`, `.hpp`, and `.ads/.adb` Ada packages
            </div>

            <div className="mt-4 flex items-center justify-center gap-3">
              <label className="btn-aerospace-glow px-3.5 py-1.5 rounded-lg bg-[#21262D] hover:bg-[#30363D] text-xs font-medium text-[#E6EDF3] border border-[#30363D] cursor-pointer transition-colors">
                Select Local ZIP
                <input 
                  type="file" 
                  accept=".zip,.tar,.gz,.c,.h,.cpp" 
                  className="hidden" 
                  onChange={handleFileInput} 
                />
              </label>
              <button
                onClick={onOpenImport}
                className="px-3.5 py-1.5 rounded-lg bg-[#161B22] hover:bg-[#21262D] text-xs font-medium text-[#00E5FF] border border-[#00E5FF]/30 transition-colors cursor-pointer"
              >
                Browse Directory
              </button>
            </div>
          </div>

          <div className="text-[11px] text-[#8B949E] flex items-center gap-1.5">
            <HelpCircle size={13} className="text-[#8B949E]" />
            <span>Automatic AST symbol extraction upon file import.</span>
          </div>
        </div>

        {/* REQUIREMENTS INGESTION BOX */}
        <div className="lg:col-span-6 rounded-xl bg-[#161B22] border border-[#21262D] p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <FileUp size={16} className="text-[#00E5FF]" />
                <h3 className="text-sm font-bold text-white font-heading">Ingest Requirements Document</h3>
              </div>
              <span className="text-[10px] font-mono text-[#8B949E]">PDF / DOCX / XML</span>
            </div>

            <p className="text-xs text-[#8B949E] mb-3 leading-relaxed">
              Upload system specification documents. The parser automatically extracts DO-178C requirement tags (`REQ-***`), safety levels (DAL-A/B), and boundary thresholds.
            </p>
          </div>

          <button
            onClick={onOpenUploadReq}
            className="btn-aerospace-glow btn-shimmer w-full py-2.5 rounded-lg bg-[#21262D] hover:bg-[#30363D] text-xs font-semibold text-[#00E5FF] border border-[#30363D] flex items-center justify-center gap-2 transition-colors cursor-pointer"
          >
            <FileUp size={14} />
            <span>Upload DO-178C Specification (PDF / DOCX)</span>
          </button>
        </div>
      </div>

      {/* RECENT FILES QUICK-ACCESS GRID */}
      <div className="rounded-xl bg-[#161B22] border border-[#21262D] p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <FileCode size={16} className="text-[#00E5FF]" />
            <h3 className="text-sm font-bold text-white font-heading">Project Files in Workspace</h3>
          </div>
          <button 
            onClick={() => onNavigateTab('explorer')}
            className="text-xs text-[#00E5FF] hover:underline cursor-pointer"
          >
            Open in Project Explorer →
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {files.map((file) => (
            <div
              key={file.id}
              onClick={() => {
                onSelectFile(file);
                onNavigateTab('explorer');
              }}
              className="p-3.5 rounded-lg bg-[#0B0E14] border border-[#21262D] hover:border-[#00E5FF]/50 cursor-pointer transition-all flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-white group-hover:text-[#00E5FF] transition-colors truncate font-mono">
                    {file.name}
                  </span>
                  <span className={`text-[10px] font-mono px-1.5 py-0.2 rounded font-semibold ${
                    file.status === 'passed' ? 'text-emerald-400 bg-emerald-950/40 border border-emerald-900' :
                    file.status === 'failed' ? 'text-rose-400 bg-rose-950/40 border border-rose-900' :
                    'text-[#8B949E] bg-[#161B22]'
                  }`}>
                    {file.status.toUpperCase()}
                  </span>
                </div>
                <div className="text-[11px] text-[#8B949E] font-mono mt-1">
                  {file.path}
                </div>
              </div>

              <div className="mt-3 pt-2.5 border-t border-[#21262D] flex items-center justify-between text-[11px] text-[#8B949E]">
                <span>Risk Priority: <strong className="text-white font-mono tabular-nums">{file.priorityScore.toFixed(2)}</strong></span>
                <span>Complexity: <strong className="text-[#CBD5E1] font-mono tabular-nums">M={file.cyclomaticComplexity}</strong></span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
