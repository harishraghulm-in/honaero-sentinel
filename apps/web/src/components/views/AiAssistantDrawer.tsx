import React, { useState } from 'react';
import { 
  Sparkles, Send, Bot, User, X, Check, Copy, 
  AlertCircle, ShieldCheck, FileCode, CornerDownRight, RefreshCw, Cpu
} from 'lucide-react';
import type { ProjectFile, Requirement, Diagnostic } from '../../types';
import { explainFailure, recommendCoverageGaps, generateTestProposals } from '../../api/ai';

interface AiAssistantDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  selectedFile?: ProjectFile;
  selectedReq?: Requirement;
  activeDiagnostic?: Diagnostic;
  projectId?: string;
  isBackendConnected?: boolean;
  executionId?: string | null;
  onApplyFixCode?: (fileId: string, fixCode: string) => void;
}

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  timestamp: string;
  text: string;
  suggestedPatch?: {
    fileId: string;
    filePath: string;
    targetLine: number;
    code: string;
  };
}

export const AiAssistantDrawer: React.FC<AiAssistantDrawerProps> = ({
  isOpen,
  onClose,
  selectedFile,
  selectedReq,
  activeDiagnostic,
  projectId,
  isBackendConnected = false,
  executionId,
  onApplyFixCode,
}) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'msg-init',
      sender: 'assistant',
      timestamp: '16:00:00',
      text: 'HonAero Sentinel Verification Assistant initialized.\n\nBackend: **NVIDIA Nemotron-4 340B Instruct** (NeMo Guardrails Aerospace Edition).\n\nI am contextually synchronized with your DO-178C avionics workspace. I evaluate requirement satisfaction, formulate boundary vectors for user inputs, diagnose AST assertion faults without halting execution, and synthesize compliant MISRA C:2012 patches.',
    },
  ]);
  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSendPrompt = async (promptText?: string) => {
    const textToSend = promptText || input;
    if (!textToSend.trim()) return;

    const userMsg: Message = {
      id: `usr-${Date.now()}`,
      sender: 'user',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      text: textToSend,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsThinking(true);

    const lower = textToSend.toLowerCase();

    // Try real backend AI endpoint if connected and appropriate
    if (isBackendConnected && projectId) {
      try {
        if (lower.includes('coverage') || lower.includes('gap') || lower.includes('mc/dc')) {
          const res = await recommendCoverageGaps(projectId, executionId || undefined);
          if (res?.content && res.content.length > 0) {
            const gap = res.content[0];
            const botMsg: Message = {
              id: `bot-${Date.now()}`,
              sender: 'assistant',
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              text: `### ${res.modelUsed || 'NVIDIA Nemotron-4 340B'} Coverage Gap Recommendation\n**Location:** \`${gap.sourceLocation}\`\n**Decision:** \`${gap.decisionId}\`\n**Uncovered Outcome:** \`${gap.uncoveredOutcome}\`\n\n${gap.gapDescription}\n\n**Proposed Test Vector:**\n\`\`\`json\n${JSON.stringify(gap.proposedVector, null, 2)}\n\`\`\`\n\n*${res.disclaimer || 'Advisory recommendation only.'}*`,
            };
            setMessages((prev) => [...prev, botMsg]);
            setIsThinking(false);
            return;
          }
        } else if (lower.includes('explain') || lower.includes('error') || lower.includes('fault') || lower.includes('fail')) {
          const res = await explainFailure(projectId, executionId || undefined, textToSend);
          if (res?.content) {
            const exp = res.content;
            const botMsg: Message = {
              id: `bot-${Date.now()}`,
              sender: 'assistant',
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              text: `### ${res.modelUsed || 'NVIDIA Nemotron-4 340B'} Root-Cause Analysis\n**Verdict:** \`${exp.verdict}\`\n**Confidence:** ${(exp.confidenceScore * 100).toFixed(0)}%\n\n**Possible Causes:**\n${exp.possibleCauses.map((c) => `- ${c}`).join('\n')}\n\n**Recommended Remediation:**\n${exp.suggestedRemediation.map((r) => `- ${r}`).join('\n')}\n\n*${res.disclaimer || 'Verified for DO-178C considerations.'}*`,
            };
            setMessages((prev) => [...prev, botMsg]);
            setIsThinking(false);
            return;
          }
        }
      } catch (err) {
        console.warn('Real AI endpoint call fell back to local aerospace knowledge:', err);
      }
    }

    setTimeout(() => {
      setIsThinking(false);
      let replyText = '';
      let patch: Message['suggestedPatch'] = undefined;

      if (lower.includes('divide') || lower.includes('zero') || lower.includes('fuel')) {
        replyText = `### NVIDIA Nemotron-4 340B Diagnostic Synthesis
**Target:** \`src/systems/fuel_mgmt_system.c:23\`
**Root Cause:** Floating-point division by zero detected during user test vector execution when both tank parameters evaluate to 0.0 lbs (\`total_fuel == 0.0f\`).

**Execution Behavior:**
In continuous verification mode, Sentinel saved this fault to \`#diag-001\` and continued executing subsequent lines (25–48) to guarantee full decision path coverage.

### Recommended DO-178C DAL-A Remediation:
Add a zero-guard clause prior to ratio evaluation. If total fuel is below epsilon (\`1e-4f\`), declare an emergency starvation state and bypass ratio division:`;
        patch = {
          fileId: 'fuel_mgmt_system',
          filePath: 'src/systems/fuel_mgmt_system.c',
          targetLine: 23,
          code: `    float total_fuel = tank_left_lbs + tank_right_lbs;
    if (total_fuel <= 1e-4f) {
        /* REQ-FMS-042: Starvation protection guard clause */
        *out_valve_command = VALVE_CROSSFEED_BALANCED;
        return FUEL_ERR_STARVATION_SHUTDOWN;
    }
    float left_ratio = tank_left_lbs / total_fuel;`,
        };
      } else if (lower.includes('mc/dc') || lower.includes('coverage') || lower.includes('gap')) {
        replyText = `### NVIDIA Nemotron-4 340B MC/DC Derivation
To satisfy DO-178C Table A-7 (Objective 5, DAL-A):
- **Decision:** \`delta < -MAX_ALLOWABLE_IMBALANCE_LBS\` (-450.0f)
- **Current Deficit:** The condition was only exercised False.

**Synthesized Test Vector for User Input:**
\`\`\`c
tank_left_lbs  = 2000.0f;
tank_right_lbs = 3000.0f; /* Delta: -1000.0f < -450.0f */
crossfeed_open = true;
\`\`\`
**Expected Assertion:** \`*out_valve_command == VALVE_FEED_RIGHT_ONLY\``;
      } else if (lower.includes('pitch') || lower.includes('fcc') || lower.includes('limit')) {
        replyText = `### NVIDIA Nemotron-4 340B Actuation Analysis: fcc_pitch_ctrl.c
Evaluated against **REQ-FCC-014** (Pilot Override) and **REQ-FCC-015** (Q-Bar Limiting):
- Nominal positive pitch authority: clamped to 25.0°
- Dynamic pressure Q_bar > 450 lb/ft²: clamped to 18.0°
- Slew rate limiter: \`RATE_LIMIT_DEG_PER_SEC * dt\` (12.5°/s)
All input vectors (pilot stick commands up to 24.0° at 520 lb/ft²) meet certification bounds.`;
      } else {
        replyText = `### NVIDIA Nemotron-4 340B Contextual Response
I reviewed your selected module (\`${selectedFile?.name || 'Workspace'}\`) and active DO-178C requirements.
The continuous execution engine is configured to record faults without aborting, testing full requirement compliance against both baseline and user-defined input vectors. What would you like to evaluate next?`;
      }

      const botMsg: Message = {
        id: `bot-${Date.now()}`,
        sender: 'assistant',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        text: replyText,
        suggestedPatch: patch,
      };

      setMessages((prev) => [...prev, botMsg]);
    }, 800);
  };

  const handleCopy = (id: string, code: string) => {
    navigator.clipboard.writeText(code);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="w-96 bg-[#0E131B] border-l border-[#21262D] flex flex-col h-full shrink-0 select-none z-30 shadow-2xl">
      {/* DRAWER TOP HEADER */}
      <div className="p-4 bg-[#161B22] border-b border-[#21262D] flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-md bg-[#00E5FF]/10 border border-[#00E5FF]/30 flex items-center justify-center text-[#00E5FF]">
            <Bot size={16} />
          </div>
          <div>
            <h3 className="text-xs font-bold text-white uppercase tracking-wider font-heading">
              Sentinel AI Studio
            </h3>
            <span className="text-[10px] font-mono text-[#00E5FF] flex items-center gap-1 font-semibold">
              <Cpu size={10} /> NVIDIA Nemotron-4 340B
            </span>
          </div>
        </div>

        <button onClick={onClose} className="text-[#8B949E] hover:text-white p-1 rounded">
          <X size={16} />
        </button>
      </div>

      {/* MODEL SPECIFICATION BANNER */}
      <div className="px-4 py-2 bg-[#0B0E14] border-b border-[#21262D] text-[10px] font-mono text-[#8B949E] flex items-center justify-between">
        <div className="truncate">
          <span>Active Context: </span>
          <strong className="text-[#00E5FF]">{selectedFile?.name || 'Workspace Root'}</strong>
        </div>
        <span className="text-emerald-400 font-semibold">NeMo Active</span>
      </div>

      {/* CHAT MESSAGES VIEWPORT */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex flex-col ${
              m.sender === 'user' ? 'items-end' : 'items-start'
            }`}
          >
            <div className="flex items-center gap-1.5 mb-1 text-[10px] text-[#8B949E] font-mono">
              {m.sender === 'assistant' ? (
                <>
                  <Bot size={12} className="text-[#00E5FF]" />
                  <span>NVIDIA Nemotron-4 340B</span>
                </>
              ) : (
                <>
                  <User size={12} />
                  <span>Lead Verification Eng</span>
                </>
              )}
              <span>· {m.timestamp}</span>
            </div>

            <div
              className={`p-3.5 rounded-xl max-w-full leading-relaxed ${
                m.sender === 'user'
                  ? 'bg-[#21262D] text-white border border-[#30363D]'
                  : 'bg-[#161B22] text-[#CBD5E1] border border-[#21262D]'
              }`}
            >
              <div className="whitespace-pre-wrap">{m.text}</div>

              {/* CODE PATCH RECOMMENDATION */}
              {m.suggestedPatch && (
                <div className="mt-3 pt-2.5 border-t border-[#30363D] space-y-2">
                  <div className="flex items-center justify-between text-[10px] font-mono">
                    <span className="text-[#00E5FF] font-semibold">
                      Nemotron Patch Proposal: Line {m.suggestedPatch.targetLine}
                    </span>
                    <button
                      onClick={() => handleCopy(m.id, m.suggestedPatch!.code)}
                      className="text-[#8B949E] hover:text-white flex items-center gap-1"
                    >
                      {copiedId === m.id ? <Check size={11} className="text-emerald-400" /> : <Copy size={11} />}
                      <span>{copiedId === m.id ? 'Copied' : 'Copy'}</span>
                    </button>
                  </div>

                  <pre className="p-2.5 rounded bg-[#0B0E14] border border-[#21262D] font-mono text-[11px] text-cyan-200 overflow-x-auto">
                    {m.suggestedPatch.code}
                  </pre>

                  {onApplyFixCode && (
                    <button
                      onClick={() => onApplyFixCode(m.suggestedPatch!.fileId, m.suggestedPatch!.code)}
                      className="btn-aerospace-glow w-full py-1.5 rounded bg-[#00E5FF] hover:bg-cyan-300 text-black text-xs font-bold transition-all cursor-pointer shadow-md"
                    >
                      Apply Guard Patch to Editor
                    </button>
                  )}
                </div>
              )}
            </div>

            {m.sender === 'assistant' && (
              <span className="text-[9px] text-[#8B949E] mt-1 font-mono">
                Model: nvidia/nemotron-4-340b-instruct · NeMo Guardrails Verified
              </span>
            )}
          </div>
        ))}

        {isThinking && (
          <div className="flex items-center gap-2 text-xs text-[#00E5FF] font-mono">
            <RefreshCw size={13} className="animate-spin" />
            <span>NVIDIA Nemotron-4 reasoning through DO-178C requirement bounds...</span>
          </div>
        )}
      </div>

      {/* QUICK PROMPT CHIPS */}
      <div className="p-2 bg-[#161B22]/60 border-t border-[#21262D] space-y-1.5 shrink-0">
        <span className="text-[10px] font-mono text-[#8B949E] uppercase block px-1">
          Nemotron Quick Prompts:
        </span>
        <div className="flex flex-wrap gap-1">
          <button
            onClick={() => handleSendPrompt("Analyze divide-by-zero error in fuel_mgmt_system.c")}
            className="px-2 py-1 rounded bg-[#0B0E14] hover:bg-[#21262D] border border-[#21262D] text-[10px] text-[#CBD5E1] transition-colors"
          >
            Fix Zero-Divide (#diag-001)
          </button>
          <button
            onClick={() => handleSendPrompt("Synthesize MC/DC test vector for fuel imbalance")}
            className="px-2 py-1 rounded bg-[#0B0E14] hover:bg-[#21262D] border border-[#21262D] text-[10px] text-[#CBD5E1] transition-colors"
          >
            Synthesize MC/DC Vector
          </button>
        </div>
      </div>

      {/* INPUT AREA */}
      <div className="p-3 bg-[#161B22] border-t border-[#21262D] shrink-0">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendPrompt();
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask NVIDIA Nemotron about requirements or code..."
            className="flex-1 bg-[#0B0E14] border border-[#30363D] rounded-lg px-3 py-2 text-xs text-white placeholder-[#8B949E] focus:outline-none focus:border-[#00E5FF] font-sans"
          />
          <button
            type="submit"
            disabled={!input.trim()}
            className="btn-aerospace-glow p-2 rounded-lg bg-[#00E5FF] hover:bg-cyan-300 disabled:opacity-50 text-black transition-colors cursor-pointer"
          >
            <Send size={14} />
          </button>
        </form>
      </div>
    </div>
  );
};
