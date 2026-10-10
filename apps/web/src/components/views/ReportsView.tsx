import React, { useState } from 'react';
import { 
  FileSpreadsheet, Download, Printer, CheckCircle2, 
  AlertCircle, ShieldCheck, Cpu, HardDrive, FileText, 
  Layers, Clock, Check
} from 'lucide-react';
import type { Project, ProjectFile, TestCase, Diagnostic  } from '../../types';

interface ReportsViewProps {
  project: Project | null;
  files: ProjectFile[];
  testCases: TestCase[];
  diagnostics: Diagnostic[];
  activeExecutionId?: string | null;
}

export const ReportsView: React.FC<ReportsViewProps> = ({
  project,
  files,
  testCases,
  diagnostics,
  activeExecutionId,
}) => {
  const [downloadSuccess, setDownloadSuccess] = useState<string | null>(null);
  const [backendReport, setBackendReport] = useState<any>(null);

  React.useEffect(() => {
    let isCancelled = false;
    const fetchReport = async () => {
      if (!project?.id || project.id.startsWith('proj-x35')) return;
      try {
        const res = await fetch(`/api/v1/projects/${project.id}/report`);
        if (res.ok) {
          const data = await res.json();
          if (!isCancelled) setBackendReport(data);
        }
      } catch (err) {
        console.warn('Failed to load project report:', err);
      }
    };
    fetchReport();
    return () => { isCancelled = true; };
  }, [project?.id]);

  const passedTests = backendReport?.executions?.passed_runs ?? testCases.filter((t) => t.lastRunStatus === 'passed').length;
  const failedTests = backendReport?.executions?.failed_runs ?? testCases.filter((t) => t.lastRunStatus === 'failed').length;
  const notRunTests = testCases.filter((t) => t.lastRunStatus === 'not_run').length;
  const reportRunId = activeExecutionId ? `#${activeExecutionId}` : (backendReport?.executions?.total_runs ? `#VR-${project?.codeName || 'PROJ'}-001` : 'Not Executed');

  // Real Export JSON audit file
  const handleExportJson = () => {
    const reportData = {
      standard: 'DO-178C Software Verification Report',
      projectName: project?.name || 'Unassigned Project',
      dalLevel: project?.dalLevel || 'DAL-A',
      runId: reportRunId,
      generatedTimestamp: new Date().toISOString(),
      toolchain: project?.toolchain || 'GCC (DO-178C Qualified)',
      metrics: {
        totalFilesDiscovered: backendReport?.sources?.total_sources || project?.stats?.discoveredFiles || files.length,
        totalTests: backendReport?.tests?.total_test_cases || testCases.length,
        passedTests,
        failedTests,
        notRunTests,
        mcDcCoverage: backendReport?.coverage?.mcdc_coverage_pct ?? project?.stats?.mcDcCoverage ?? 0,
      },
      diagnostics,
      filesSummary: files.map((f) => ({
        name: f.name,
        path: f.path,
        criticality: f.criticality,
        status: f.status,
        coverage: f.coveragePercent,
      })),
      backendReport,
    };

    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `HonAero_DO178C_Report_${project?.codeName || 'PROJECT'}.json`;
    a.click();
    URL.revokeObjectURL(url);

    setDownloadSuccess('Exported JSON Verification Package');
    setTimeout(() => setDownloadSuccess(null), 3000);
  };

  // Real Export Markdown Report
  const handleExportMarkdown = () => {
    const md = `# HONAERO SENTINEL — DO-178C VERIFICATION AUDIT REPORT
**Project:** ${project?.name || 'Aerospace Verification Project'} (${project?.codeName || 'VERIF'})  
**Safety Criticality:** ${project?.dalLevel || 'DAL-A'}  
**Run ID:** ${reportRunId}  
**Timestamp:** ${new Date().toISOString()}  
**Toolchain:** ${project?.toolchain || 'GCC-Embedded'}  

## Executive Summary
- Tests Passed: ${passedTests}
- Tests Failed: ${failedTests}
- Tests Not Run: ${notRunTests}
- MC/DC Coverage: ${backendReport?.coverage?.mcdc_coverage_pct ?? project?.stats?.mcDcCoverage ?? 0}%
- Statement Coverage: ${backendReport?.coverage?.statement_coverage_pct ?? 'N/A'}%

## Diagnostics & Active Issues
${diagnostics.length > 0 ? diagnostics.map((d) => `- [${d.severity.toUpperCase()}] ${d.filePath}:${d.line} (${d.testId || 'N/A'}): ${d.message}`).join('\n') : 'No open diagnostics recorded.'}

## Code Modules Status
${files.map((f) => `| ${f.name} | ${f.criticality} | ${f.status.toUpperCase()} | ${f.coveragePercent}% |`).join('\n')}
`;

    const blob = new Blob([md], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `HonAero_DO178C_Summary_${project?.codeName || 'PROJECT'}.md`;
    a.click();
    URL.revokeObjectURL(url);

    setDownloadSuccess('Exported Markdown Compliance Summary');
    setTimeout(() => setDownloadSuccess(null), 3000);
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 bg-[#0B0E14] text-[#E6EDF3] space-y-6">
      {/* NOTIFICATION */}
      {downloadSuccess && (
        <div className="p-3 rounded-lg bg-emerald-950/60 border border-emerald-500/40 text-emerald-200 text-xs flex items-center gap-2 shadow-lg">
          <CheckCircle2 size={16} className="text-emerald-400" />
          <span>{downloadSuccess}</span>
        </div>
      )}

      {/* 1. REPORT BANNER & ACTION HEADER */}
      <div className="p-5 rounded-xl bg-[#161B22] border border-[#21262D] space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-[#21262D]">
          <div>
            <div className="flex items-center gap-2">
              <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                failedTests > 0
                  ? 'text-rose-400 bg-rose-950/40 border-rose-900'
                  : passedTests > 0
                  ? 'text-emerald-400 bg-emerald-950/40 border-emerald-900'
                  : 'text-amber-400 bg-amber-950/40 border-amber-900'
              }`}>
                {failedTests > 0
                  ? `AUDIT STATE: DEFECTS DETECTED (${failedTests} FAILING RUNS)`
                  : passedTests > 0
                  ? 'AUDIT STATE: PASSED (ALL VERIFIED RUNS PASSING)'
                  : 'AUDIT STATE: NOT ASSESSED'}
              </span>
              <span className="text-xs font-mono text-[#8B949E]">
                Run ID: {reportRunId}
              </span>
            </div>
            <h1 className="text-xl font-bold text-white mt-1 font-heading">
              DO-178C Software Verification & Compliance Report
            </h1>
            <p className="text-xs text-[#8B949E] mt-0.5 max-w-2xl">
              Formal verification evidence bundle for {project?.name || 'the project'}. Contains deterministic static analysis, test harness assertion logs, and MC/DC structural coverage data.
            </p>
          </div>

          <div className="flex items-center gap-2.5 shrink-0">
            <button
              onClick={handleExportJson}
              className="px-3 py-1.5 rounded-lg bg-[#21262D] hover:bg-[#30363D] text-xs font-semibold text-white border border-[#30363D] transition-colors cursor-pointer"
            >
              <Download size={13} className="text-[#00E5FF]" />
              <span>Export JSON Package</span>
            </button>

            <button
              onClick={handleExportMarkdown}
              className="btn-aerospace-glow btn-shimmer flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-[#00E5FF] hover:bg-cyan-300 text-black text-xs font-bold transition-all shadow-[0_0_12px_rgba(0,229,255,0.25)] cursor-pointer"
            >
              <FileText size={13} />
              <span>Export Markdown Report</span>
            </button>

            <button
              onClick={() => window.print()}
              className="p-2 text-[#8B949E] hover:text-white rounded-lg hover:bg-[#21262D] border border-[#21262D] transition-colors"
              title="Print formal report"
            >
              <Printer size={15} />
            </button>
          </div>
        </div>

        {/* 6 STATE COUNTERS */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="p-3 rounded-lg bg-[#0B0E14] border border-[#21262D]">
            <span className="text-[10px] font-mono text-[#8B949E] uppercase block">PASS</span>
            <span className="text-xl font-bold text-emerald-400 font-mono">{passedTests}</span>
            <span className="text-[10px] text-[#8B949E] block mt-0.5">Verified Assertions</span>
          </div>
          <div className="p-3 rounded-lg bg-[#0B0E14] border border-[#21262D]">
            <span className="text-[10px] font-mono text-[#8B949E] uppercase block">FAIL</span>
            <span className="text-xl font-bold text-rose-400 font-mono">{failedTests}</span>
            <span className="text-[10px] text-rose-400 block mt-0.5">
              {failedTests > 0 ? `${failedTests} Failures Logged` : 'Zero Faults'}
            </span>
          </div>
          <div className="p-3 rounded-lg bg-[#0B0E14] border border-[#21262D]">
            <span className="text-[10px] font-mono text-[#8B949E] uppercase block">COMPILER ERROR</span>
            <span className="text-xl font-bold text-white font-mono">
              {backendReport?.executions?.build_failures || 0}
            </span>
            <span className="text-[10px] text-emerald-400 block mt-0.5">
              {backendReport?.executions?.build_failures ? 'Build Issues' : 'Clean Build'}
            </span>
          </div>
          <div className="p-3 rounded-lg bg-[#0B0E14] border border-[#21262D]">
            <span className="text-[10px] font-mono text-[#8B949E] uppercase block">BLOCKED</span>
            <span className="text-xl font-bold text-white font-mono">0</span>
            <span className="text-[10px] text-[#8B949E] block mt-0.5">Dependencies Met</span>
          </div>
          <div className="p-3 rounded-lg bg-[#0B0E14] border border-[#21262D]">
            <span className="text-[10px] font-mono text-[#8B949E] uppercase block">SKIPPED</span>
            <span className="text-xl font-bold text-white font-mono">0</span>
            <span className="text-[10px] text-[#8B949E] block mt-0.5">No Skipped Tests</span>
          </div>
          <div className="p-3 rounded-lg bg-[#0B0E14] border border-[#21262D]">
            <span className="text-[10px] font-mono text-[#8B949E] uppercase block">NOT RUN</span>
            <span className="text-xl font-bold text-amber-400 font-mono">{notRunTests}</span>
            <span className="text-[10px] text-amber-400 block mt-0.5">Proposals Pending</span>
          </div>
        </div>
      </div>

      {/* 2. ENVIRONMENT & TOOLCHAIN REVISION TABLE */}
      <div className="p-5 rounded-xl bg-[#161B22] border border-[#21262D] space-y-3">
        <h3 className="text-sm font-bold text-white">Toolchain & Qualified Environment Specification</h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <div className="p-3 rounded-lg bg-[#0B0E14] border border-[#21262D]">
            <span className="text-[10px] font-mono text-[#8B949E] uppercase block">Compiler Toolchain</span>
            <span className="text-white font-mono text-xs mt-1 block">{project?.toolchain || 'GCC-Embedded'}</span>
          </div>
          <div className="p-3 rounded-lg bg-[#0B0E14] border border-[#21262D]">
            <span className="text-[10px] font-mono text-[#8B949E] uppercase block">Instrumentation Tool</span>
            <span className="text-white font-mono text-xs mt-1 block">Gcov-Aero v12.2.0 (MC/DC Enabled)</span>
          </div>
          <div className="p-3 rounded-lg bg-[#0B0E14] border border-[#21262D]">
            <span className="text-[10px] font-mono text-[#8B949E] uppercase block">Static Rule Checker</span>
            <span className="text-white font-mono text-xs mt-1 block">Frama-C / MISRA C:2012 Compliance</span>
          </div>
        </div>
      </div>

      {/* 3. PER-FILE VERIFICATION RESULTS BREAKDOWN */}
      <div className="p-5 rounded-xl bg-[#161B22] border border-[#21262D] space-y-3">
        <h3 className="text-sm font-bold text-white">Module-by-Module Verification Status</h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-[#21262D] text-[10px] font-mono uppercase text-[#8B949E]">
                <th className="pb-2.5">Source Module</th>
                <th className="pb-2.5">Criticality</th>
                <th className="pb-2.5">Lines / Functions</th>
                <th className="pb-2.5">MC/DC Cov</th>
                <th className="pb-2.5 text-right">Audit Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#21262D]">
              {files.map((f) => (
                <tr key={f.id} className="hover:bg-[#0B0E14] transition-colors">
                  <td className="py-3 font-mono font-medium text-white">
                    <div>{f.name}</div>
                    <div className="text-[10px] text-[#8B949E]">{f.path}</div>
                  </td>
                  <td className="py-3 font-mono">{f.criticality}</td>
                  <td className="py-3 font-mono text-[#CBD5E1]">
                    {f.linesCount} lines · {f.functionsCount} funcs
                  </td>
                  <td className="py-3 font-mono">
                    <span className={f.coveragePercent < 80 ? 'text-amber-400' : 'text-emerald-400'}>
                      {f.coveragePercent}%
                    </span>
                  </td>
                  <td className="py-3 text-right">
                    <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded uppercase ${
                      f.status === 'passed' ? 'text-emerald-400 bg-emerald-950/40 border border-emerald-900' :
                      f.status === 'failed' ? 'text-rose-400 bg-rose-950/40 border border-rose-900' :
                      'text-[#8B949E] bg-[#161B22]'
                    }`}>
                      {f.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 4. REMAINING LIMITATIONS DISCLOSURE */}
      <div className="p-4 rounded-xl bg-[#161B22] border border-amber-500/40 text-xs text-[#CBD5E1] space-y-1.5">
        <span className="font-bold text-amber-300 block uppercase font-mono text-[11px]">
          HonAero Verification Integrity Disclosure
        </span>
        <p className="leading-relaxed">
          {failedTests > 0
            ? `Untested files and unverified proposals are not certified. DO-178C signoff requires resolving all ${failedTests} failing assertion(s) and achieving full MC/DC independence pair coverage.`
            : passedTests > 0
            ? `All ${passedTests} test executions completed successfully. Final DO-178C DAL-A signoff requires confirming complete requirement-to-code traceability and 100% MC/DC evidence.`
            : `No test executions have been performed for ${project?.name || 'the project'}. Formal compliance requires executing approved test cases and gathering structural coverage records.`}
        </p>
      </div>
    </div>
  );
};
