import React, { useState } from 'react';
import { X, FolderPlus, Upload, CheckCircle2, Check } from 'lucide-react';
import type { Project  } from '../../types';

interface ImportProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onImportComplete: (projectName: string, createdId?: string) => void;
  onLoadSample: (projectId: string) => void;
}

export const ImportProjectModal: React.FC<ImportProjectModalProps> = ({
  isOpen,
  onClose,
  onImportComplete,
  onLoadSample,
}) => {
  const [importMode, setImportMode] = useState<'zip' | 'folder'>('zip');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedFolderFiles, setSelectedFolderFiles] = useState<File[]>([]);
  const [projectName, setProjectName] = useState('My_Aerospace_Project');
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleImport = async () => {
    setIsProcessing(true);
    setErrorMessage(null);
    setStatusMessage('Creating project record...');
    try {
      const res = await fetch('/api/v1/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: projectName, description: 'Imported aerospace verification project.' }),
      });
      if (!res.ok) {
        throw new Error(`Project creation failed with status ${res.status}`);
      }
      const created = await res.json();

      if (importMode === 'zip' && selectedFile) {
        setStatusMessage('Extracting & validating archive safe paths...');
        const base64 = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => {
            const result = reader.result as string;
            resolve(result.includes(',') ? result.split(',')[1] : result);
          };
          reader.onerror = reject;
          reader.readAsDataURL(selectedFile);
        });

        const zipRes = await fetch(`/api/v1/projects/${created.id}/sources/import-zip`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            filename: selectedFile.name,
            archive_base64: base64,
            overwrite: true,
          }),
        });
        if (!zipRes.ok) {
          const errData = await zipRes.json().catch(() => ({}));
          throw new Error(errData?.detail?.message || 'Archive extraction failed');
        }
      } else if (importMode === 'folder' && selectedFolderFiles.length > 0) {
        setStatusMessage(`Reading ${selectedFolderFiles.length} project files...`);
        const allowedExts = new Set(['.c', '.h', '.cpp', '.hpp', '.cc', '.cxx', '.hh', '.hxx', '.cmake', '.mk']);
        const allowedNames = new Set(['cmakelists.txt', 'makefile', 'gnumakefile']);

        const batchFiles: Array<{ filename: string; filepath: string; content: string }> = [];
        for (const file of selectedFolderFiles) {
          const relPath = (file as any).webkitRelativePath || file.name;
          const parts = relPath.split('/');
          // Filter out .git, node_modules, build
          if (parts.some((p: string) => p === '.git' || p === 'node_modules' || p === 'build' || p === 'dist' || p === '.vs')) {
            continue;
          }
          const baseName = file.name.toLowerCase();
          const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
          if (!allowedExts.has(ext) && !allowedNames.has(baseName)) {
            continue;
          }
          const content = await file.text();
          batchFiles.push({
            filename: file.name,
            filepath: relPath,
            content,
          });
        }

        if (batchFiles.length === 0) {
          throw new Error('No valid C/C++ source, header, or build files found in selected folder.');
        }

        setStatusMessage(`Uploading ${batchFiles.length} source modules to backend...`);
        const batchRes = await fetch(`/api/v1/projects/${created.id}/sources/batch`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            files: batchFiles,
            overwrite: true,
          }),
        });
        if (!batchRes.ok) {
          const errData = await batchRes.json().catch(() => ({}));
          throw new Error(errData?.detail?.message || 'Batch upload failed');
        }
      }

      setStatusMessage('Indexing functions & decision AST...');
      await fetch(`/api/v1/projects/${created.id}/analyze`, { method: 'POST' }).catch(() => {});

      setIsProcessing(false);
      onImportComplete(created.name, created.id);
      onClose();
    } catch (err: any) {
      console.error('Import failed:', err);
      setErrorMessage(err.message || 'Import failed');
      setIsProcessing(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-[#161B22] border border-[#30363D] rounded-xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
        <div className="flex items-center justify-between pb-3 border-b border-[#21262D]">
          <div className="flex items-center gap-2">
            <FolderPlus size={18} className="text-[#00E5FF]" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Import Aerospace Project
            </h3>
          </div>
          <button onClick={onClose} className="text-[#8B949E] hover:text-white">
            <X size={16} />
          </button>
        </div>

        {/* MODE TABS: ZIP ARCHIVE vs FOLDER */}
        <div className="flex border-b border-[#21262D] gap-2 pb-2">
          <button
            type="button"
            onClick={() => setImportMode('zip')}
            className={`px-3 py-1.5 text-xs font-semibold rounded transition-colors ${
              importMode === 'zip' ? 'bg-[#00E5FF]/20 text-[#00E5FF] border border-[#00E5FF]/40' : 'text-[#8B949E] hover:text-white'
            }`}
          >
            ZIP Archive
          </button>
          <button
            type="button"
            onClick={() => setImportMode('folder')}
            className={`px-3 py-1.5 text-xs font-semibold rounded transition-colors ${
              importMode === 'folder' ? 'bg-[#00E5FF]/20 text-[#00E5FF] border border-[#00E5FF]/40' : 'text-[#8B949E] hover:text-white'
            }`}
          >
            Directory Folder (webkitdirectory)
          </button>
        </div>

        {/* DRAG AND DROP ARCHIVE OR FOLDER */}
        <div className="border-2 border-dashed border-[#30363D] hover:border-[#00E5FF] rounded-xl p-6 text-center bg-[#0B0E14] transition-colors">
          <Upload size={28} className="mx-auto text-[#00E5FF] mb-2" />
          <div className="text-xs font-semibold text-white">
            {importMode === 'zip' ? 'Select C/C++ Source Archive (ZIP, TAR.GZ)' : 'Select Entire Project Folder'}
          </div>
          <div className="text-[11px] text-[#8B949E] mt-1">
            {importMode === 'zip'
              ? 'Automatically parses headers, functions, and safe relative directory tree'
              : 'Preserves nested folder hierarchy (src/, include/, drivers/) and CMake/Makefiles'}
          </div>

          {importMode === 'zip' ? (
            <label className="mt-3 inline-block px-3 py-1.5 rounded-lg bg-[#21262D] hover:bg-[#30363D] text-xs font-medium text-white cursor-pointer transition-colors">
              Select Archive File
              <input
                type="file"
                accept=".zip,.tar,.gz"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    setSelectedFile(e.target.files[0]);
                    setProjectName(e.target.files[0].name.replace(/\.[^/.]+$/, ''));
                  }
                }}
              />
            </label>
          ) : (
            <label className="mt-3 inline-block px-3 py-1.5 rounded-lg bg-[#21262D] hover:bg-[#30363D] text-xs font-medium text-white cursor-pointer transition-colors">
              Select Directory Folder
              <input
                type="file"
                // @ts-ignore
                webkitdirectory=""
                directory=""
                multiple
                className="hidden"
                onChange={(e) => {
                  if (e.target.files && e.target.files.length > 0) {
                    const fileArr = Array.from(e.target.files);
                    setSelectedFolderFiles(fileArr);
                    const rootDirName = (fileArr[0] as any).webkitRelativePath?.split('/')[0] || 'Project_Folder';
                    setProjectName(rootDirName);
                  }
                }}
              />
            </label>
          )}

          {importMode === 'zip' && selectedFile && (
            <div className="mt-2 text-xs font-mono text-emerald-400">
              Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
            </div>
          )}

          {importMode === 'folder' && selectedFolderFiles.length > 0 && (
            <div className="mt-2 text-xs font-mono text-emerald-400">
              Selected Folder: {selectedFolderFiles.length} files detected
            </div>
          )}
        </div>

        {errorMessage && (
          <div className="p-2.5 rounded bg-rose-950/40 border border-rose-900 text-rose-300 text-xs">
            {errorMessage}
          </div>
        )}

        {statusMessage && (
          <div className="p-2.5 rounded bg-cyan-950/40 border border-cyan-800 text-cyan-300 text-xs">
            {statusMessage}
          </div>
        )}

        <div>
          <label className="text-xs font-semibold text-white block mb-1">
            Project Identifier
          </label>
          <input
            type="text"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            className="w-full bg-[#0B0E14] border border-[#30363D] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-[#00E5FF]"
          />
        </div>

        {/* OR LOAD READY SAMPLE FIXTURE */}
        <div className="pt-2">
          <span className="text-[10px] font-mono text-[#8B949E] uppercase block mb-2">
            Or load verified aerospace sample baseline:
          </span>
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => {
                onLoadSample('proj-x35-fcc');
                onClose();
              }}
              className="p-2.5 rounded-lg bg-[#0B0E14] hover:bg-[#21262D] border border-[#21262D] text-left text-xs text-[#E6EDF3] transition-colors"
            >
              <div className="font-semibold text-white truncate">X-35 Fly-By-Wire FCC</div>
              <div className="text-[10px] text-[#00E5FF] font-mono mt-0.5">DAL-A (42 files)</div>
            </button>
            <button
              onClick={() => {
                onLoadSample('proj-apu-controller');
                onClose();
              }}
              className="p-2.5 rounded-lg bg-[#0B0E14] hover:bg-[#21262D] border border-[#21262D] text-left text-xs text-[#E6EDF3] transition-colors"
            >
              <div className="font-semibold text-white truncate">APU-90 Turbine Controller</div>
              <div className="text-[10px] text-[#00E5FF] font-mono mt-0.5">DAL-B (28 files)</div>
            </button>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#21262D]">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-[#21262D] text-xs font-semibold text-[#8B949E] hover:text-white"
          >
            Cancel
          </button>
          <button
            onClick={handleImport}
            disabled={isProcessing}
            className="px-4 py-2 rounded-lg bg-[#00E5FF] hover:bg-cyan-300 disabled:opacity-50 text-black text-xs font-bold transition-all shadow-[0_0_12px_rgba(0,229,255,0.25)]"
          >
            {isProcessing ? 'Extracting & Indexing...' : 'Import & Index AST'}
          </button>
        </div>
      </div>
    </div>
  );
};
