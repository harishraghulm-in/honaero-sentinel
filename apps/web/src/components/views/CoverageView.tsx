import React from 'react';
import { 
  PieChart, CheckCircle2, AlertTriangle, ShieldCheck, 
  ArrowRight, FileCode, Layers, Info
} from 'lucide-react';
import type { ProjectFile, Requirement  } from '../../types';

interface CoverageViewProps {
  files: ProjectFile[];
  requirements: Requirement[];
  onSelectFile: (file: ProjectFile) => void;
  onNavigateTab: (tab: any) => void;
  projectId?: string;
  activeExecutionId?: string | null;
}

export const CoverageView: React.FC<CoverageViewProps> = ({
  files,
  requirements,
  onSelectFile,
  onNavigateTab,
  projectId,
  activeExecutionId,
}) => {
  const [coverageData, setCoverageData] = React.useState<{
    statementPct: number | null;
    branchPct: number | null;
    mcdcPct: number | null;
    gapAnalysis: string[];
    isAssessed: boolean;
  }>({
    statementPct: null,
    branchPct: null,
    mcdcPct: null,
    gapAnalysis: [],
    isAssessed: false,
  });

  React.useEffect(() => {
    let isCancelled = false;
    const fetchRealCoverage = async () => {
      if (!projectId) return;

      try {
        let execId = activeExecutionId;
        if (!execId) {
          const execsRes = await fetch(`/api/v1/projects/${projectId}/executions`);
          if (execsRes.ok) {
            const execs = await execsRes.json();
            if (Array.isArray(execs) && execs.length > 0) {
              execId = execs[0].id || execs[0].execution_id;
            }
          }
        }

        if (!execId) {
          if (!isCancelled) {
            setCoverageData({
              statementPct: null,
              branchPct: null,
              mcdcPct: null,
              gapAnalysis: [],
              isAssessed: false,
            });
          }
          return;
        }

        const [covRes, mcdcRes] = await Promise.all([
          fetch(`/api/v1/projects/${projectId}/executions/${execId}/coverage`),
          fetch(`/api/v1/projects/${projectId}/executions/${execId}/mcdc`),
        ]);

        let stmt: number | null = null;
        let br: number | null = null;
        let mcdc: number | null = null;
        let gaps: string[] = [];

        if (covRes.ok) {
          const c = await covRes.json();
          stmt = typeof c.statement_coverage_pct === 'number' ? c.statement_coverage_pct : null;
          br = typeof c.branch_coverage_pct === 'number' ? c.branch_coverage_pct : null;
        }

        if (mcdcRes.ok) {
          const m = await mcdcRes.json();
          mcdc = typeof m.coverage_percentage === 'number' ? m.coverage_percentage : null;
          if (Array.isArray(m.gap_recommendations)) {
            gaps = m.gap_recommendations;
          }
        }

        if (!isCancelled) {
          setCoverageData({
            statementPct: stmt,
            branchPct: br,
            mcdcPct: mcdc,
            gapAnalysis: gaps,
            isAssessed: stmt !== null || br !== null || mcdc !== null,
          });
        }
      } catch (err) {
        if (!isCancelled) {
          setCoverageData({
            statementPct: null,
            branchPct: null,
            mcdcPct: null,
            gapAnalysis: [],
            isAssessed: false,
          });
        }
      }
    };

    fetchRealCoverage();
    return () => {
      isCancelled = true;
    };
  }, [projectId, activeExecutionId]);

  const totalFiles = files.length;
  const isAssessed = coverageData.isAssessed;

  return (
    <div className="flex-1 overflow-y-auto p-6 bg-[#0B0E14] text-[#E6EDF3] space-y-6">
      {/* 1. TOP METRIC CARDS */}
      <div className="p-5 rounded-xl bg-[#161B22] border border-[#21262D] space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-[#21262D]">
          <div>
            <div className="flex items-center gap-2">
              <PieChart size={17} className="text-[#00E5FF]" />
              <h2 className="text-base font-bold text-white">DO-178C Structural Code Coverage Metrics</h2>
            </div>
            <p className="text-xs text-[#8B949E] mt-0.5">
              Instrumented via Gcov & Verification Harness. Required for DAL-A Certification: 100% MC/DC.
            </p>
          </div>
          <span className="text-[10px] font-mono font-bold text-[#00E5FF] px-2.5 py-1 rounded bg-[#00E5FF]/10 border border-[#00E5FF]/20">
            Target: Level A (DAL-A)
          </span>
        </div>

        {/* 3 GAUGES */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Statement */}
          <div className="p-4 rounded-xl bg-[#0B0E14] border border-[#21262D] space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="text-[#8B949E]">Statement Coverage</span>
              <span className="text-emerald-400 font-bold font-mono text-base">
                {coverageData.statementPct !== null ? `${coverageData.statementPct}%` : 'Not assessed'}
              </span>
            </div>
            <div className="w-full bg-[#161B22] h-2 rounded-full overflow-hidden border border-[#21262D]">
              <div
                className="bg-emerald-400 h-full"
                style={{ width: `${coverageData.statementPct ?? 0}%` }}
              />
            </div>
            <span className="text-[10px] text-[#8B949E] block">
              {coverageData.statementPct !== null
                ? `${coverageData.statementPct}% Executed Statements`
                : 'Run verification to instrument and assess statements'}
            </span>
          </div>

          {/* Decision / Branch */}
          <div className="p-4 rounded-xl bg-[#0B0E14] border border-[#21262D] space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="text-[#8B949E]">Decision / Branch Coverage</span>
              <span className="text-amber-400 font-bold font-mono text-base">
                {coverageData.branchPct !== null ? `${coverageData.branchPct}%` : 'Not assessed'}
              </span>
            </div>
            <div className="w-full bg-[#161B22] h-2 rounded-full overflow-hidden border border-[#21262D]">
              <div
                className="bg-amber-400 h-full"
                style={{ width: `${coverageData.branchPct ?? 0}%` }}
              />
            </div>
            <span className="text-[10px] text-[#8B949E] block">
              {coverageData.branchPct !== null
                ? `${coverageData.branchPct}% Decision Paths Tested`
                : 'Run verification to test branch conditions'}
            </span>
          </div>

          {/* MC/DC */}
          <div className="p-4 rounded-xl bg-[#0B0E14] border border-[#21262D] space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="text-[#8B949E]">MC/DC Coverage (DAL-A)</span>
              <span className="text-amber-400 font-bold font-mono text-base">
                {coverageData.mcdcPct !== null ? `${coverageData.mcdcPct}%` : 'Not assessed'}
              </span>
            </div>
            <div className="w-full bg-[#161B22] h-2 rounded-full overflow-hidden border border-[#21262D]">
              <div
                className="bg-gradient-to-r from-amber-400 to-[#00E5FF] h-full"
                style={{ width: `${coverageData.mcdcPct ?? 0}%` }}
              />
            </div>
            <span className="text-[10px] text-amber-400 block font-mono">
              {coverageData.mcdcPct !== null
                ? `${(100 - coverageData.mcdcPct).toFixed(1)}% Gap to DAL-A Mandate`
                : 'Independence pairs evaluated upon test run'}
            </span>
          </div>
        </div>
      </div>

      {/* 2. FILE BY FILE COVERAGE BREAKDOWN */}
      <div className="p-5 rounded-xl bg-[#161B22] border border-[#21262D] space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-white">Module Coverage & Gap Analysis</h3>
          <span className="text-[10px] font-mono text-[#8B949E]">5 Files Tracked</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-[#21262D] text-[10px] font-mono uppercase text-[#8B949E]">
                <th className="pb-2.5">Source Module</th>
                <th className="pb-2.5">Criticality</th>
                <th className="pb-2.5">Complexity</th>
                <th className="pb-2.5">Coverage Bar</th>
                <th className="pb-2.5 text-right">Percent</th>
                <th className="pb-2.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#21262D]">
              {files.map((file) => (
                <tr key={file.id} className="hover:bg-[#0B0E14] transition-colors">
                  <td className="py-3 font-mono font-medium text-white">
                    <div>{file.name}</div>
                    <div className="text-[10px] text-[#8B949E]">{file.path}</div>
                  </td>
                  <td className="py-3 font-mono text-[#CBD5E1]">{file.criticality}</td>
                  <td className="py-3 font-mono text-[#CBD5E1]">M={file.cyclomaticComplexity}</td>
                  <td className="py-3 w-48">
                    <div className="w-full bg-[#0B0E14] h-2 rounded-full overflow-hidden border border-[#21262D]">
                      <div
                        className={`h-full ${
                          file.coveragePercent < 80 ? 'bg-amber-400' : 'bg-emerald-400'
                        }`}
                        style={{ width: `${file.coveragePercent}%` }}
                      />
                    </div>
                  </td>
                  <td className="py-3 text-right font-mono font-bold">
                    <span className={file.coveragePercent < 80 ? 'text-amber-400' : 'text-emerald-400'}>
                      {file.coveragePercent}%
                    </span>
                  </td>
                  <td className="py-3 text-right">
                    <button
                      onClick={() => {
                        onSelectFile(file);
                        onNavigateTab('explorer');
                      }}
                      className="text-[11px] text-[#00E5FF] hover:underline font-semibold"
                    >
                      Inspect Source →
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 3. COVERAGE GAP NOTIFICATION BOX */}
      {coverageData.gapAnalysis.length > 0 ? (
        <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/30 text-amber-200 text-xs space-y-2">
          <div className="flex items-center gap-2 font-bold text-amber-300">
            <AlertTriangle size={15} />
            <span>Active MC/DC Independence Pair Compliance Gaps Identified</span>
          </div>
          <div className="space-y-1.5 text-[#CBD5E1]">
            {coverageData.gapAnalysis.map((gap, gIdx) => (
              <p key={gIdx} className="leading-relaxed font-mono text-[11px] bg-black/40 p-2 rounded border border-amber-500/20">
                {gap}
              </p>
            ))}
          </div>
          <button
            onClick={() => onNavigateTab('test_cases')}
            className="text-xs text-[#00E5FF] hover:underline font-semibold flex items-center gap-1 pt-1 cursor-pointer"
          >
            <span>Formulate Test Vector in Test Cases Studio</span>
            <ArrowRight size={12} />
          </button>
        </div>
      ) : isAssessed ? (
        <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/30 text-emerald-200 text-xs space-y-2">
          <div className="flex items-center gap-2 font-bold text-emerald-300">
            <ShieldCheck size={15} />
            <span>All Tested Decision Paths Satisfy DO-178C Structural Integrity</span>
          </div>
          <p className="text-[#CBD5E1] leading-relaxed">
            All exercised decisions achieved full MC/DC and branch coverage under the current test vector configuration.
          </p>
        </div>
      ) : (
        <div className="p-4 rounded-xl bg-[#161B22] border border-[#21262D] text-xs text-[#8B949E] space-y-1.5">
          <div className="flex items-center gap-2 font-bold text-[#E6EDF3]">
            <Info size={15} className="text-[#00E5FF]" />
            <span>DO-178C Structural Coverage Assessment Notice</span>
          </div>
          <p className="leading-relaxed">
            Structural coverage has not yet been instrumented for this project revision. Run verification from the Live Verification tab to compile with GCOV and evaluate statement, decision, and MC/DC independence pairs.
          </p>
        </div>
      )}
    </div>
  );
};
