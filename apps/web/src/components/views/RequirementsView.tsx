import React, { useState } from 'react';
import { 
  FileText, Search, Plus, Sparkles, CheckCircle2, 
  AlertCircle, ArrowRight, ExternalLink, ShieldCheck, 
  Layers, Upload, FileUp, Check, Filter
} from 'lucide-react';
import type { Requirement, ProjectFile, TestCase  } from '../../types';

interface RequirementsViewProps {
  requirements: Requirement[];
  files: ProjectFile[];
  testCases: TestCase[];
  onOpenUploadDoc: () => void;
  onProposeTestFromReq: (req: Requirement) => void;
  onSelectFile: (file: ProjectFile) => void;
  onNavigateTab: (tab: any) => void;
}

export const RequirementsView: React.FC<RequirementsViewProps> = ({
  requirements,
  files,
  testCases,
  onOpenUploadDoc,
  onProposeTestFromReq,
  onSelectFile,
  onNavigateTab,
}) => {
  const [selectedReq, setSelectedReq] = useState<Requirement>(requirements[0]);
  const [search, setSearch] = useState('');
  const [filterCoverage, setFilterCoverage] = useState<'all' | 'fully' | 'partial' | 'uncovered'>('all');

  const filteredRequirements = requirements.filter((r) => {
    const matchesSearch = r.id.toLowerCase().includes(search.toLowerCase()) ||
                          r.title.toLowerCase().includes(search.toLowerCase()) ||
                          r.description.toLowerCase().includes(search.toLowerCase());
    if (!matchesSearch) return false;
    if (filterCoverage === 'fully') return r.coverageStatus === 'Fully Covered';
    if (filterCoverage === 'partial') return r.coverageStatus === 'Partially Covered';
    if (filterCoverage === 'uncovered') return r.coverageStatus === 'Uncovered';
    return true;
  });

  // Find linked files and tests for selectedReq
  const linkedFiles = files.filter((f) => selectedReq.linkedFileIds.includes(f.id));
  const linkedTests = testCases.filter((t) => selectedReq.linkedTestIds.includes(t.id));

  return (
    <div className="flex-1 flex overflow-hidden bg-[#0B0E14] text-[#E6EDF3]">
      {/* 1. REQUIREMENTS LIST (LEFT) */}
      <section className="w-96 bg-[#0E131B] border-r border-[#21262D] flex flex-col shrink-0">
        <div className="p-3.5 bg-[#161B22]/50 border-b border-[#21262D] space-y-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText size={15} className="text-[#00E5FF]" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-white">
                DO-178C Requirements
              </h2>
            </div>
            <button
              onClick={onOpenUploadDoc}
              className="flex items-center gap-1 text-[11px] font-semibold text-[#00E5FF] hover:underline"
            >
              <FileUp size={12} />
              <span>Upload Doc</span>
            </button>
          </div>

          <div className="relative">
            <Search size={13} className="absolute left-2.5 top-2.5 text-[#8B949E]" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search REQ-ID or keyword..."
              className="w-full bg-[#0B0E14] border border-[#30363D] rounded-md pl-8 pr-3 py-1.5 text-xs text-[#E6EDF3] placeholder-[#8B949E] focus:outline-none focus:border-[#00E5FF]"
            />
          </div>

          <div className="flex items-center gap-1 p-0.5 bg-[#0B0E14] rounded-md border border-[#21262D]">
            <button
              onClick={() => setFilterCoverage('all')}
              className={`flex-1 py-1 text-[10px] font-medium rounded transition-colors ${
                filterCoverage === 'all' ? 'bg-[#21262D] text-white' : 'text-[#8B949E]'
              }`}
            >
              All ({requirements.length})
            </button>
            <button
              onClick={() => setFilterCoverage('fully')}
              className={`flex-1 py-1 text-[10px] font-medium rounded transition-colors ${
                filterCoverage === 'fully' ? 'bg-[#21262D] text-emerald-400' : 'text-[#8B949E]'
              }`}
            >
              Full
            </button>
            <button
              onClick={() => setFilterCoverage('partial')}
              className={`flex-1 py-1 text-[10px] font-medium rounded transition-colors ${
                filterCoverage === 'partial' ? 'bg-[#21262D] text-amber-400 font-bold' : 'text-[#8B949E]'
              }`}
            >
              Gaps
            </button>
          </div>
        </div>

        {/* LIST OF REQS */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
          {filteredRequirements.map((req) => {
            const isSelected = selectedReq.id === req.id;
            return (
              <div
                key={req.id}
                onClick={() => setSelectedReq(req)}
                className={`p-3 rounded-lg border cursor-pointer transition-all ${
                  isSelected
                    ? 'bg-[#161B22] border-[#00E5FF]/60 shadow-md'
                    : 'bg-[#0B0E14] border-[#21262D] hover:border-[#30363D]'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-mono font-bold text-[#00E5FF]">
                    {req.id}
                  </span>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[9px] font-mono text-[#CBD5E1] px-1 bg-[#161B22] border border-[#21262D] rounded">
                      {req.criticality}
                    </span>
                    <span className={`text-[9px] font-mono px-1 rounded ${
                      req.coverageStatus === 'Fully Covered' ? 'text-emerald-400 bg-emerald-950/40' :
                      'text-amber-400 bg-amber-950/40'
                    }`}>
                      {req.coverageStatus}
                    </span>
                  </div>
                </div>

                <div className="text-xs font-semibold text-white truncate">
                  {req.title}
                </div>
                <div className="text-[11px] text-[#8B949E] line-clamp-2 mt-1">
                  {req.description}
                </div>

                <div className="mt-2 pt-1.5 border-t border-[#21262D] flex items-center justify-between text-[10px] text-[#8B949E] font-mono">
                  <span>{req.linkedTestIds.length} Tests Linked</span>
                  <span>Page {req.page}</span>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* 2. REQUIREMENT INSPECTION & TRACEABILITY CHAIN (RIGHT) */}
      <section className="flex-1 flex flex-col overflow-y-auto p-6 space-y-6">
        {/* REQ DETAIL CARD */}
        <div className="p-5 rounded-xl bg-[#161B22] border border-[#21262D] space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#21262D]">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-mono font-bold text-[#00E5FF] px-2 py-0.5 rounded bg-[#00E5FF]/10 border border-[#00E5FF]/20">
                  {selectedReq.id}
                </span>
                <span className="text-xs font-mono text-emerald-400 font-semibold px-2 py-0.5 bg-emerald-950/40 border border-emerald-900 rounded">
                  {selectedReq.standard} {selectedReq.criticality}
                </span>
                <span className="text-xs text-[#8B949E] font-mono">
                  Status: {selectedReq.reviewStatus}
                </span>
              </div>
              <h1 className="text-lg font-bold text-white mt-1.5 font-heading">
                {selectedReq.title}
              </h1>
            </div>

            <button
              onClick={() => onProposeTestFromReq(selectedReq)}
              className="btn-aerospace-glow btn-shimmer flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-[#00E5FF] hover:bg-cyan-300 text-black text-xs font-bold transition-all shadow-[0_0_12px_rgba(0,229,255,0.25)] shrink-0 cursor-pointer"
            >
              <Sparkles size={13} />
              <span>Propose AI Test Vectors</span>
            </button>
          </div>

          <div>
            <span className="text-[10px] font-mono uppercase text-[#8B949E] tracking-wider block mb-1">
              Exact Requirement Specification Text (Uninterpreted)
            </span>
            <div className="p-3.5 rounded-lg bg-[#0B0E14] border border-[#21262D] text-xs font-mono text-[#CBD5E1] leading-relaxed">
              "{selectedReq.description}"
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-lg bg-[#0B0E14] border border-[#21262D]">
              <span className="text-[10px] font-mono text-[#8B949E] uppercase block">Source Document</span>
              <span className="text-white font-mono text-xs mt-1 block truncate">
                {selectedReq.documentSource}
              </span>
              <span className="text-[10px] text-[#8B949E] block mt-0.5">Section Page {selectedReq.page}</span>
            </div>

            <div className="p-3 rounded-lg bg-[#0B0E14] border border-[#21262D]">
              <span className="text-[10px] font-mono text-[#8B949E] uppercase block">Verification Status</span>
              <span className={`text-xs font-bold mt-1 block ${
                selectedReq.coverageStatus === 'Fully Covered' ? 'text-emerald-400' : 'text-amber-400'
              }`}>
                {selectedReq.coverageStatus}
              </span>
              <span className="text-[10px] text-[#8B949E] block mt-0.5">
                Requires 100% MC/DC branch confirmation
              </span>
            </div>
          </div>
        </div>

        {/* 3. VERIFICATION CHAIN: REQ -> CODE -> TEST -> EVIDENCE */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Layers size={16} className="text-[#00E5FF]" />
              <span>DO-178C Bidirectional Traceability Chain</span>
            </h3>
            <span className="text-[10px] font-mono text-[#8B949E]">
              Requirement → Source File → Test Case → Observed Evidence
            </span>
          </div>

          {/* CHAIN GRAPH TILES */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            
            {/* 1. LINKED CODE MODULE */}
            <div className="p-4 rounded-xl bg-[#161B22] border border-[#21262D] flex flex-col justify-between">
              <div>
                <span className="text-[10px] font-mono uppercase text-[#8B949E] block mb-2">
                  1. Implemented Source Modules
                </span>
                {linkedFiles.map((f) => (
                  <div key={f.id} className="p-2.5 rounded-lg bg-[#0B0E14] border border-[#21262D] mb-2">
                    <div className="text-xs font-semibold text-white font-mono">{f.name}</div>
                    <div className="text-[10px] text-[#8B949E] font-mono">{f.path}</div>
                    <div className="mt-2 text-[10px] text-[#8B949E] flex items-center justify-between">
                      <span>Status: <strong className={f.status === 'failed' ? 'text-rose-400' : 'text-emerald-400'}>{f.status}</strong></span>
                      <span>Cov: <strong className="text-white">{f.coveragePercent}%</strong></span>
                    </div>
                  </div>
                ))}
              </div>

              {linkedFiles[0] && (
                <button
                  onClick={() => {
                    onSelectFile(linkedFiles[0]);
                    onNavigateTab('explorer');
                  }}
                  className="mt-3 text-xs text-[#00E5FF] hover:underline flex items-center gap-1 font-semibold"
                >
                  <span>Open C Code Module</span>
                  <ArrowRight size={12} />
                </button>
              )}
            </div>

            {/* 2. LINKED TEST CASES */}
            <div className="p-4 rounded-xl bg-[#161B22] border border-[#21262D] flex flex-col justify-between">
              <div>
                <span className="text-[10px] font-mono uppercase text-[#8B949E] block mb-2">
                  2. Associated Test Cases ({linkedTests.length})
                </span>
                {linkedTests.map((t) => (
                  <div key={t.id} className="p-2.5 rounded-lg bg-[#0B0E14] border border-[#21262D] mb-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono font-bold text-[#00E5FF]">{t.id}</span>
                      <span className={`text-[9px] font-mono px-1 rounded ${
                        t.lastRunStatus === 'passed' ? 'text-emerald-400 bg-emerald-950/40' : 'text-rose-400 bg-rose-950/40'
                      }`}>
                        {t.lastRunStatus.toUpperCase()}
                      </span>
                    </div>
                    <div className="text-xs text-[#CBD5E1] truncate mt-1">{t.title}</div>
                    <div className="text-[10px] text-[#8B949E] font-mono mt-1">
                      Function: {t.sourceFunction}()
                    </div>
                  </div>
                ))}
              </div>

              <button
                onClick={() => onNavigateTab('test_cases')}
                className="mt-3 text-xs text-[#00E5FF] hover:underline flex items-center gap-1 font-semibold"
              >
                <span>Inspect Test Vector Schema</span>
                <ArrowRight size={12} />
              </button>
            </div>

            {/* 3. EXECUTION EVIDENCE */}
            <div className="p-4 rounded-xl bg-[#161B22] border border-[#21262D] flex flex-col justify-between">
              <div>
                <span className="text-[10px] font-mono uppercase text-[#8B949E] block mb-2">
                  3. Verification Evidence & Logs
                </span>
                <div className="p-2.5 rounded-lg bg-[#0B0E14] border border-[#21262D] space-y-2 text-xs">
                  <div className="text-[11px] text-[#CBD5E1]">
                    {linkedTests.some((t) => t.lastRunStatus === 'failed') ? (
                      <span className="text-rose-400 font-semibold flex items-center gap-1">
                        <AlertCircle size={13} /> Failure Evidence Captured
                      </span>
                    ) : (
                      <span className="text-emerald-400 font-semibold flex items-center gap-1">
                        <CheckCircle2 size={13} /> Verified Execution Evidence
                      </span>
                    )}
                  </div>
                  <div className="text-[10px] text-[#8B949E] font-mono leading-relaxed">
                    Harness run telemetry logged. Trace hash verified against DO-178C revision baseline.
                  </div>
                </div>
              </div>

              <button
                onClick={() => onNavigateTab('issues')}
                className="mt-3 text-xs text-[#00E5FF] hover:underline flex items-center gap-1 font-semibold"
              >
                <span>View Full Diagnostic Evidence</span>
                <ArrowRight size={12} />
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
