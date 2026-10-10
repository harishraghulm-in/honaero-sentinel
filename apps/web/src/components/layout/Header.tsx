import React from 'react';
import { 
  Play, Square, FolderPlus, FileUp, Settings, 
  ChevronDown, Server, Cpu, Check, AlertCircle, RefreshCw
} from 'lucide-react';
import { HonAeroLogo } from '../brand/HonAeroLogo';
import type { Project, RunStatus  } from '../../types';

interface HeaderProps {
  projects: Project[];
  activeProject: Project | null;
  onSelectProject: (p: Project) => void;
  runStatus: RunStatus;
  progress: number;
  onStartVerification: () => void;
  onCancelVerification: () => void;
  onOpenImportModal: () => void;
  onOpenUploadReqModal: () => void;
  onOpenSettingsModal: () => void;
  isBackendConnected: boolean;
  onToggleBackend: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  projects,
  activeProject,
  onSelectProject,
  runStatus,
  progress,
  onStartVerification,
  onCancelVerification,
  onOpenImportModal,
  onOpenUploadReqModal,
  onOpenSettingsModal,
  isBackendConnected,
  onToggleBackend,
}) => {
  const [projectDropdownOpen, setProjectDropdownOpen] = React.useState(false);

  return (
    <header className="h-16 bg-[#0B0E14] border-b border-[#21262D] px-4 flex items-center justify-between gap-4 z-30 shrink-0 select-none">
      {/* LEFT: Official HonAero Sentinel Logo & Brand */}
      <div className="flex items-center gap-5">
        <HonAeroLogo size="md" showSubtitle={true} />

        <div className="h-7 w-[1px] bg-[#21262D] hidden md:block" />

        {/* ACTIVE PROJECT SELECTOR */}
        <div className="relative">
          <button
            onClick={() => setProjectDropdownOpen(!projectDropdownOpen)}
            className="flex items-center gap-2.5 px-3 py-1.5 rounded bg-[#161B22] border border-[#30363D] hover:border-[#00E5FF]/40 text-left transition-colors"
          >
            <div className="flex flex-col">
              <span className="text-[9px] uppercase tracking-wider text-[#8B949E] font-medium leading-none">
                Active Project
              </span>
              <span className="text-xs font-semibold text-[#E6EDF3] mt-0.5 truncate max-w-[190px]">
                {activeProject ? activeProject.name : 'No Project Selected'}
              </span>
            </div>
            <span className="text-[10px] font-mono font-bold text-[#00E5FF] px-1.5 py-0.5 bg-[#00E5FF]/10 rounded border border-[#00E5FF]/20">
              {activeProject ? activeProject.dalLevel : 'DAL-?'}
            </span>
            <ChevronDown size={14} className="text-[#8B949E]" />
          </button>

          {projectDropdownOpen && (
            <div className="absolute left-0 top-full mt-1.5 w-72 bg-[#161B22] border border-[#30363D] rounded-lg shadow-2xl py-1 z-50">
              <div className="px-3 py-1.5 border-b border-[#21262D] text-[10px] font-mono text-[#8B949E] uppercase">
                Select Workspace Project
              </div>
              {projects.map((p) => (
                <button
                  key={p.id}
                  onClick={() => {
                    onSelectProject(p);
                    setProjectDropdownOpen(false);
                  }}
                  className={`w-full text-left px-3 py-2 flex items-center justify-between hover:bg-[#21262D] transition-colors ${
                    activeProject && p.id === activeProject.id ? 'bg-[#00E5FF]/10 text-[#00E5FF]' : 'text-[#E6EDF3]'
                  }`}
                >
                  <div>
                    <div className="text-xs font-medium">{p.name}</div>
                    <div className="text-[10px] text-[#8B949E]">{p.codeName} · {p.dalLevel}</div>
                  </div>
                  {activeProject && p.id === activeProject.id && <Check size={14} className="text-[#00E5FF]" />}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* CENTER: Verification Engine & Backend Status */}
      <div className="hidden lg:flex items-center gap-3">
        {/* Backend Engine Link */}
        <button
          onClick={onToggleBackend}
          title="Click to toggle between Native C++ Engine Simulator and Remote FastAPI backend"
          className="flex items-center gap-2 px-2.5 py-1 rounded bg-[#161B22] border border-[#21262D] hover:border-[#30363D] transition-colors"
        >
          <Server size={13} className={isBackendConnected ? "text-[#00E5FF]" : "text-[#8B949E]"} />
          <div className="flex flex-col text-left">
            <span className="text-[9px] uppercase tracking-wider text-[#8B949E] font-medium leading-none">
              Engine Mode
            </span>
            <span className="text-[11px] font-mono text-[#CBD5E1]">
              {isBackendConnected ? 'FastAPI :8001' : 'C++ Engine [Demo Mode]'}
            </span>
          </div>
          <span className={`w-2 h-2 rounded-full ${isBackendConnected ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]' : 'bg-cyan-400'}`} />
        </button>

        {/* Current Run Status Indicator */}
        <div className="flex items-center gap-2 px-2.5 py-1 rounded bg-[#161B22] border border-[#21262D]">
          <Cpu size={13} className="text-[#8B949E]" />
          <div className="flex flex-col text-left">
            <span className="text-[9px] uppercase tracking-wider text-[#8B949E] font-medium leading-none">
              Run Status
            </span>
            <span className="text-[11px] font-mono uppercase font-semibold">
              {runStatus === 'running' && (
                <span className="text-[#00E5FF] flex items-center gap-1.5">
                  <RefreshCw size={11} className="animate-spin" /> Verifying ({progress}%)
                </span>
              )}
              {runStatus === 'idle' && <span className="text-[#8B949E]">Standby</span>}
              {runStatus === 'completed' && <span className="text-emerald-400">Completed</span>}
              {runStatus === 'cancelled' && <span className="text-amber-400">Cancelled</span>}
            </span>
          </div>
        </div>
      </div>

      {/* RIGHT: Actions */}
      <div className="flex items-center gap-2.5">
        <button
          onClick={onOpenImportModal}
          className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#CBD5E1] bg-[#161B22] hover:bg-[#21262D] border border-[#30363D] rounded-md transition-colors"
          title="Import project files (ZIP or folder)"
        >
          <FolderPlus size={14} className="text-[#00E5FF]" />
          <span>Import Project</span>
        </button>

        <button
          onClick={onOpenUploadReqModal}
          className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#CBD5E1] bg-[#161B22] hover:bg-[#21262D] border border-[#30363D] rounded-md transition-colors"
          title="Ingest DO-178C PDF / DOCX requirement document"
        >
          <FileUp size={14} className="text-[#00E5FF]" />
          <span>Upload Req</span>
        </button>

        {/* PRIMARY ACTION: RUN VERIFICATION / STOP */}
        {runStatus === 'running' ? (
          <button
            onClick={onCancelVerification}
            className="flex items-center gap-2 px-4 py-1.5 text-xs font-bold text-black bg-amber-400 hover:bg-amber-300 rounded-md shadow-md transition-colors cursor-pointer"
          >
            <Square size={13} fill="currentColor" />
            <span>Cancel Run</span>
          </button>
        ) : (
          <button
            onClick={onStartVerification}
            className="btn-aerospace-glow btn-shimmer flex items-center gap-2 px-4 py-1.5 text-xs font-bold text-black bg-[#00E5FF] hover:bg-cyan-300 rounded-md transition-all cursor-pointer"
          >
            <Play size={13} fill="currentColor" />
            <span>Run Verification</span>
          </button>
        )}

        <button
          onClick={onOpenSettingsModal}
          className="p-2 text-[#8B949E] hover:text-[#E6EDF3] hover:bg-[#161B22] rounded-md transition-colors"
          title="Toolchain and Verification Settings"
        >
          <Settings size={17} />
        </button>
      </div>
    </header>
  );
};
