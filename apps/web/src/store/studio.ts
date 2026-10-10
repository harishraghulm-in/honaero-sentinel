import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface EditorSelection {
  line: number;
  column: number;
}

interface StudioState {
  activePane: string;
  setActivePane: (pane: string) => void;
  bottomPanelOpen: boolean;
  setBottomPanelOpen: (open: boolean) => void;
  bottomPanelTab: string;
  setBottomPanelTab: (tab: string) => void;
  executionId: string | null;
  setExecutionId: (id: string | null) => void;
  projectId: string | null;
  setProjectId: (id: string | null) => void;
  selectedSourceId: string | null;
  setSelectedSourceId: (id: string | null) => void;
  selectedFunctionId: string | null;
  setSelectedFunctionId: (id: string | null) => void;
  selectedTestSuiteId: string | null;
  setSelectedTestSuiteId: (id: string | null) => void;
  editorSelection: EditorSelection | null;
  setEditorSelection: (selection: EditorSelection | null) => void;
}

export const useStudioStore = create<StudioState>()(
  persist(
    (set) => ({
      activePane: 'explorer',
      setActivePane: (pane) => set({ activePane: pane }),
      bottomPanelOpen: true,
      setBottomPanelOpen: (open) => set({ bottomPanelOpen: open }),
      bottomPanelTab: 'problems',
      setBottomPanelTab: (tab) => set({ bottomPanelTab: tab, bottomPanelOpen: true }),
      executionId: null,
      setExecutionId: (id) => set({ executionId: id }),
      projectId: null,
      setProjectId: (id) => set({ projectId: id, selectedSourceId: null, executionId: null, selectedFunctionId: null, selectedTestSuiteId: null, editorSelection: null }),
      selectedSourceId: null,
      setSelectedSourceId: (id) => set({ selectedSourceId: id, selectedFunctionId: null, editorSelection: null }),
      selectedFunctionId: null,
      setSelectedFunctionId: (id) => set({ selectedFunctionId: id }),
      selectedTestSuiteId: null,
      setSelectedTestSuiteId: (id) => set({ selectedTestSuiteId: id }),
      editorSelection: null,
      setEditorSelection: (selection) => set({ editorSelection: selection }),
    }),
    {
      name: 'studio-storage-ide-v1',
    }
  )
);
