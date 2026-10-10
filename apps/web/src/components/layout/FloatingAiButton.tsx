import React from 'react';
import { Sparkles, Bot, MessageSquare } from 'lucide-react';

interface FloatingAiButtonProps {
  isOpen: boolean;
  onToggle: () => void;
  unreadCount?: number;
}

export const FloatingAiButton: React.FC<FloatingAiButtonProps> = ({
  isOpen,
  onToggle,
  unreadCount = 1,
}) => {
  return (
    <div className="fixed bottom-10 right-6 z-40 select-none">
      <div className="relative group">
        {/* RADAR BEACON PULSE RING */}
        <div className="absolute inset-0 rounded-full bg-[#00E5FF] opacity-30 animate-radar pointer-events-none" />

        {/* FLOATING ACTION BUTTON */}
        <button
          onClick={onToggle}
          aria-label="Open Sentinel AI Assistant (NVIDIA Nemotron)"
          className={`relative flex items-center justify-center w-13 h-13 rounded-full text-black shadow-2xl transition-all cursor-pointer ${
            isOpen
              ? 'bg-[#E6EDF3] hover:bg-white text-black ring-2 ring-[#00E5FF]'
              : 'bg-[#00E5FF] hover:bg-cyan-300 btn-aerospace-glow btn-shimmer'
          }`}
          style={{ width: '52px', height: '52px' }}
        >
          {isOpen ? (
            <MessageSquare size={20} className="text-black" />
          ) : (
            <div className="relative flex items-center justify-center">
              <Sparkles size={22} className="text-black" />
              <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-cyan-500"></span>
              </span>
            </div>
          )}
        </button>

        {/* HOVER TOOLTIP / BADGE */}
        <div className="absolute right-full mr-3 top-1/2 -translate-y-1/2 pointer-events-none opacity-0 group-hover:opacity-100 transition-all duration-200 whitespace-nowrap">
          <div className="bg-[#161B22] border border-[#30363D] px-3 py-1.5 rounded-lg shadow-xl text-left">
            <div className="flex items-center gap-1.5 text-xs font-bold text-white font-heading">
              <Bot size={13} className="text-[#00E5FF]" />
              <span>Sentinel AI Assistant</span>
            </div>
            <div className="text-[10px] font-mono text-[#00E5FF] mt-0.5">
              NVIDIA Nemotron-4 340B Active
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
