import React, { useState } from 'react';
import { 
  AlertOctagon, AlertTriangle, Info, CheckCircle2, 
  Search, Filter, ExternalLink, ArrowRight, FileCode, 
  Sparkles, Terminal, Copy, Check
} from 'lucide-react';
import type { Diagnostic, ProjectFile  } from '../../types';

interface IssuesViewProps {
  diagnostics: Diagnostic[];
  files: ProjectFile[];
  onNavigateToSource: (filePath: string, line: number) => void;
  onAskAiAboutDiagnostic: (diag: Diagnostic) => void;
}

export const IssuesView: React.FC<IssuesViewProps> = ({
  diagnostics,
  files,
  onNavigateToSource,
  onAskAiAboutDiagnostic,
}) => {
  const [selectedDiag, setSelectedDiag] = useState<Diagnostic>(diagnostics[0] || null);
  const [severityFilter, setSeverityFilter] = useState<'all' | 'error' | 'warning' | 'info'>('all');
  const [search, setSearch] = useState('');
  const [copiedTrace, setCopiedTrace] = useState(false);

  const filteredDiagnostics = diagnostics.filter((d) => {
    const matchesSearch = d.message.toLowerCase().includes(search.toLowerCase()) ||
                          d.filePath.toLowerCase().includes(search.toLowerCase()) ||
                          (d.testId && d.testId.toLowerCase().includes(search.toLowerCase()));
    if (!matchesSearch) return false;
    if (severityFilter !== 'all' && d.severity !== severityFilter) return false;
    return true;
  });

  const handleCopyTrace = (trace: string) => {
    navigator.clipboard.writeText(trace);
    setCopiedTrace(true);
    setTimeout(() => setCopiedTrace(false), 2000);
  };

  return (
    <div className="flex-1 flex overflow-hidden bg-[#0B0E14] text-[#E6EDF3]">
      {/* 1. DIAGNOSTICS TABLE / LIST (LEFT) */}
      <section className="w-1/2 border-r border-[#21262D] flex flex-col bg-[#0E131B]">
        {/* TOP FILTER BAR */}
        <div className="p-4 bg-[#161B22] border-b border-[#21262D] space-y-3 shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertOctagon size={16} className="text-rose-400" />
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                Issues & Verification Diagnostics
              </h2>
            </div>
            <span className="text-[10px] font-mono text-[#8B949E]">
              {diagnostics.length} Active Records
            </span>
          </div>

          <div className="relative">
            <Search size={13} className="absolute left-2.5 top-2.5 text-[#8B949E]" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter by message, file, or test ID..."
              className="w-full bg-[#0B0E14] border border-[#30363D] rounded-md pl-8 pr-3 py-1.5 text-xs text-[#E6EDF3] placeholder-[#8B949E] focus:outline-none focus:border-[#00E5FF]"
            />
          </div>

          {/* SEVERITY SEGMENT TABS */}
          <div className="flex items-center gap-1 p-0.5 bg-[#0B0E14] rounded-md border border-[#21262D]">
            <button
              onClick={() => setSeverityFilter('all')}
              className={`flex-1 py-1 text-[11px] font-medium rounded transition-colors ${
                severityFilter === 'all' ? 'bg-[#21262D] text-white' : 'text-[#8B949E]'
              }`}
            >
              All ({diagnostics.length})
            </button>
            <button
              onClick={() => setSeverityFilter('error')}
              className={`flex-1 py-1 text-[11px] font-medium rounded transition-colors ${
                severityFilter === 'error' ? 'bg-[#21262D] text-rose-400 font-bold' : 'text-[#8B949E]'
              }`}
            >
              Errors ({diagnostics.filter((d) => d.severity === 'error').length})
            </button>
            <button
              onClick={() => setSeverityFilter('warning')}
              className={`flex-1 py-1 text-[11px] font-medium rounded transition-colors ${
                severityFilter === 'warning' ? 'bg-[#21262D] text-amber-400 font-bold' : 'text-[#8B949E]'
              }`}
            >
              Warnings ({diagnostics.filter((d) => d.severity === 'warning').length})
            </button>
            <button
              onClick={() => setSeverityFilter('info')}
              className={`flex-1 py-1 text-[11px] font-medium rounded transition-colors ${
                severityFilter === 'info' ? 'bg-[#21262D] text-[#00E5FF]' : 'text-[#8B949E]'
              }`}
            >
              Info
            </button>
          </div>
        </div>

        {/* LIST */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {filteredDiagnostics.map((diag) => {
            const isSelected = selectedDiag?.id === diag.id;
            return (
              <div
                key={diag.id}
                onClick={() => setSelectedDiag(diag)}
                className={`p-3.5 rounded-lg border cursor-pointer transition-all ${
                  isSelected
                    ? 'bg-[#161B22] border-[#00E5FF]/60 shadow-md'
                    : 'bg-[#0B0E14] border-[#21262D] hover:border-[#30363D]'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-[9px] font-mono font-bold px-1.5 py-0.2 rounded uppercase ${
                        diag.severity === 'error' ? 'bg-rose-950/60 text-rose-300 border border-rose-800' :
                        diag.severity === 'warning' ? 'bg-amber-950/60 text-amber-300 border border-amber-800' :
                        'bg-cyan-950/60 text-cyan-300 border border-cyan-800'
                      }`}
                    >
                      {diag.severity}
                    </span>
                    <span className="text-[10px] font-mono text-[#8B949E] uppercase">
                      {diag.category.replace('_', ' ')}
                    </span>
                  </div>

                  <span className="text-[10px] font-mono text-[#8B949E]">
                    {diag.timestamp.split(' ')[1]}
                  </span>
                </div>

                <div className="text-xs font-semibold text-white leading-snug">
                  {diag.message}
                </div>

                <div className="mt-2 pt-2 border-t border-[#21262D] flex items-center justify-between text-[11px] font-mono text-[#8B949E]">
                  <span className="text-[#00E5FF] truncate max-w-[200px]">
                    {diag.filePath}:{diag.line}
                  </span>
                  {diag.testId && <span>{diag.testId}</span>}
                </div>
              </div>
            );
          })}

          {filteredDiagnostics.length === 0 && (
            <div className="text-center py-12 text-[#8B949E] text-xs">
              No diagnostics found matching filter.
            </div>
          )}
        </div>
      </section>

      {/* 2. DIAGNOSTIC EVIDENCE & RAW TRACE INSPECTOR (RIGHT) */}
      <section className="flex-1 flex flex-col overflow-y-auto p-6 space-y-5 bg-[#0B0E14]">
        {selectedDiag ? (
          <>
            {/* EVIDENCE DETAIL CARD */}
            <div className="p-5 rounded-xl bg-[#161B22] border border-[#21262D] space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#21262D]">
                <div>
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded uppercase ${
                      selectedDiag.severity === 'error' ? 'bg-rose-950/60 text-rose-300 border border-rose-800' :
                      'bg-amber-950/60 text-amber-300 border border-amber-800'
                    }`}>
                      {selectedDiag.severity}
                    </span>
                    <span className="text-xs font-mono text-white">
                      {selectedDiag.category.toUpperCase()}
                    </span>
                  </div>
                  <h1 className="text-base font-bold text-white mt-2">
                    {selectedDiag.message}
                  </h1>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => onNavigateToSource(selectedDiag.filePath, selectedDiag.line)}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-[#00E5FF] hover:bg-cyan-300 text-black text-xs font-bold transition-all shadow-[0_0_12px_rgba(0,229,255,0.25)]"
                  >
                    <FileCode size={13} />
                    <span>Jump to Source Line {selectedDiag.line}</span>
                  </button>
                </div>
              </div>

              {/* METADATA GRID */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-2.5 rounded-lg bg-[#0B0E14] border border-[#21262D]">
                  <span className="text-[9px] font-mono text-[#8B949E] uppercase block">File Path</span>
                  <span className="text-white font-mono text-xs mt-0.5 block truncate">{selectedDiag.filePath}</span>
                </div>
                <div className="p-2.5 rounded-lg bg-[#0B0E14] border border-[#21262D]">
                  <span className="text-[9px] font-mono text-[#8B949E] uppercase block">Source Coordinate</span>
                  <span className="text-[#00E5FF] font-mono text-xs mt-0.5 block">Line {selectedDiag.line} : Col {selectedDiag.column || 1}</span>
                </div>
                <div className="p-2.5 rounded-lg bg-[#0B0E14] border border-[#21262D]">
                  <span className="text-[9px] font-mono text-[#8B949E] uppercase block">Function Scope</span>
                  <span className="text-white font-mono text-xs mt-0.5 block">{selectedDiag.functionName || 'Global'}()</span>
                </div>
                <div className="p-2.5 rounded-lg bg-[#0B0E14] border border-[#21262D]">
                  <span className="text-[9px] font-mono text-[#8B949E] uppercase block">Linked Req</span>
                  <span className="text-white font-mono text-xs mt-0.5 block">{selectedDiag.requirementId || 'N/A'}</span>
                </div>
              </div>
            </div>

            {/* RAW EVIDENCE STACK TRACE */}
            <div className="rounded-xl bg-[#161B22] border border-[#21262D] p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Terminal size={15} className="text-[#00E5FF]" />
                  <span className="text-xs font-bold text-white uppercase tracking-wider">
                    Raw Compiler & Execution Trace
                  </span>
                </div>

                <button
                  onClick={() => handleCopyTrace(selectedDiag.rawTrace)}
                  className="flex items-center gap-1 text-[11px] font-mono text-[#8B949E] hover:text-white"
                >
                  {copiedTrace ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                  <span>{copiedTrace ? 'Copied' : 'Copy Trace'}</span>
                </button>
              </div>

              <div className="p-4 rounded-lg bg-[#070A0F] border border-[#21262D] font-mono text-xs text-[#CBD5E1] whitespace-pre-wrap leading-relaxed overflow-x-auto">
                {selectedDiag.rawTrace}
              </div>
            </div>

            {/* AI DIAGNOSTIC REMEDIATION ACTION */}
            <div className="rounded-xl bg-gradient-to-r from-cyan-950/30 to-[#161B22] border border-[#00E5FF]/30 p-4 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2 text-xs font-bold text-[#00E5FF]">
                  <Sparkles size={14} />
                  <span>Sentinel AI Remediation Assistant</span>
                </div>
                <p className="text-[11px] text-[#8B949E] mt-0.5">
                  Request an automated fix suggestion based on MISRA C:2012 guidelines and zero-divide guard clauses.
                </p>
              </div>

              <button
                onClick={() => onAskAiAboutDiagnostic(selectedDiag)}
                className="px-3.5 py-1.5 rounded-lg bg-[#00E5FF] hover:bg-cyan-300 text-black text-xs font-bold transition-all shrink-0"
              >
                Analyze with AI
              </button>
            </div>
          </>
        ) : (
          <div className="flex items-center justify-center h-full text-xs text-[#8B949E]">
            Select a diagnostic record from the left table to inspect raw trace and location.
          </div>
        )}
      </section>
    </div>
  );
};
