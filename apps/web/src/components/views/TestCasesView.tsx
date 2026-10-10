import React, { useState } from 'react';
import { 
  CheckSquare, Play, Plus, Sparkles, AlertCircle, 
  CheckCircle2, Trash2, Edit3, Save, X, RefreshCw, 
  HelpCircle, Sliders, Hash, Check
} from 'lucide-react';
import type { TestCase, Requirement, ProjectFile, TestVectorField  } from '../../types';

interface TestCasesViewProps {
  testCases: TestCase[];
  requirements: Requirement[];
  files: ProjectFile[];
  selectedTestCase?: TestCase;
  onSelectTestCase: (tc: TestCase) => void;
  onSaveTestCase: (tc: TestCase) => void;
  onDeleteTestCase: (id: string) => void;
  onExecuteTestCase: (tc: TestCase) => void;
  onAddNewTestCase: (tc: TestCase) => void;
}

export const TestCasesView: React.FC<TestCasesViewProps> = ({
  testCases,
  requirements,
  files,
  selectedTestCase,
  onSelectTestCase,
  onSaveTestCase,
  onDeleteTestCase,
  onExecuteTestCase,
  onAddNewTestCase,
}) => {
  const [vectorValues, setVectorValues] = useState<Record<string, any>>({});
  const [isEditingVector, setIsEditingVector] = useState(false);
  const [showAiModal, setShowAiModal] = useState(false);
  const [showManualModal, setShowManualModal] = useState(false);

  // Manual Test Creator state
  const [manualTitle, setManualTitle] = useState('');
  const [manualReqId, setManualReqId] = useState(requirements[0]?.id || '');
  const [manualFileId, setManualFileId] = useState(files[0]?.id || '');
  const [manualFnName, setManualFnName] = useState('sensor_validate');
  const [manualObjective, setManualObjective] = useState('');
  const [manualExpected, setManualExpected] = useState('');
  const [manualInputParam, setManualInputParam] = useState('input_val');
  const [manualInputValue, setManualInputValue] = useState('100');

  // AI Modal generator state
  const [selectedReqForAi, setSelectedReqForAi] = useState<string>(requirements[0]?.id || '');
  const [isGeneratingAi, setIsGeneratingAi] = useState(false);
  const [aiProposal, setAiProposal] = useState<TestCase | null>(null);

  // Initialize vector inputs from selected test case
  const currentSchema = selectedTestCase?.vectorSchema || [];

  const handleFieldChange = (fieldName: string, val: any) => {
    setVectorValues((prev) => ({
      ...prev,
      [fieldName]: val,
    }));
  };

  const getFieldValue = (field: TestVectorField) => {
    if (vectorValues[field.name] !== undefined) {
      return vectorValues[field.name];
    }
    return field.currentValue;
  };

  // Run dynamic validation
  const validateField = (field: TestVectorField, val: any) => {
    if (field.type === 'float' || field.type === 'int') {
      const num = Number(val);
      if (isNaN(num)) return { valid: false, message: 'Must be a valid number' };
      if (field.min !== undefined && num < field.min) {
        return { valid: false, message: `Below min bound (${field.min} ${field.unit || ''})` };
      }
      if (field.max !== undefined && num > field.max) {
        return { valid: false, message: `Exceeds max bound (${field.max} ${field.unit || ''})` };
      }
    }
    return { valid: true };
  };

  // Save changes to test vector
  const handleSaveVectorChanges = () => {
    if (!selectedTestCase) return;
    const updatedSchema = currentSchema.map((field) => ({
      ...field,
      currentValue: vectorValues[field.name] !== undefined ? vectorValues[field.name] : field.currentValue,
    }));

    onSaveTestCase({
      ...selectedTestCase,
      vectorSchema: updatedSchema,
    });
    setIsEditingVector(false);
  };

  // Trigger AI test case proposal
  const handleGenerateAiTest = () => {
    setIsGeneratingAi(true);
    setTimeout(() => {
      setIsGeneratingAi(false);
      const req = requirements.find((r) => r.id === selectedReqForAi) || requirements[0];
      const proposed: TestCase = {
        id: `TC-${req.id.replace('REQ-', '')}-03`,
        title: `MC/DC Corner Case: ${req.title}`,
        requirementId: req.id,
        fileId: req.linkedFileIds[0] || 'fcc_pitch_ctrl',
        sourceFunction: 'update_pitch_actuation',
        objective: 'Test decision boundary where rate of change exceeds structural slew rate limit.',
        preconditions: 'High aerodynamic pressure, sudden pilot control reversal.',
        vectorSchema: [
          {
            name: 'pilot_command_deg',
            label: 'Rapid Stick Reversal',
            type: 'float',
            currentValue: -14.8,
            unit: 'deg',
            min: -15.0,
            max: 25.0,
            description: 'Negative pitch authority limit test',
            isBoundaryCase: true,
          },
          {
            name: 'q_bar_dynamic_pressure',
            label: 'Dynamic Pressure (Q_bar)',
            type: 'float',
            currentValue: 450.0,
            unit: 'lb/ft²',
            min: 0.0,
            max: 800.0,
            description: 'Exact threshold boundary',
            isBoundaryCase: true,
          },
          {
            name: 'autopilot_disengage_switch',
            label: 'Autopilot Disengage Switch',
            type: 'boolean',
            currentValue: false,
            description: 'Autopilot remains active',
          },
        ],
        expectedResult: 'Actuation rate limited to exactly 12.5 deg/sec; no hydraulic flutter emitted.',
        boundaryCases: ['Negative envelope limit -15.0 deg', 'Q_bar 450.0 threshold'],
        isNegativeTest: true,
        status: 'proposal',
        lastRunStatus: 'not_run',
      };
      setAiProposal(proposed);
    }, 1200);
  };

  const handleApproveAiProposal = () => {
    if (aiProposal) {
      onAddNewTestCase({
        ...aiProposal,
        status: 'approved',
      });
      setShowAiModal(false);
      setAiProposal(null);
    }
  };

  return (
    <div className="flex-1 flex overflow-hidden bg-[#0B0E14] text-[#E6EDF3]">
      {/* 1. TEST CASE LIST (LEFT COLUMN) */}
      <section className="w-80 bg-[#0E131B] border-r border-[#21262D] flex flex-col shrink-0">
        <div className="p-3.5 bg-[#161B22]/50 border-b border-[#21262D] flex items-center justify-between">
          <div>
            <h2 className="text-xs font-bold uppercase tracking-wider text-white">
              Test Harness Suite
            </h2>
            <span className="text-[10px] font-mono text-[#8B949E]">
              {testCases.length} Defined Test Cases
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowManualModal(true)}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-[#21262D] hover:bg-[#30363D] text-white text-xs font-semibold border border-[#30363D] transition-colors"
            >
              <Plus size={12} />
              <span>Manual Test</span>
            </button>
            <button
              onClick={() => {
                setAiProposal(null);
                setShowAiModal(true);
              }}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-[#00E5FF] hover:bg-cyan-300 text-black text-xs font-bold transition-all shadow-[0_0_10px_rgba(0,229,255,0.25)]"
            >
              <Sparkles size={12} />
              <span>Generate Test</span>
            </button>
          </div>
        </div>

        {/* LIST OF TEST CASES */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
          {testCases.length === 0 ? (
            <div className="p-4 text-center text-xs text-[#8B949E] font-mono">
              No test cases defined. Generate from requirements or create a manual test vector.
            </div>
          ) : testCases.map((tc) => {
            const isSelected = selectedTestCase?.id === tc.id;
            return (
              <div
                key={tc.id}
                onClick={() => {
                  onSelectTestCase(tc);
                  setVectorValues({});
                }}
                className={`p-3 rounded-lg border cursor-pointer transition-all ${
                  isSelected
                    ? 'bg-[#161B22] border-[#00E5FF]/60 shadow-md'
                    : 'bg-[#0B0E14] border-[#21262D] hover:border-[#30363D]'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-mono font-bold text-[#00E5FF]">
                    {tc.id}
                  </span>
                  <span className={`text-[9px] font-mono px-1.5 py-0.2 rounded font-semibold ${
                    tc.lastRunStatus === 'passed' ? 'text-emerald-400 bg-emerald-950/40' :
                    tc.lastRunStatus === 'failed' ? 'text-rose-400 bg-rose-950/40' :
                    'text-[#8B949E] bg-[#161B22]'
                  }`}>
                    {tc.lastRunStatus.toUpperCase()}
                  </span>
                </div>

                <div className="text-xs font-semibold text-white truncate">
                  {tc.title}
                </div>

                <div className="mt-1.5 pt-1.5 border-t border-[#21262D] flex items-center justify-between text-[10px] text-[#8B949E] font-mono">
                  <span>{tc.requirementId}</span>
                  <span>{tc.vectorSchema.length} Inputs</span>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* 2. DYNAMIC TEST VECTOR EDITOR & SCENARIO INSPECTION */}
      <section className="flex-1 flex flex-col overflow-y-auto p-6 space-y-6">
        {!selectedTestCase ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-8 text-[#8B949E] font-mono">
            <CheckSquare size={36} className="text-[#00E5FF]/40 mb-3" />
            <h3 className="text-white text-sm font-semibold mb-1">No Test Case Selected</h3>
            <p className="text-xs max-w-sm">Select an existing test case from the list on the left, or click "Generate Test" to formulate tests from uploaded requirements.</p>
          </div>
        ) : (
          <>
        {/* HEADER OF TEST CASE */}
        <div className="p-5 rounded-xl bg-[#161B22] border border-[#21262D] space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#21262D]">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-mono font-bold text-[#00E5FF]">
                  {selectedTestCase.id}
                </span>
                <span className="text-xs font-mono text-[#CBD5E1] px-2 py-0.5 bg-[#0B0E14] border border-[#21262D] rounded">
                  Req: {selectedTestCase.requirementId}
                </span>
                <span className={`text-xs font-mono px-2 py-0.5 rounded font-semibold ${
                  selectedTestCase.lastRunStatus === 'passed' ? 'text-emerald-400 bg-emerald-950/40' :
                  selectedTestCase.lastRunStatus === 'failed' ? 'text-rose-400 bg-rose-950/40' :
                  'text-[#8B949E] bg-[#0B0E14]'
                }`}>
                  {selectedTestCase.lastRunStatus.toUpperCase()}
                </span>
              </div>

              <h1 className="text-lg font-bold text-white mt-1">
                {selectedTestCase.title}
              </h1>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => onExecuteTestCase(selectedTestCase)}
                className="btn-aerospace-glow btn-shimmer flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#00E5FF] hover:bg-cyan-300 text-black text-xs font-bold transition-all shadow-[0_0_12px_rgba(0,229,255,0.25)] cursor-pointer"
              >
                <Play size={13} fill="currentColor" />
                <span>Execute Vector</span>
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="p-3 rounded-lg bg-[#0B0E14] border border-[#21262D]">
              <span className="text-[10px] font-mono text-[#8B949E] uppercase block mb-1">Objective</span>
              <span className="text-[#CBD5E1]">{selectedTestCase.objective}</span>
            </div>
            <div className="p-3 rounded-lg bg-[#0B0E14] border border-[#21262D]">
              <span className="text-[10px] font-mono text-[#8B949E] uppercase block mb-1">Preconditions</span>
              <span className="text-[#CBD5E1]">{selectedTestCase.preconditions}</span>
            </div>
          </div>
        </div>

        {/* DYNAMIC TEST VECTOR INPUTS (ADAPTIVE SCHEMA) */}
        <div className="p-5 rounded-xl bg-[#161B22] border border-[#21262D] space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#21262D]">
            <div className="flex items-center gap-2">
              <Sliders size={16} className="text-[#00E5FF]" />
              <h3 className="text-sm font-bold text-white">
                Dynamic Test Vector Schema ({currentSchema.length} Parameters)
              </h3>
            </div>

            <div className="flex items-center gap-2">
              {isEditingVector ? (
                <>
                  <button
                    onClick={handleSaveVectorChanges}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black text-xs font-bold transition-colors"
                  >
                    <Save size={12} />
                    <span>Save Vector</span>
                  </button>
                  <button
                    onClick={() => {
                      setVectorValues({});
                      setIsEditingVector(false);
                    }}
                    className="p-1.5 text-[#8B949E] hover:text-white rounded"
                  >
                    <X size={14} />
                  </button>
                </>
              ) : (
                <button
                  onClick={() => setIsEditingVector(true)}
                  className="flex items-center gap-1 px-3 py-1 text-xs font-semibold text-[#00E5FF] hover:bg-[#21262D] rounded border border-[#00E5FF]/30 transition-colors"
                >
                  <Edit3 size={12} />
                  <span>Modify Inputs</span>
                </button>
              )}
            </div>
          </div>

          {/* DYNAMIC INPUT FIELDS GRID */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {currentSchema.map((field) => {
              const currentVal = getFieldValue(field);
              const validation = validateField(field, currentVal);

              return (
                <div
                  key={field.name}
                  className="p-3.5 rounded-lg bg-[#0B0E14] border border-[#21262D] space-y-2 flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between">
                      <label className="text-xs font-semibold text-white truncate">
                        {field.label}
                      </label>
                      <span className="text-[10px] font-mono text-[#8B949E] uppercase">
                        {field.type}
                      </span>
                    </div>
                    <div className="text-[11px] text-[#8B949E] mt-0.5 line-clamp-1">
                      {field.description}
                    </div>
                  </div>

                  {/* Dynamic control type */}
                  <div className="pt-2">
                    {field.type === 'boolean' ? (
                      <div className="flex items-center gap-3">
                        <button
                          disabled={!isEditingVector}
                          onClick={() => handleFieldChange(field.name, true)}
                          className={`flex-1 py-1 text-xs font-mono font-bold rounded border ${
                            currentVal === true
                              ? 'bg-cyan-500/20 text-[#00E5FF] border-[#00E5FF]'
                              : 'bg-[#161B22] text-[#8B949E] border-[#21262D]'
                          }`}
                        >
                          TRUE
                        </button>
                        <button
                          disabled={!isEditingVector}
                          onClick={() => handleFieldChange(field.name, false)}
                          className={`flex-1 py-1 text-xs font-mono font-bold rounded border ${
                            currentVal === false
                              ? 'bg-rose-500/20 text-rose-300 border-rose-500'
                              : 'bg-[#161B22] text-[#8B949E] border-[#21262D]'
                          }`}
                        >
                          FALSE
                        </button>
                      </div>
                    ) : (
                      <div className="relative">
                        <input
                          type={field.type === 'int' || field.type === 'float' ? 'number' : 'text'}
                          disabled={!isEditingVector}
                          value={currentVal}
                          onChange={(e) => handleFieldChange(field.name, e.target.value)}
                          className={`w-full bg-[#161B22] border rounded-md px-3 py-1.5 text-xs font-mono text-white focus:outline-none ${
                            !validation.valid ? 'border-rose-500' : 'border-[#30363D] focus:border-[#00E5FF]'
                          } ${!isEditingVector ? 'opacity-80 cursor-not-allowed' : ''}`}
                        />
                        {field.unit && (
                          <span className="absolute right-2.5 top-1.5 text-[10px] font-mono text-[#8B949E]">
                            {field.unit}
                          </span>
                        )}
                      </div>
                    )}

                    {!validation.valid && (
                      <div className="text-[10px] text-rose-400 mt-1 flex items-center gap-1">
                        <AlertCircle size={10} />
                        <span>{validation.message}</span>
                      </div>
                    )}

                    {field.min !== undefined && field.max !== undefined && (
                      <div className="text-[10px] font-mono text-[#8B949E] mt-1 flex justify-between">
                        <span>Min: {field.min} {field.unit}</span>
                        <span>Max: {field.max} {field.unit}</span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* EXPECTED VS OBSERVED EXECUTION RESULT */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl bg-[#161B22] border border-[#21262D]">
            <span className="text-[10px] font-mono uppercase text-[#00E5FF] block mb-2 font-semibold">
              Expected Correctness Result (DO-178C Specification)
            </span>
            <div className="p-3 rounded-lg bg-[#0B0E14] border border-[#21262D] text-xs font-mono text-[#CBD5E1] leading-relaxed">
              {selectedTestCase.expectedResult}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[#161B22] border border-[#21262D]">
            <span className="text-[10px] font-mono uppercase text-[#8B949E] block mb-2 font-semibold">
              Actual Observed Execution Telemetry
            </span>
            <div className="p-3 rounded-lg bg-[#0B0E14] border border-[#21262D] text-xs font-mono leading-relaxed">
              {selectedTestCase.observedResult ? (
                <span className={selectedTestCase.lastRunStatus === 'failed' ? 'text-rose-400' : 'text-emerald-400'}>
                  {selectedTestCase.observedResult}
                </span>
              ) : (
                <span className="text-[#8B949E] italic">
                  Not executed yet. Click "Execute Vector" to run through C++ harness.
                </span>
              )}
            </div>
          </div>
        </div>
        </>
      )}
      </section>

      {/* AI TEST CASE GENERATION MODAL */}
      {showAiModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-[#161B22] border border-[#30363D] rounded-xl max-w-xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-[#21262D]">
              <div className="flex items-center gap-2">
                <Sparkles size={18} className="text-[#00E5FF]" />
                <h3 className="text-sm font-bold text-white">AI-Assisted Test Case Generator</h3>
              </div>
              <button onClick={() => setShowAiModal(false)} className="text-[#8B949E] hover:text-white">
                <X size={16} />
              </button>
            </div>

            <p className="text-xs text-[#8B949E] leading-relaxed">
              Select a DO-178C requirement to automatically formulate negative boundary tests, MC/DC criteria, and typed test vectors. 
              <strong className="text-[#CBD5E1] block mt-1">Note: AI-generated tests are proposals and require execution validation.</strong>
            </p>

            <div>
              <label className="text-xs font-semibold text-white block mb-1.5">
                Target Requirement
              </label>
              <select
                value={selectedReqForAi}
                onChange={(e) => setSelectedReqForAi(e.target.value)}
                className="w-full bg-[#0B0E14] border border-[#30363D] rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-[#00E5FF]"
              >
                {requirements.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.id}: {r.title} ({r.criticality})
                  </option>
                ))}
              </select>
            </div>

            {/* AI PROPOSAL PREVIEW */}
            {aiProposal && (
              <div className="p-4 rounded-lg bg-[#0B0E14] border border-[#00E5FF]/40 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-[#00E5FF]">
                    Proposed: {aiProposal.id}
                  </span>
                  <span className="text-[10px] font-mono text-amber-400 bg-amber-950/40 px-1.5 py-0.5 rounded border border-amber-900">
                    Proposal (Unexecuted)
                  </span>
                </div>
                <div className="text-xs font-semibold text-white">{aiProposal.title}</div>
                <div className="text-[11px] text-[#8B949E]">{aiProposal.objective}</div>
                <div className="text-[10px] font-mono text-[#CBD5E1] pt-1">
                  Expected: {aiProposal.expectedResult}
                </div>
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#21262D]">
              <button
                onClick={() => setShowAiModal(false)}
                className="px-4 py-2 rounded-lg bg-[#21262D] text-xs font-semibold text-[#8B949E] hover:text-white"
              >
                Cancel
              </button>

              {!aiProposal ? (
                <button
                  onClick={handleGenerateAiTest}
                  disabled={isGeneratingAi}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#00E5FF] hover:bg-cyan-300 text-black text-xs font-bold transition-all shadow-[0_0_12px_rgba(0,229,255,0.25)]"
                >
                  {isGeneratingAi ? (
                    <>
                      <RefreshCw size={13} className="animate-spin" />
                      <span>Generating Scenarios...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles size={13} />
                      <span>Formulate Test Proposal</span>
                    </>
                  )}
                </button>
              ) : (
                <button
                  onClick={handleApproveAiProposal}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black text-xs font-bold transition-colors"
                >
                  <Check size={14} />
                  <span>Approve & Add to Suite</span>
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* CREATE MANUAL TEST CASE MODAL */}
      {showManualModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-[#161B22] border border-[#30363D] rounded-xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-[#21262D]">
              <div className="flex items-center gap-2">
                <CheckSquare size={18} className="text-[#00E5FF]" />
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Create Manual Test Case
                </h3>
              </div>
              <button onClick={() => setShowManualModal(false)} className="text-[#8B949E] hover:text-white">
                <X size={16} />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-xs font-semibold text-white block mb-1">Test Case Title</label>
                <input
                  type="text"
                  placeholder="e.g. Boundary Validation: Max Dynamic Pressure"
                  value={manualTitle}
                  onChange={(e) => setManualTitle(e.target.value)}
                  className="w-full bg-[#0B0E14] border border-[#30363D] rounded-lg px-3 py-2 text-white focus:outline-none focus:border-[#00E5FF]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-white block mb-1">Target Function</label>
                  <input
                    type="text"
                    placeholder="e.g. sensor_read"
                    value={manualFnName}
                    onChange={(e) => setManualFnName(e.target.value)}
                    className="w-full bg-[#0B0E14] border border-[#30363D] rounded-lg px-3 py-2 text-white focus:outline-none focus:border-[#00E5FF]"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-white block mb-1">Related Requirement</label>
                  <select
                    value={manualReqId}
                    onChange={(e) => setManualReqId(e.target.value)}
                    className="w-full bg-[#0B0E14] border border-[#30363D] rounded-lg px-3 py-2 text-white focus:outline-none focus:border-[#00E5FF]"
                  >
                    {requirements.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.id}: {r.title}
                      </option>
                    ))}
                    {requirements.length === 0 && <option value="REQ-MANUAL">REQ-MANUAL-001</option>}
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-white block mb-1">Test Objective</label>
                <input
                  type="text"
                  placeholder="Verify behavior under specific boundary or invalid conditions"
                  value={manualObjective}
                  onChange={(e) => setManualObjective(e.target.value)}
                  className="w-full bg-[#0B0E14] border border-[#30363D] rounded-lg px-3 py-2 text-white focus:outline-none focus:border-[#00E5FF]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-white block mb-1">Input Parameter Name</label>
                  <input
                    type="text"
                    placeholder="param_name"
                    value={manualInputParam}
                    onChange={(e) => setManualInputParam(e.target.value)}
                    className="w-full bg-[#0B0E14] border border-[#30363D] rounded-lg px-3 py-2 text-white focus:outline-none focus:border-[#00E5FF]"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-white block mb-1">Input Value</label>
                  <input
                    type="text"
                    placeholder="100"
                    value={manualInputValue}
                    onChange={(e) => setManualInputValue(e.target.value)}
                    className="w-full bg-[#0B0E14] border border-[#30363D] rounded-lg px-3 py-2 text-white focus:outline-none focus:border-[#00E5FF]"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-white block mb-1">Expected Outcome</label>
                <input
                  type="text"
                  placeholder="e.g. Return 1 (Nominal Valid)"
                  value={manualExpected}
                  onChange={(e) => setManualExpected(e.target.value)}
                  className="w-full bg-[#0B0E14] border border-[#30363D] rounded-lg px-3 py-2 text-white focus:outline-none focus:border-[#00E5FF]"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#21262D]">
              <button
                onClick={() => setShowManualModal(false)}
                className="px-4 py-2 rounded-lg bg-[#21262D] text-xs font-semibold text-[#8B949E] hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  const newManualId = `TC-MANUAL-${Math.floor(Math.random() * 900) + 100}`;
                  const created: TestCase = {
                    id: newManualId,
                    title: manualTitle || `Manual Test: ${manualFnName}`,
                    requirementId: manualReqId || 'REQ-MANUAL-001',
                    fileId: manualFileId || (files[0]?.id || 'src_0'),
                    sourceFunction: manualFnName || 'sensor_validate',
                    objective: manualObjective || 'Deterministic manual test assertion',
                    preconditions: 'System under test nominal condition',
                    vectorSchema: [
                      {
                        name: manualInputParam || 'val',
                        label: manualInputParam || 'Input',
                        type: isNaN(Number(manualInputValue)) ? 'string' : 'int',
                        currentValue: isNaN(Number(manualInputValue)) ? manualInputValue : Number(manualInputValue),
                        description: 'Manual test input vector',
                      },
                    ],
                    expectedResult: manualExpected || 'Return 0 (Success)',
                    boundaryCases: ['Manual boundary'],
                    isNegativeTest: false,
                    status: 'approved',
                    lastRunStatus: 'not_run',
                  };
                  onAddNewTestCase(created);
                  setShowManualModal(false);
                  setManualTitle('');
                }}
                className="px-4 py-2 rounded-lg bg-[#00E5FF] hover:bg-cyan-300 text-black text-xs font-bold transition-all shadow-[0_0_12px_rgba(0,229,255,0.25)]"
              >
                Save Manual Test Case
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
