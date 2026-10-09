import { create } from 'zustand';

interface StudioState {
  activePane: string;
  setActivePane: (pane: string) => void;
  activeResultTab: string;
  setActiveResultTab: (tab: string) => void;
  executionId: string | null;
  setExecutionId: (id: string | null) => void;
}

export const useStudioStore = create<StudioState>((set) => ({
  activePane: 'source',
  setActivePane: (pane) => set({ activePane: pane }),
  activeResultTab: 'coverage',
  setActiveResultTab: (tab) => set({ activeResultTab: tab }),
  executionId: null,
  setExecutionId: (id) => set({ executionId: id }),
}));
