import React from 'react';
import { GitBranch, Cpu, ShieldCheck, Terminal, Radio, HardDrive } from 'lucide-react';
import type { Project, ProjectFile  } from '../../types';

interface StatusBarProps {
  activeProject: Project | null;
  activeFile?: ProjectFile;
  isBackendConnected: boolean;
  totalEventsCount: number;
  unresolvedIssuesCount: number;
}

export const StatusBar: React.FC<StatusBarProps> = ({
  activeProject,
  activeFile,
  isBackendConnected,
  totalEventsCount,
  unresolvedIssuesCount,
}) => {
  return (
    <footer className="h-7 bg-[#0B0E14] border-t border-[#21262D] px-3 flex items-center justify-between text-[11px] font-mono text-[#8B949E] shrink-0 select-none z-20">
      <div className="flex items-center gap-4">
        {/* Project & Branch */}
        <div className="flex items-center gap-1.5 text-[#CBD5E1]">
          <GitBranch size={13} className="text-[#00E5FF]" />
          <span>{activeProject?.branch || 'main'}</span>
        </div>

        <div className="h-3 w-[1px] bg-[#21262D]" />

        {/* Selected file info */}
        {activeFile ? (
          <div className="flex items-center gap-2">
            <span className="text-[#E6EDF3]">{activeFile.path}</span>
            <span className="text-[#8B949E]">({activeFile.linesCount} lines · {activeFile.language})</span>
          </div>
        ) : (
          <span>No file selected</span>
        )}
      </div>

      <div className="flex items-center gap-4">
        {/* Toolchain */}
        <div className="hidden lg:flex items-center gap-1.5">
          <Cpu size={13} className="text-[#8B949E]" />
          <span>{(activeProject?.toolchain || 'GCC-Embedded').split(' ')[0]}</span>
        </div>

        <div className="h-3 w-[1px] bg-[#21262D] hidden lg:block" />

        {/* DO-178C Criticality */}
        <div className="flex items-center gap-1.5">
          <ShieldCheck size={13} className="text-emerald-400" />
          <span className="text-[#CBD5E1]">DO-178C {activeProject?.dalLevel || 'DAL-A'}</span>
        </div>

        <div className="h-3 w-[1px] bg-[#21262D]" />

        {/* Diagnostics count */}
        <div className="flex items-center gap-1">
          {unresolvedIssuesCount > 0 ? (
            <span className="text-rose-400 font-semibold">{unresolvedIssuesCount} Issues</span>
          ) : (
            <span className="text-emerald-400">0 Issues</span>
          )}
        </div>

        <div className="h-3 w-[1px] bg-[#21262D]" />

        {/* Engine mode */}
        <div className="flex items-center gap-1.5">
          <Radio size={12} className={isBackendConnected ? "text-emerald-400 animate-pulse" : "text-[#00E5FF]"} />
          <span className={isBackendConnected ? "text-emerald-400" : "text-[#CBD5E1]"}>
            {isBackendConnected ? 'FastAPI Engine' : 'Simulation Engine'}
          </span>
        </div>
      </div>
    </footer>
  );
};
