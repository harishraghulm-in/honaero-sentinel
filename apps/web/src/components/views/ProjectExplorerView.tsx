import React, { useState, useMemo } from 'react';
import { 
  FileCode, Folder, ChevronRight, ChevronDown, Search, 
  Filter, Play, AlertCircle, CheckCircle2, Shield, Eye, 
  Edit3, Copy, Check, Hash, CornerDownRight, Sparkles
} from 'lucide-react';
import type { ProjectFile  } from '../../types';

interface ProjectExplorerViewProps {
  files: ProjectFile[];
  selectedFile?: ProjectFile;
  onSelectFile: (file: ProjectFile) => void;
  activeLine?: number;
  highlightedFunction?: string;
  onRunFileVerification: (file: ProjectFile) => void;
  onOpenAiForFile?: (file: ProjectFile) => void;
}

export const ProjectExplorerView: React.FC<ProjectExplorerViewProps> = ({
  files,
  selectedFile,
  onSelectFile,
  activeLine,
  highlightedFunction,
  onRunFileVerification,
  onOpenAiForFile,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<'all' | 'c' | 'headers' | 'failed'>('all');
  const [editorSearch, setEditorSearch] = useState('');
  const [isEditable, setIsEditable] = useState(false);
  const [fileContent, setFileContent] = useState<Record<string, string>>({});
  const [copied, setCopied] = useState(false);
  const [collapsedFolders, setCollapsedFolders] = useState<Record<string, boolean>>({});

  // Current file text
  const currentText = selectedFile ? (fileContent[selectedFile.id] ?? selectedFile.content ?? '') : '';

  const handleTextChange = (newVal: string) => {
    if (selectedFile) {
      setFileContent((prev) => ({ ...prev, [selectedFile.id]: newVal }));
    }
  };

  const handleCopyCode = () => {
    navigator.clipboard.writeText(currentText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Group files by directory
  const filteredFiles = useMemo(() => {
    return files.filter((f) => {
      const matchesSearch = f.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                            f.path.toLowerCase().includes(searchQuery.toLowerCase());
      if (!matchesSearch) return false;
      if (filterType === 'c') return f.language === 'C' || f.language === 'C++';
      if (filterType === 'headers') return f.language === 'Header';
      if (filterType === 'failed') return f.status === 'failed';
      return true;
    });
  }, [files, searchQuery, filterType]);

  const directoryTree = useMemo(() => {
    const tree: Record<string, ProjectFile[]> = {};
    filteredFiles.forEach((file) => {
      const dir = file.directory || 'root';
      if (!tree[dir]) tree[dir] = [];
      tree[dir].push(file);
    });
    return tree;
  }, [filteredFiles]);

  const toggleFolder = (dir: string) => {
    setCollapsedFolders((prev) => ({ ...prev, [dir]: !prev[dir] }));
  };

  // Split lines for line numbers
  const lines = currentText.split('\n');

  // Simple syntax colorizer for C tokens
  const renderCodeLine = (line: string, lineIndex: number) => {
    const lineNumber = lineIndex + 1;
    const isTargetLine = activeLine === lineNumber;

    return (
      <div
        key={lineIndex}
        className={`flex group hover:bg-[#161B22]/80 font-mono text-[13px] leading-6 px-4 transition-colors ${
          isTargetLine 
            ? 'bg-cyan-950/40 border-l-2 border-[#00E5FF] text-white shadow-[inset_0_0_15px_rgba(0,229,255,0.15)]' 
            : ''
        }`}
      >
        {/* Line Number */}
        <span
          className={`w-10 shrink-0 text-right pr-4 select-none ${
            isTargetLine ? 'text-[#00E5FF] font-bold' : 'text-[#484F58]'
          }`}
        >
          {lineNumber}
        </span>

        {/* Code Content */}
        <span className="whitespace-pre overflow-x-auto flex-1 text-[#CBD5E1]">
          {highlightSyntax(line)}
        </span>
      </div>
    );
  };

  // Fast keyword syntax colorizer
  const highlightSyntax = (raw: string) => {
    if (raw.trim().startsWith('//') || raw.trim().startsWith('/*') || raw.trim().startsWith('*')) {
      return <span className="text-[#6E7681] italic">{raw}</span>;
    }
    if (raw.trim().startsWith('#include') || raw.trim().startsWith('#define') || raw.trim().startsWith('#ifndef') || raw.trim().startsWith('#endif')) {
      return <span className="text-[#FF7B72]">{raw}</span>;
    }

    // Split words
    const parts = raw.split(/(\b(?:float|int|uint16_t|uint32_t|uint8_t|bool|void|return|if|else|static|const|struct|typedef)\b)/g);
    return parts.map((part, i) => {
      if (/^(float|int|uint16_t|uint32_t|uint8_t|bool|void|static|const|struct|typedef)$/.test(part)) {
        return <span key={i} className="text-[#79C0FF] font-semibold">{part}</span>;
      }
      if (/^(return|if|else)$/.test(part)) {
        return <span key={i} className="text-[#FF7B72] font-semibold">{part}</span>;
      }
      if (part.includes('(') && !part.startsWith('/*')) {
        return <span key={i} className="text-[#D2A8FF]">{part}</span>;
      }
      return <span key={i}>{part}</span>;
    });
  };

  return (
    <div className="flex-1 flex overflow-hidden bg-[#0B0E14]">
      {/* 1. PROJECT EXPLORER TREE (LEFT PANEL) */}
      <section className="w-80 bg-[#0E131B] border-r border-[#21262D] flex flex-col shrink-0 select-none">
        {/* TOP SEARCH & FILTER BAR */}
        <div className="p-3 border-b border-[#21262D] space-y-2 bg-[#161B22]/40">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono tracking-wider uppercase text-[#8B949E] font-semibold">
              Project Explorer
            </span>
            <span className="text-[10px] font-mono text-[#00E5FF]">
              {filteredFiles.length} files
            </span>
          </div>

          <div className="relative">
            <Search size={13} className="absolute left-2.5 top-2.5 text-[#8B949E]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search source & headers..."
              className="w-full bg-[#0B0E14] border border-[#30363D] rounded-md pl-8 pr-3 py-1.5 text-xs text-[#E6EDF3] placeholder-[#8B949E] focus:outline-none focus:border-[#00E5FF]"
            />
          </div>

          {/* FILTER SEGMENTS */}
          <div className="flex items-center gap-1 p-0.5 bg-[#0B0E14] rounded-md border border-[#21262D]">
            <button
              onClick={() => setFilterType('all')}
              className={`flex-1 py-1 text-[10px] font-medium rounded transition-colors ${
                filterType === 'all' ? 'bg-[#21262D] text-[#E6EDF3]' : 'text-[#8B949E] hover:text-[#E6EDF3]'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setFilterType('c')}
              className={`flex-1 py-1 text-[10px] font-medium rounded transition-colors ${
                filterType === 'c' ? 'bg-[#21262D] text-[#00E5FF]' : 'text-[#8B949E] hover:text-[#E6EDF3]'
              }`}
            >
              C Sources
            </button>
            <button
              onClick={() => setFilterType('headers')}
              className={`flex-1 py-1 text-[10px] font-medium rounded transition-colors ${
                filterType === 'headers' ? 'bg-[#21262D] text-[#E6EDF3]' : 'text-[#8B949E] hover:text-[#E6EDF3]'
              }`}
            >
              Headers
            </button>
            <button
              onClick={() => setFilterType('failed')}
              className={`flex-1 py-1 text-[10px] font-medium rounded transition-colors ${
                filterType === 'failed' ? 'bg-[#21262D] text-rose-400 font-bold' : 'text-[#8B949E] hover:text-[#E6EDF3]'
              }`}
            >
              Issues
            </button>
          </div>
        </div>

        {/* NESTED DIRECTORY TREE */}
        <div className="flex-1 overflow-y-auto p-2 space-y-2">
          {Object.entries(directoryTree).map(([dirName, dirFiles]) => {
            const isCollapsed = collapsedFolders[dirName];
            return (
              <div key={dirName} className="space-y-0.5">
                <button
                  onClick={() => toggleFolder(dirName)}
                  className="w-full flex items-center gap-1.5 px-2 py-1 text-xs font-semibold text-[#8B949E] hover:text-white rounded hover:bg-[#161B22] transition-colors"
                >
                  {isCollapsed ? <ChevronRight size={13} /> : <ChevronDown size={13} />}
                  <Folder size={14} className="text-[#00E5FF]/70" />
                  <span className="font-mono text-[11px] truncate">{dirName}</span>
                  <span className="ml-auto text-[10px] font-mono text-[#8B949E]">
                    {dirFiles.length}
                  </span>
                </button>

                {!isCollapsed && (
                  <div className="pl-4 space-y-0.5">
                    {dirFiles.map((file) => {
                      const isSelected = selectedFile?.id === file.id;
                      return (
                        <div
                          key={file.id}
                          onClick={() => onSelectFile(file)}
                          className={`group flex items-center justify-between px-2.5 py-1.5 rounded-md cursor-pointer text-xs transition-all ${
                            isSelected
                              ? 'bg-[#161B22] border border-[#30363D] text-[#00E5FF]'
                              : 'text-[#CBD5E1] hover:bg-[#161B22]/50 hover:text-white'
                          }`}
                        >
                          <div className="flex items-center gap-2 truncate">
                            <FileCode
                              size={14}
                              className={
                                file.status === 'failed'
                                  ? 'text-rose-400'
                                  : file.status === 'passed'
                                  ? 'text-emerald-400'
                                  : 'text-[#00E5FF]'
                              }
                            />
                            <span className="font-mono text-[11px] truncate">{file.name}</span>
                          </div>

                          <div className="flex items-center gap-1.5 shrink-0">
                            {file.status === 'passed' && (
                              <CheckCircle2 size={12} className="text-emerald-400" />
                            )}
                            {file.status === 'failed' && (
                              <AlertCircle size={12} className="text-rose-400" />
                            )}
                            <span className="text-[9px] font-mono text-[#8B949E] px-1 bg-[#0B0E14] rounded">
                              {file.criticality}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}

          {filteredFiles.length === 0 && (
            <div className="p-4 text-center text-xs text-[#8B949E]">
              No files match filter.
            </div>
          )}
        </div>

        {/* BOTTOM QUICK FILE RISK SUMMARY */}
        {selectedFile && (
          <div className="p-3 border-t border-[#21262D] bg-[#161B22]/70">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] font-mono text-[#8B949E] uppercase">Selected Module</span>
              <span className={`text-[10px] font-mono px-1 rounded ${
                selectedFile.status === 'failed' ? 'text-rose-400 bg-rose-950/40' : 'text-emerald-400 bg-emerald-950/40'
              }`}>
                {selectedFile.status.toUpperCase()}
              </span>
            </div>
            <div className="text-xs font-semibold text-white truncate">{selectedFile.name}</div>
            <div className="text-[11px] text-[#8B949E] mt-1 flex items-center justify-between">
              <span>Priority: <strong className="text-[#00E5FF] font-mono">{selectedFile.priorityScore}</strong></span>
              <span>Coverage: <strong className="text-white font-mono">{selectedFile.coveragePercent}%</strong></span>
            </div>
          </div>
        )}
      </section>

      {/* 2. MAIN SOURCE CODE EDITOR */}
      <section className="flex-1 flex flex-col bg-[#0B0E14] overflow-hidden">
        {/* EDITOR TAB HEADER */}
        <div className="h-10 bg-[#161B22] border-b border-[#21262D] px-4 flex items-center justify-between select-none shrink-0">
          <div className="flex items-center gap-3">
            {selectedFile ? (
              <>
                <div className="flex items-center gap-2 px-2.5 py-1 bg-[#0B0E14] border border-[#30363D] rounded text-xs text-[#E6EDF3]">
                  <FileCode size={13} className="text-[#00E5FF]" />
                  <span className="font-mono text-[11px] font-semibold">{selectedFile.name}</span>
                  <span className="text-[10px] text-[#8B949E]">({selectedFile.linesCount} lines)</span>
                </div>
                <span className="text-xs text-[#8B949E] font-mono hidden md:inline">
                  {selectedFile.path}
                </span>
              </>
            ) : (
              <span className="text-xs text-[#8B949E] font-mono">No module selected</span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* Copy Button */}
            <button
              onClick={handleCopyCode}
              className="p-1.5 text-[#8B949E] hover:text-white rounded hover:bg-[#21262D] transition-colors"
              title="Copy source code"
            >
              {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
            </button>

            {/* Read-Only Safety Switch */}
            <button
              onClick={() => setIsEditable(!isEditable)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono transition-colors ${
                isEditable 
                  ? 'bg-amber-400/20 text-amber-300 border border-amber-400/30' 
                  : 'bg-[#21262D] text-[#8B949E] hover:text-white'
              }`}
            >
              {isEditable ? <Edit3 size={12} /> : <Eye size={12} />}
              <span>{isEditable ? 'Editing Mode' : 'Read-Only (DO-178C)'}</span>
            </button>

            {/* Run verification on this single file */}
            <button
              disabled={!selectedFile}
              onClick={() => selectedFile && onRunFileVerification(selectedFile)}
              className="flex items-center gap-1.5 px-3 py-1 bg-[#00E5FF] hover:bg-cyan-300 disabled:opacity-50 disabled:cursor-not-allowed text-black text-xs font-bold rounded transition-colors shadow-sm"
            >
              <Play size={12} fill="currentColor" />
              <span>Verify File</span>
            </button>
          </div>
        </div>

        {/* ACTIVE LINE NOTIFICATION (IF EXECUTION FOCUSED) */}
        {activeLine && (
          <div className="bg-cyan-950/60 border-b border-[#00E5FF]/40 px-4 py-1.5 flex items-center justify-between text-xs text-[#00E5FF]">
            <div className="flex items-center gap-2">
              <CornerDownRight size={14} className="animate-pulse" />
              <span>
                Active Execution Focus: Line <strong>{activeLine}</strong>
                {highlightedFunction && ` in function ${highlightedFunction}()`}
              </span>
            </div>
            <span className="text-[10px] font-mono text-[#8B949E]">
              Event Sync: Verified Target
            </span>
          </div>
        )}

        {/* SOURCE CODE VIEWPORT */}
        <div className="flex-1 overflow-auto py-3 bg-[#0B0E14]">
          {isEditable ? (
            <textarea
              value={currentText}
              onChange={(e) => handleTextChange(e.target.value)}
              className="w-full h-full bg-transparent text-[#E6EDF3] font-mono text-[13px] leading-6 p-4 focus:outline-none resize-none"
              spellCheck={false}
            />
          ) : (
            <div>
              {lines.map((line, idx) => renderCodeLine(line, idx))}
            </div>
          )}
        </div>

        {/* BOTTOM METRIC STRIP FOR SOURCE EDITOR */}
        <div className="h-8 bg-[#161B22] border-t border-[#21262D] px-4 flex items-center justify-between text-[11px] font-mono text-[#8B949E] select-none">
          <div className="flex items-center gap-4">
            {selectedFile ? (
              <>
                <span>Criticality: <strong className="text-white">{selectedFile.criticality}</strong></span>
                <span>Complexity: <strong className="text-white">M={selectedFile.cyclomaticComplexity}</strong></span>
                <span>Coverage: <strong className={selectedFile.coveragePercent < 80 ? "text-amber-400" : "text-emerald-400"}>{selectedFile.coveragePercent}%</strong></span>
              </>
            ) : (
              <span>No module selected</span>
            )}
          </div>
          <div className="flex items-center gap-3">
            {onOpenAiForFile && selectedFile && (
              <button
                onClick={() => onOpenAiForFile(selectedFile)}
                className="text-[#00E5FF] hover:underline flex items-center gap-1"
              >
                <Sparkles size={12} />
                <span>Ask Sentinel AI about this code</span>
              </button>
            )}
          </div>
        </div>
      </section>
    </div>
  );
};
