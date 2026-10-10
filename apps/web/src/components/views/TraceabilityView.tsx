import React, { useState } from 'react';
import { 
  GitMerge, CheckCircle2, AlertCircle, ArrowRight, 
  FileCode, CheckSquare, Search, Filter, ShieldCheck, 
  ExternalLink
} from 'lucide-react';
import type { Requirement, ProjectFile, TestCase  } from '../../types';

interface TraceabilityViewProps {
  requirements: Requirement[];
  files: ProjectFile[];
  testCases: TestCase[];
  onSelectFile: (file: ProjectFile) => void;
  onSelectTestCase: (tc: TestCase) => void;
  onNavigateTab: (tab: any) => void;
  projectId?: string;
  activeExecutionId?: string | null;
}

export const TraceabilityView: React.FC<TraceabilityViewProps> = ({
  requirements,
  files,
  testCases,
  onSelectFile,
  onSelectTestCase,
  onNavigateTab,
  projectId,
  activeExecutionId,
}) => {
  const [search, setSearch] = useState('');
  const [filterGap, setFilterGap] = useState<'all' | 'gaps_only'>('all');

  const totalReqs = requirements.length;
  const coveredReqs = requirements.filter(
    (r) => r.coverageStatus === 'Fully Covered' || (r.linkedTestIds && r.linkedTestIds.length > 0)
  ).length;
  const traceabilityScore = totalReqs > 0 ? Math.round((coveredReqs / totalReqs) * 1000) / 10 : 0;

  const filteredRequirements = requirements.filter((r) => {
    const matches = r.id.toLowerCase().includes(search.toLowerCase()) ||
                    r.title.toLowerCase().includes(search.toLowerCase());
    if (!matches) return false;
    if (filterGap === 'gaps_only') return r.coverageStatus !== 'Fully Covered';
    return true;
  });

  return (
    <div className="flex-1 overflow-y-auto p-6 bg-[#0B0E14] text-[#E6EDF3] space-y-6">
      {/* 1. TOP HEADER & METRIC SUMMARY */}
      <div className="p-5 rounded-xl bg-[#161B22] border border-[#21262D] space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#21262D]">
          <div>
            <div className="flex items-center gap-2">
              <GitMerge size={17} className="text-[#00E5FF]" />
              <h2 className="text-base font-bold text-white">
                DO-178C Bidirectional Traceability Matrix
              </h2>
            </div>
            <p className="text-xs text-[#8B949E] mt-0.5">
              Tracks complete verification chain: System Requirement → Software Architecture → Test Cases → Execution Evidence.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs text-[#8B949E]">Overall Traceability Score:</span>
            <span className={`text-lg font-mono font-bold ${traceabilityScore >= 90 ? 'text-emerald-400' : 'text-amber-400'}`}>
              {totalReqs > 0 ? `${traceabilityScore}%` : 'Not assessed'}
            </span>
          </div>
        </div>

        {/* SEARCH & FILTER CONTROLS */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="relative w-80">
            <Search size={13} className="absolute left-2.5 top-2.5 text-[#8B949E]" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search Requirement ID or title..."
              className="w-full bg-[#0B0E14] border border-[#30363D] rounded-md pl-8 pr-3 py-1.5 text-xs text-[#E6EDF3] placeholder-[#8B949E] focus:outline-none focus:border-[#00E5FF]"
            />
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setFilterGap(filterGap === 'all' ? 'gaps_only' : 'all')}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold border transition-colors ${
                filterGap === 'gaps_only'
                  ? 'bg-amber-400/20 text-amber-300 border-amber-400/50'
                  : 'bg-[#21262D] text-[#8B949E] border-[#30363D] hover:text-white'
              }`}
            >
              {filterGap === 'gaps_only' ? 'Showing Incomplete Links Only' : 'Show Only Traceability Gaps'}
            </button>
          </div>
        </div>
      </div>

      {/* 2. BIDIRECTIONAL TRACEABILITY TABLE */}
      <div className="p-5 rounded-xl bg-[#161B22] border border-[#21262D] space-y-4">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-[#21262D] text-[10px] font-mono uppercase text-[#8B949E]">
                <th className="pb-2.5 w-44">Requirement</th>
                <th className="pb-2.5 w-60">Source Implementation</th>
                <th className="pb-2.5 w-60">Test Cases</th>
                <th className="pb-2.5 w-32">Run Status</th>
                <th className="pb-2.5 text-right w-36">Evidence Trace</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#21262D]">
              {filteredRequirements.map((req) => {
                const linkedFileObjs = files.filter((f) => req.linkedFileIds.includes(f.id));
                const linkedTestObjs = testCases.filter((t) => req.linkedTestIds.includes(t.id));
                const hasFail = linkedTestObjs.some((t) => t.lastRunStatus === 'failed');

                return (
                  <tr key={req.id} className="hover:bg-[#0B0E14]/80 transition-colors align-top">
                    {/* REQUIREMENT COLUMN */}
                    <td className="py-3 pr-3 font-mono">
                      <div className="text-xs font-bold text-[#00E5FF]">{req.id}</div>
                      <div className="text-[11px] text-white font-sans font-medium mt-0.5">{req.title}</div>
                      <span className="text-[9px] text-[#8B949E] block mt-1">
                        {req.criticality} · Page {req.page}
                      </span>
                    </td>

                    {/* SOURCE FILE COLUMN */}
                    <td className="py-3 pr-3 font-mono">
                      {linkedFileObjs.map((f) => (
                        <div key={f.id} className="mb-1">
                          <button
                            onClick={() => {
                              onSelectFile(f);
                              onNavigateTab('explorer');
                            }}
                            className="text-xs text-white hover:text-[#00E5FF] hover:underline flex items-center gap-1 text-left"
                          >
                            <FileCode size={12} className="text-[#00E5FF] shrink-0" />
                            <span className="truncate">{f.name}</span>
                          </button>
                          <span className="text-[10px] text-[#8B949E] block">{f.path}</span>
                        </div>
                      ))}
                      {linkedFileObjs.length === 0 && (
                        <span className="text-amber-400 italic text-[11px]">No file mapped</span>
                      )}
                    </td>

                    {/* TEST CASES COLUMN */}
                    <td className="py-3 pr-3 font-mono">
                      {linkedTestObjs.map((t) => (
                        <div key={t.id} className="mb-1.5 flex items-center justify-between gap-2">
                          <button
                            onClick={() => {
                              onSelectTestCase(t);
                              onNavigateTab('test_cases');
                            }}
                            className="text-xs text-[#CBD5E1] hover:text-[#00E5FF] hover:underline truncate"
                          >
                            {t.id}
                          </button>
                          <span className={`text-[9px] px-1 rounded uppercase font-semibold ${
                            t.lastRunStatus === 'passed' ? 'text-emerald-400 bg-emerald-950/40' :
                            t.lastRunStatus === 'failed' ? 'text-rose-400 bg-rose-950/40' :
                            'text-[#8B949E] bg-[#161B22]'
                          }`}>
                            {t.lastRunStatus}
                          </span>
                        </div>
                      ))}
                      {linkedTestObjs.length === 0 && (
                        <span className="text-rose-400 italic text-[11px]">Missing test coverage link</span>
                      )}
                    </td>

                    {/* RUN STATUS */}
                    <td className="py-3 pr-3 font-mono text-xs">
                      {hasFail ? (
                        <span className="text-rose-400 font-bold flex items-center gap-1">
                          <AlertCircle size={13} /> FAILED
                        </span>
                      ) : linkedTestObjs.length > 0 ? (
                        <span className="text-emerald-400 font-semibold flex items-center gap-1">
                          <CheckCircle2 size={13} /> VERIFIED
                        </span>
                      ) : (
                        <span className="text-amber-400 font-semibold">UNTESTED</span>
                      )}
                    </td>

                    {/* EVIDENCE LINK */}
                    <td className="py-3 text-right">
                      {hasFail ? (
                        <button
                          onClick={() => onNavigateTab('issues')}
                          className="text-[11px] text-rose-400 hover:underline font-semibold cursor-pointer"
                        >
                          View Issue →
                        </button>
                      ) : linkedTestObjs.length > 0 ? (
                        <span className="text-[10px] font-mono text-emerald-400">
                          {activeExecutionId ? `#${activeExecutionId.substring(0, 10)}` : 'Evidence Logged'}
                        </span>
                      ) : (
                        <span className="text-[10px] font-mono text-[#8B949E]">
                          No Evidence
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
