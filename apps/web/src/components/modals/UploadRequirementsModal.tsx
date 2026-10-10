import React, { useState } from 'react';
import { X, FileUp, Upload, CheckCircle2, Check, FileText } from 'lucide-react';

interface UploadRequirementsModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId?: string;
  onUploadSuccess: (docName: string, reqCount: number) => void;
}

export const UploadRequirementsModal: React.FC<UploadRequirementsModalProps> = ({
  isOpen,
  onClose,
  projectId,
  onUploadSuccess,
}) => {
  const [docFile, setDocFile] = useState<File | null>(null);
  const [docName, setDocName] = useState<string>('');
  const [isParsing, setIsParsing] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [standard, setStandard] = useState('DO-178C Level A');

  if (!isOpen) return null;

  const handleParse = async () => {
    if (!docFile && !docName) {
      setErrorMsg('Please select a specification document file.');
      return;
    }
    setIsParsing(true);
    setErrorMsg(null);

    if (projectId && docFile) {
      try {
        const ext = docFile.name.toLowerCase().split('.').pop() || 'txt';
        let content = '';

        if (ext === 'pdf' || ext === 'docx') {
          // Send base64 encoded binary
          content = await new Promise<string>((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
              const res = reader.result as string;
              resolve(res.includes(',') ? res.split(',')[1] : res);
            };
            reader.onerror = reject;
            reader.readAsDataURL(docFile);
          });
        } else {
          // Plain text / markdown / csv / json
          content = await docFile.text();
        }

        // 1. Upload requirement document to project
        const docUploadRes = await fetch(`/api/v1/projects/${projectId}/requirements/documents`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            filename: docFile.name,
            file_type: ext,
            content: content,
            revision: '1.0',
          }),
        });

        if (!docUploadRes.ok) {
          const errData = await docUploadRes.json().catch(() => ({}));
          throw new Error(errData?.detail?.message || `Document upload failed (status ${docUploadRes.status})`);
        }
        const createdDoc = await docUploadRes.json();

        // 2. Extract structured requirements from document
        const extractRes = await fetch(`/api/v1/projects/${projectId}/requirements/extract?document_id=${createdDoc.id}`, {
          method: 'POST',
        });

        if (extractRes.ok) {
          const data = await extractRes.json();
          setIsParsing(false);
          const count = Array.isArray(data) ? data.length : 0;
          onUploadSuccess(docFile.name, count);
          onClose();
          return;
        } else {
          const errData = await extractRes.json().catch(() => ({}));
          throw new Error(errData?.detail?.message || 'Requirement extraction failed');
        }
      } catch (err: any) {
        console.error('Requirements parsing error:', err);
        setErrorMsg(err.message || 'Failed to parse requirements document.');
        setIsParsing(false);
        return;
      }
    }

    setIsParsing(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-[#161B22] border border-[#30363D] rounded-xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
        <div className="flex items-center justify-between pb-3 border-b border-[#21262D]">
          <div className="flex items-center gap-2">
            <FileUp size={18} className="text-[#00E5FF]" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Ingest DO-178C Requirements Document
            </h3>
          </div>
          <button onClick={onClose} className="text-[#8B949E] hover:text-white">
            <X size={16} />
          </button>
        </div>

        <p className="text-xs text-[#8B949E] leading-relaxed">
          Upload PDF, DOCX, or XML specification documents. Sentinel parses structured requirements (`REQ-***`), safety bounds, and links them directly to AST code functions.
        </p>

        {/* DROPZONE */}
        <div className="border-2 border-dashed border-[#30363D] hover:border-[#00E5FF] rounded-xl p-6 text-center bg-[#0B0E14] transition-colors">
          <FileText size={28} className="mx-auto text-[#00E5FF] mb-2" />
          <div className="text-xs font-semibold text-white">
            Drop PDF or DOCX Specification
          </div>
          <div className="text-[11px] text-[#8B949E] mt-1">
            Accepts SysReq, ICD, and Software Requirements Specifications (SRS)
          </div>

          <label className="mt-3 inline-block px-3 py-1.5 rounded-lg bg-[#21262D] hover:bg-[#30363D] text-xs font-medium text-white cursor-pointer transition-colors">
            Choose Document File
            <input
              type="file"
              accept=".pdf,.docx,.xml,.txt,.md,.json,.csv"
              className="hidden"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  setDocFile(e.target.files[0]);
                  setDocName(e.target.files[0].name);
                  setErrorMsg(null);
                }
              }}
            />
          </label>

          <div className="mt-2 text-xs font-mono text-emerald-400">
            Selected: {docName || 'None selected'}
          </div>
          {errorMsg && (
            <div className="mt-2 text-xs font-mono text-rose-400">
              {errorMsg}
            </div>
          )}
        </div>

        <div>
          <label className="text-xs font-semibold text-white block mb-1">
            Target Certification Standard
          </label>
          <select
            value={standard}
            onChange={(e) => setStandard(e.target.value)}
            className="w-full bg-[#0B0E14] border border-[#30363D] rounded-lg p-2 text-xs text-white focus:outline-none"
          >
            <option>DO-178C Level A (Flight Critical)</option>
            <option>DO-178C Level B (Hazardous / Severe)</option>
            <option>DO-254 Hardware / FPGA Interface</option>
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
            onClick={handleParse}
            disabled={isParsing}
            className="px-4 py-2 rounded-lg bg-[#00E5FF] hover:bg-cyan-300 disabled:opacity-50 text-black text-xs font-bold transition-all shadow-[0_0_12px_rgba(0,229,255,0.25)]"
          >
            {isParsing ? 'Extracting Requirements...' : 'Ingest & Link Traceability'}
          </button>
        </div>
      </div>
    </div>
  );
};
