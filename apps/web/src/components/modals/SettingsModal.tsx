import React, { useState } from 'react';
import { X, Settings, Cpu, Server, ShieldCheck, Check } from 'lucide-react';
import type { Project  } from '../../types';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  activeProject: Project | null;
  isBackendConnected: boolean;
  onToggleBackend: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  activeProject,
  isBackendConnected,
  onToggleBackend,
}) => {
  const [fastApiUrl, setFastApiUrl] = useState('http://localhost:8001/api/v1');
  const [targetArch, setTargetArch] = useState('PowerPC e500v2');
  const [misraStandard, setMisraStandard] = useState('MISRA C:2012 Amendment 3');
  const [saved, setSaved] = useState(false);

  if (!isOpen) return null;

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => {
      setSaved(false);
      onClose();
    }, 800);
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-[#161B22] border border-[#30363D] rounded-xl max-w-lg w-full p-6 space-y-5 shadow-2xl">
        <div className="flex items-center justify-between pb-3 border-b border-[#21262D]">
          <div className="flex items-center gap-2">
            <Settings size={18} className="text-[#00E5FF]" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Toolchain & Verification Configuration
            </h3>
          </div>
          <button onClick={onClose} className="text-[#8B949E] hover:text-white">
            <X size={16} />
          </button>
        </div>

        {/* BACKEND VERIFICATION ENGINE BRIDGE */}
        <div className="p-4 rounded-xl bg-[#0B0E14] border border-[#21262D] space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Server size={15} className="text-[#00E5FF]" />
              <span className="text-xs font-semibold text-white">Execution Engine Source</span>
            </div>
            <button
              onClick={onToggleBackend}
              className={`px-3 py-1 rounded text-xs font-mono font-bold transition-colors ${
                isBackendConnected
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                  : 'bg-[#21262D] text-[#CBD5E1] border border-[#30363D]'
              }`}
            >
              {isBackendConnected ? 'Connected (FastAPI :8000)' : 'Simulator Mode (Default)'}
            </button>
          </div>

          <div>
            <label className="text-[10px] font-mono text-[#8B949E] uppercase block mb-1">
              FastAPI Endpoint URL
            </label>
            <input
              type="text"
              value={fastApiUrl}
              onChange={(e) => setFastApiUrl(e.target.value)}
              className="w-full bg-[#161B22] border border-[#30363D] rounded-md px-3 py-1.5 text-xs font-mono text-white focus:outline-none focus:border-[#00E5FF]"
            />
          </div>
        </div>

        {/* TOOLCHAIN TARGET ARCHITECTURE */}
        <div className="p-4 rounded-xl bg-[#0B0E14] border border-[#21262D] space-y-3">
          <div className="flex items-center gap-2">
            <Cpu size={15} className="text-[#00E5FF]" />
            <span className="text-xs font-semibold text-white">Target Embedded Architecture</span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs">
            <button
              onClick={() => setTargetArch('PowerPC e500v2')}
              className={`p-2 rounded border text-left font-mono ${
                targetArch === 'PowerPC e500v2'
                  ? 'border-[#00E5FF] bg-[#00E5FF]/10 text-white'
                  : 'border-[#21262D] text-[#8B949E]'
              }`}
            >
              PowerPC e500v2 (Clang)
            </button>
            <button
              onClick={() => setTargetArch('ARM Cortex-R5F')}
              className={`p-2 rounded border text-left font-mono ${
                targetArch === 'ARM Cortex-R5F'
                  ? 'border-[#00E5FF] bg-[#00E5FF]/10 text-white'
                  : 'border-[#21262D] text-[#8B949E]'
              }`}
            >
              ARM Cortex-R5F (GCC)
            </button>
          </div>
        </div>

        {/* MISRA STANDARD */}
        <div className="p-4 rounded-xl bg-[#0B0E14] border border-[#21262D] space-y-2">
          <div className="flex items-center gap-2">
            <ShieldCheck size={15} className="text-emerald-400" />
            <span className="text-xs font-semibold text-white">Static Safety Standard</span>
          </div>
          <select
            value={misraStandard}
            onChange={(e) => setMisraStandard(e.target.value)}
            className="w-full bg-[#161B22] border border-[#30363D] rounded-md p-2 text-xs text-white focus:outline-none"
          >
            <option>MISRA C:2012 Amendment 3 (Required)</option>
            <option>DO-178C Tool Qualification Package Sec. 12</option>
            <option>CERT-C Aerospace Secure Coding Rules</option>
          </select>
        </div>

        <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#21262D]">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-[#21262D] text-xs font-semibold text-[#8B949E] hover:text-white"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#00E5FF] hover:bg-cyan-300 text-black text-xs font-bold transition-all shadow-[0_0_12px_rgba(0,229,255,0.25)]"
          >
            {saved ? <Check size={14} /> : null}
            <span>{saved ? 'Saved' : 'Save Toolchain Configuration'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
