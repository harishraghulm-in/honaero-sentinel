import React from 'react';
import { 
  LayoutDashboard, FolderGit2, BookOpenCheck, CheckSquare, 
  Activity, PieChart, GitMerge, AlertOctagon, FileSpreadsheet, 
  Sparkles, SlidersHorizontal
} from 'lucide-react';

export type NavTabId = 
  | 'overview' 
  | 'explorer' 
  | 'requirements' 
  | 'test_cases' 
  | 'verification_runs' 
  | 'coverage' 
  | 'traceability' 
  | 'issues' 
  | 'reports' 
  | 'ai_assistant';

interface NavigationRailProps {
  activeTab: NavTabId;
  onTabChange: (tab: NavTabId) => void;
  issuesCount?: number;
  testCount?: number;
  uncoveredReqCount?: number;
}

interface NavItemDef {
  id: NavTabId;
  label: string;
  shortLabel: string;
  icon: React.ReactNode;
  badge?: string | number;
  badgeColor?: string;
}

export const NavigationRail: React.FC<NavigationRailProps> = ({
  activeTab,
  onTabChange,
  issuesCount = 2,
  testCount = 5,
  uncoveredReqCount = 1,
}) => {
  const navItems: NavItemDef[] = [
    {
      id: 'overview',
      label: 'Overview',
      shortLabel: 'Overview',
      icon: <LayoutDashboard size={19} />,
    },
    {
      id: 'explorer',
      label: 'Project Explorer',
      shortLabel: 'Explorer',
      icon: <FolderGit2 size={19} />,
    },
    {
      id: 'requirements',
      label: 'Requirements (DO-178C)',
      shortLabel: 'Reqs',
      icon: <BookOpenCheck size={19} />,
      badge: uncoveredReqCount > 0 ? `${uncoveredReqCount} gap` : undefined,
      badgeColor: 'text-amber-400',
    },
    {
      id: 'test_cases',
      label: 'Test Cases & Vectors',
      shortLabel: 'Tests',
      icon: <CheckSquare size={19} />,
      badge: testCount,
    },
    {
      id: 'verification_runs',
      label: 'Verification Runs',
      shortLabel: 'Live Run',
      icon: <Activity size={19} />,
    },
    {
      id: 'coverage',
      label: 'Coverage Analysis',
      shortLabel: 'Coverage',
      icon: <PieChart size={19} />,
    },
    {
      id: 'traceability',
      label: 'Traceability Matrix',
      shortLabel: 'Trace',
      icon: <GitMerge size={19} />,
    },
    {
      id: 'issues',
      label: 'Issues & Evidence',
      shortLabel: 'Issues',
      icon: <AlertOctagon size={19} />,
      badge: issuesCount > 0 ? issuesCount : undefined,
      badgeColor: 'text-rose-400 font-bold',
    },
    {
      id: 'reports',
      label: 'Verification Reports',
      shortLabel: 'Reports',
      icon: <FileSpreadsheet size={19} />,
    },
    {
      id: 'ai_assistant',
      label: 'Sentinel AI Assistant',
      shortLabel: 'AI Studio',
      icon: <Sparkles size={19} />,
    },
  ];

  return (
    <aside className="w-16 md:w-56 bg-[#0E131B] border-r border-[#21262D] flex flex-col justify-between py-3 select-none shrink-0 z-20">
      <div className="flex flex-col gap-1 px-2">
        <div className="hidden md:block px-3 py-1.5 text-[10px] font-mono tracking-widest text-[#8B949E] uppercase">
          Verification Workspace
        </div>

        {navItems.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`group relative flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-all ${
                isActive
                  ? 'bg-[#161B22] text-[#00E5FF] shadow-sm border border-[#30363D]'
                  : 'text-[#8B949E] hover:text-[#E6EDF3] hover:bg-[#161B22]/60'
              }`}
              title={item.label}
            >
              <div className={`shrink-0 ${isActive ? 'text-[#00E5FF]' : 'group-hover:text-[#CBD5E1]'}`}>
                {item.icon}
              </div>

              <span className="hidden md:inline truncate">{item.label}</span>

              {item.badge !== undefined && (
                <span
                  className={`hidden md:inline-block ml-auto text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#0B0E14] border border-[#21262D] ${
                    item.badgeColor || 'text-[#8B949E]'
                  }`}
                >
                  {item.badge}
                </span>
              )}

              {/* Tooltip on narrow mobile icon bar */}
              <div className="md:hidden absolute left-full ml-2 px-2 py-1 bg-[#161B22] border border-[#30363D] text-[#E6EDF3] text-xs rounded opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50 whitespace-nowrap shadow-xl">
                {item.label}
              </div>
            </button>
          );
        })}
      </div>

      <div className="px-3 pt-3 border-t border-[#21262D] hidden md:block">
        <div className="text-[10px] font-mono text-[#8B949E] uppercase tracking-wider mb-1">
          DO-178C Safety Standard
        </div>
        <div className="text-[11px] text-[#CBD5E1] flex items-center justify-between">
          <span>DAL-A Flight Envelope</span>
          <span className="text-[#00E5FF] font-mono">100% MC/DC</span>
        </div>
      </div>
    </aside>
  );
};
