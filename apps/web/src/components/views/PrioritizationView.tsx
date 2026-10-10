import React, { useState, useMemo } from 'react';
import { 
  ArrowUpDown, Filter, Play, CheckCircle2, AlertCircle, 
  HelpCircle, Sparkles, Binary, CheckSquare, Square, 
  FileCode, ChevronRight, Layers, ArrowRight, Info
} from 'lucide-react';
import type { ProjectFile  } from '../../types';

interface PrioritizationViewProps {
  files: ProjectFile[];
  onSelectFile: (file: ProjectFile) => void;
  onRunSelectedQueue: (fileIds: string[]) => void;
  onNavigateTab: (tab: any) => void;
}

export const PrioritizationView: React.FC<PrioritizationViewProps> = ({
  files,
  onSelectFile,
  onRunSelectedQueue,
  onNavigateTab,
}) => {
  const [selectedFileIds, setSelectedFileIds] = useState<string[]>(files.map((f) => f.id));
  const [filterDeterminism, setFilterDeterminism] = useState<'all' | 'deterministic' | 'hybrid' | 'ai_heuristic'>('all');
  const [sortBy, setSortBy] = useState<'score' | 'criticality' | 'complexity' | 'coverage'>('score');
  const [sortDirection, setSortDirection] = useState<'desc' | 'asc'>('desc');
  const [inspectedFile, setInspectedFile] = useState<ProjectFile>(files[0]);

  // Toggle selection
  const toggleSelectAll = () => {
    if (selectedFileIds.length === files.length) {
      setSelectedFileIds([]);
    } else {
      setSelectedFileIds(files.map((f) => f.id));
    }
  };

  const toggleSelectOne = (id: string) => {
    if (selectedFileIds.includes(id)) {
      setSelectedFileIds(selectedFileIds.filter((i) => i !== id));
    } else {
      setSelectedFileIds([...selectedFileIds, id]);
    }
  };

  // Filter & sort files
  const processedFiles = useMemo(() => {
    let list = [...files];
    if (filterDeterminism !== 'all') {
      list = list.filter((f) => f.priorityRationale.determinismType === filterDeterminism);
    }

    list.sort((a, b) => {
      let diff = 0;
      if (sortBy === 'score') diff = b.priorityScore - a.priorityScore;
      if (sortBy === 'complexity') diff = b.cyclomaticComplexity - a.cyclomaticComplexity;
      if (sortBy === 'coverage') diff = a.coveragePercent - b.coveragePercent;
      return sortDirection === 'desc' ? diff : -diff;
    });

    return list;
  }, [files, filterDeterminism, sortBy, sortDirection]);

  return (
    <div className="flex-1 flex overflow-hidden bg-[#0B0E14] text-[#E6EDF3]">
      {/* LEFT: PRIORITIZATION QUEUE TABLE */}
      <section className="flex-1 flex flex-col overflow-hidden border-r border-[#21262D]">
        {/* HEADER CONTROLS */}
        <div className="p-4 bg-[#161B22] border-b border-[#21262D] space-y-3 shrink-0">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white font-heading">Intelligent Verification Priority Queue</h2>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#00E5FF]/10 text-[#00E5FF] border border-[#00E5FF]/20">
                  Explainable DO-178C Scoring
                </span>
              </div>
              <p className="text-xs text-[#8B949E] mt-0.5">
                Ranks source files by safety envelope criticality, branch coverage gaps, and cyclomatic risk.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => onRunSelectedQueue(selectedFileIds)}
                disabled={selectedFileIds.length === 0}
                className="btn-aerospace-glow btn-shimmer flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-[#00E5FF] hover:bg-cyan-300 disabled:opacity-50 text-black text-xs font-bold transition-all shadow-[0_0_12px_rgba(0,229,255,0.25)] cursor-pointer"
              >
                <Play size={13} fill="currentColor" />
                <span>Verify Selected ({selectedFileIds.length})</span>
              </button>
            </div>
          </div>

          {/* FILTER & SORT TOOLBAR */}
          <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-[#21262D]">
            <div className="flex items-center gap-1">
              <span className="text-[10px] font-mono text-[#8B949E] uppercase mr-1">Source Model:</span>
              <button
                onClick={() => setFilterDeterminism('all')}
                className={`px-2 py-1 text-[11px] font-medium rounded transition-colors ${
                  filterDeterminism === 'all' ? 'bg-[#21262D] text-[#00E5FF]' : 'text-[#8B949E] hover:text-white'
                }`}
              >
                All Models
              </button>
              <button
                onClick={() => setFilterDeterminism('deterministic')}
                className={`px-2 py-1 text-[11px] font-medium rounded transition-colors ${
                  filterDeterminism === 'deterministic' ? 'bg-[#21262D] text-[#00E5FF]' : 'text-[#8B949E] hover:text-white'
                }`}
              >
                Deterministic Static (AST)
              </button>
              <button
                onClick={() => setFilterDeterminism('hybrid')}
                className={`px-2 py-1 text-[11px] font-medium rounded transition-colors ${
                  filterDeterminism === 'hybrid' ? 'bg-[#21262D] text-[#00E5FF]' : 'text-[#8B949E] hover:text-white'
                }`}
              >
                Hybrid Verification
              </button>
              <button
                onClick={() => setFilterDeterminism('ai_heuristic')}
                className={`px-2 py-1 text-[11px] font-medium rounded transition-colors ${
                  filterDeterminism === 'ai_heuristic' ? 'bg-[#21262D] text-[#00E5FF]' : 'text-[#8B949E] hover:text-white'
                }`}
              >
                AI Heuristic
              </button>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono text-[#8B949E] uppercase">Sort by:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="bg-[#0B0E14] border border-[#30363D] rounded px-2 py-1 text-xs text-[#E6EDF3] focus:outline-none"
              >
                <option value="score">Priority Risk Score</option>
                <option value="complexity">Cyclomatic Complexity</option>
                <option value="coverage">Coverage (Lowest First)</option>
              </select>
              <button
                onClick={() => setSortDirection(sortDirection === 'desc' ? 'asc' : 'desc')}
                className="p-1 rounded bg-[#0B0E14] border border-[#30363D] text-[#8B949E] hover:text-white"
                title="Toggle sort direction"
              >
                <ArrowUpDown size={13} />
              </button>
            </div>
          </div>
        </div>

        {/* QUEUE LIST */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {/* Table Header */}
          <div className="flex items-center px-3 py-1.5 text-[10px] font-mono uppercase text-[#8B949E] border-b border-[#21262D]">
            <button onClick={toggleSelectAll} className="mr-3">
              {selectedFileIds.length === files.length ? (
                <CheckSquare size={14} className="text-[#00E5FF]" />
              ) : (
                <Square size={14} className="text-[#8B949E]" />
              )}
            </button>
            <span className="w-12">Rank</span>
            <span className="w-20">Score</span>
            <span className="flex-1">Source Module</span>
            <span className="w-20 text-center">DAL Level</span>
            <span className="w-20 text-right">Complexity</span>
            <span className="w-24 text-right">Coverage</span>
            <span className="w-20 text-center">State</span>
          </div>

          {processedFiles.map((file, idx) => {
            const isSelected = selectedFileIds.includes(file.id);
            const isInspected = inspectedFile.id === file.id;

            return (
              <div
                key={file.id}
                onClick={() => setInspectedFile(file)}
                className={`flex items-center px-3 py-3 rounded-lg border cursor-pointer transition-all ${
                  isInspected
                    ? 'bg-[#161B22] border-[#00E5FF]/60 shadow-md'
                    : 'bg-[#0E131B] border-[#21262D] hover:border-[#30363D]'
                }`}
              >
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleSelectOne(file.id);
                  }}
                  className="mr-3"
                >
                  {isSelected ? (
                    <CheckSquare size={14} className="text-[#00E5FF]" />
                  ) : (
                    <Square size={14} className="text-[#8B949E]" />
                  )}
                </button>

                {/* Rank */}
                <span className="w-12 font-mono text-xs font-bold text-[#8B949E]">
                  #{idx + 1}
                </span>

                {/* Score badge */}
                <div className="w-20">
                  <span className={`text-xs font-mono font-bold px-1.5 py-0.5 rounded ${
                    file.priorityScore >= 0.9 ? 'bg-rose-950/60 text-rose-300 border border-rose-800' :
                    file.priorityScore >= 0.8 ? 'bg-amber-950/60 text-amber-300 border border-amber-800' :
                    'bg-cyan-950/60 text-cyan-300 border border-cyan-800'
                  }`}>
                    {file.priorityScore.toFixed(2)}
                  </span>
                </div>

                {/* File info */}
                <div className="flex-1 min-w-0 pr-3">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-semibold text-white truncate font-mono">
                      {file.name}
                    </span>
                    <span className="text-[10px] text-[#8B949E] font-mono truncate hidden sm:inline">
                      ({file.path})
                    </span>
                  </div>
                  <div className="text-[11px] text-[#8B949E] truncate mt-0.5">
                    {file.priorityRationale.summary}
                  </div>
                </div>

                {/* DAL Criticality */}
                <div className="w-20 text-center">
                  <span className="text-[10px] font-mono font-bold text-white px-1.5 py-0.5 bg-[#0B0E14] border border-[#21262D] rounded">
                    {file.criticality}
                  </span>
                </div>

                {/* Complexity */}
                <div className="w-20 text-right font-mono text-xs text-[#CBD5E1]">
                  M={file.cyclomaticComplexity}
                </div>

                {/* Coverage */}
                <div className="w-24 text-right font-mono text-xs">
                  <span className={file.coveragePercent < 80 ? 'text-amber-400 font-semibold' : 'text-emerald-400'}>
                    {file.coveragePercent}%
                  </span>
                </div>

                {/* State */}
                <div className="w-20 text-center">
                  <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded uppercase font-semibold ${
                    file.status === 'passed' ? 'text-emerald-400 bg-emerald-950/40' :
                    file.status === 'failed' ? 'text-rose-400 bg-rose-950/40' :
                    'text-[#8B949E] bg-[#161B22]'
                  }`}>
                    {file.status}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* NOTICE OF NON-CERTIFIED HEURISTICS */}
        <div className="p-2.5 bg-[#0B0E14] border-t border-[#21262D] text-[10px] text-[#8B949E] flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <Info size={13} className="text-[#8B949E]" />
            <span>
              Heuristic priority scores assist verification ordering and are not certified aerospace safety metrics.
            </span>
          </div>
          <span className="font-mono text-[#00E5FF]">DO-178C Tool Qualification Compliant</span>
        </div>
      </section>

      {/* RIGHT: EXPLAINABLE RATIONALE INSPECTOR */}
      <section className="w-96 bg-[#0E131B] p-5 flex flex-col justify-between overflow-y-auto">
        <div className="space-y-5">
          <div>
            <span className="text-[10px] font-mono uppercase text-[#00E5FF] tracking-wider font-semibold block">
              Explainable Decision Rationale
            </span>
            <h3 className="text-sm font-bold text-white mt-1">
              {inspectedFile.name}
            </h3>
            <span className="text-[11px] font-mono text-[#8B949E] block">
              {inspectedFile.path}
            </span>
          </div>

          {/* SCORING BREAKDOWN CARD */}
          <div className="p-4 rounded-xl bg-[#161B22] border border-[#21262D] space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-[#8B949E]">Calculated Risk Score</span>
              <span className="text-lg font-bold font-mono text-[#00E5FF]">
                {inspectedFile.priorityScore.toFixed(2)} / 1.00
              </span>
            </div>

            {/* Score Bar */}
            <div className="w-full bg-[#0B0E14] h-2 rounded-full overflow-hidden border border-[#21262D]">
              <div
                className="h-full bg-gradient-to-r from-cyan-500 to-rose-500"
                style={{ width: `${inspectedFile.priorityScore * 100}%` }}
              />
            </div>

            <div className="flex items-center justify-between text-[11px] pt-1">
              <span className="text-[#8B949E]">Scoring Method:</span>
              <span className="font-mono font-semibold text-white uppercase text-[10px] px-1.5 py-0.5 rounded bg-[#0B0E14] border border-[#21262D]">
                {inspectedFile.priorityRationale.determinismType.replace('_', ' ')}
              </span>
            </div>
          </div>

          {/* WHY RANKED HERE */}
          <div className="space-y-2">
            <span className="text-xs font-semibold text-white block">
              Ranking Contributing Factors
            </span>
            <div className="space-y-2">
              {inspectedFile.priorityRationale.factors.map((factor, i) => (
                <div
                  key={i}
                  className="p-2.5 rounded-lg bg-[#161B22] border border-[#21262D] text-xs text-[#CBD5E1] flex items-start gap-2"
                >
                  <span className="text-[#00E5FF] font-mono text-[10px] mt-0.5">•</span>
                  <span>{factor}</span>
                </div>
              ))}
            </div>
          </div>

          {/* CODE ATTRIBUTES */}
          <div className="p-4 rounded-xl bg-[#161B22] border border-[#21262D] space-y-2 text-xs">
            <span className="text-[10px] font-mono text-[#8B949E] uppercase block mb-1">
              Static Code Telemetry
            </span>
            <div className="flex justify-between py-1 border-b border-[#21262D]">
              <span className="text-[#8B949E]">Criticality Level</span>
              <span className="font-mono font-bold text-white">{inspectedFile.criticality}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#21262D]">
              <span className="text-[#8B949E]">McCabe Cyclomatic Index</span>
              <span className="font-mono font-bold text-white">{inspectedFile.cyclomaticComplexity}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#21262D]">
              <span className="text-[#8B949E]">Source Lines</span>
              <span className="font-mono font-bold text-white">{inspectedFile.linesCount}</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-[#8B949E]">Branch Coverage</span>
              <span className="font-mono font-bold text-white">{inspectedFile.coveragePercent}%</span>
            </div>
          </div>
        </div>

        {/* ACTION BUTTON */}
        <div className="pt-4 border-t border-[#21262D] flex flex-col gap-2">
          <button
            onClick={() => {
              onSelectFile(inspectedFile);
              onNavigateTab('explorer');
            }}
            className="w-full py-2 rounded-lg bg-[#21262D] hover:bg-[#30363D] text-xs font-semibold text-white flex items-center justify-center gap-2 transition-colors"
          >
            <FileCode size={13} className="text-[#00E5FF]" />
            <span>Open in Source Editor</span>
          </button>
        </div>
      </section>
    </div>
  );
};
