
import { useQuery, useMutation } from '@tanstack/react-query';
import Editor from '@monaco-editor/react';
import { ShieldCheck, AlertTriangle, CheckCircle, Upload, Play, Download, Settings, Code, FileText, Beaker } from 'lucide-react';
import { getSources } from './api/sources';
import { getAnalysis } from './api/analysis';
import { getScope } from './api/scope';
import { getTestCases } from './api/tests';
import { getExecution, createExecution } from './api/executions';
import { getCoverage } from './api/coverage';
import { getMcdc } from './api/mcdc';
import { getTraceability } from './api/traceability';
import { getEvidence } from './api/evidence';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const projectId = 'proj-123'; // Hardcoded for demo

const vectorSchema = z.object({
  pressure: z.number().int(),
  altitude: z.number().int(),
});
type TestVector = z.infer<typeof vectorSchema>;
import { useStudioStore } from './store/studio';

export default function App() {
  const { activePane, setActivePane, activeResultTab, setActiveResultTab, executionId, setExecutionId } = useStudioStore();

  // Source Queries
  const { data: sources, isLoading: sourcesLoading } = useQuery({ queryKey: ['sources', projectId], queryFn: () => getSources(projectId), retry: false });
  useQuery({ queryKey: ['analysis', projectId], queryFn: () => getAnalysis(projectId), retry: false });
  useQuery({ queryKey: ['scope', projectId], queryFn: () => getScope(projectId), retry: false });
  useQuery({ queryKey: ['tests', projectId], queryFn: () => getTestCases(projectId), retry: false });
  
  // Execution Polling
  const { data: execution, isError: execError } = useQuery({
    queryKey: ['execution', projectId, executionId],
    queryFn: () => getExecution(projectId, executionId!),
    enabled: !!executionId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'QUEUED' || status === 'BUILDING' || status === 'RUNNING') return 1000;
      return false;
    },
    retry: false
  });

  const isComplete = execution ? ['PASS', 'FAIL', 'ERROR', 'CANCELLED'].includes(execution.status) : false;

  // Results Queries
  const { data: coverage } = useQuery({ queryKey: ['coverage', projectId, executionId], queryFn: () => getCoverage(projectId, executionId!), enabled: isComplete, retry: false });
  const { data: mcdc } = useQuery({ queryKey: ['mcdc', projectId, executionId], queryFn: () => getMcdc(projectId, executionId!), enabled: isComplete, retry: false });
  const { data: traceability } = useQuery({ queryKey: ['traceability', projectId], queryFn: () => getTraceability(projectId), enabled: isComplete, retry: false });
  const { data: evidence } = useQuery({ queryKey: ['evidence', projectId], queryFn: () => getEvidence(projectId), enabled: isComplete, retry: false });

  const executeMutation = useMutation({
    mutationFn: (vector: TestVector) => createExecution(projectId, vector),
    onSuccess: (data) => {
      if (data && data.id) {
        setExecutionId(data.id);
      }
    }
  });

  const { register, handleSubmit, formState: { errors } } = useForm<TestVector>({
    resolver: zodResolver(vectorSchema),
    defaultValues: { pressure: 950, altitude: 5000 },
  });

  const renderStatus = () => {
    if (!executionId && !executeMutation.isPending) return null;
    if (executeMutation.isPending || (execution && ['QUEUED', 'BUILDING', 'RUNNING'].includes(execution.status))) {
      return <div className="text-cyan-500 font-semibold mb-4">Execution Running: {execution?.status || 'QUEUED'}...</div>;
    }
    if (execError || (execution && execution.status === 'ERROR')) return <div className="text-red-500 font-semibold mb-4">Execution Errored. Backend unreachable or failed.</div>;
    if (execution?.status === 'CANCELLED') return <div className="text-yellow-500 font-semibold mb-4">Execution Cancelled</div>;
    if (execution?.status === 'PASS') return <div className="text-green-500 font-semibold mb-4">Execution Passed</div>;
    if (execution?.status === 'FAIL') return <div className="text-red-500 font-semibold mb-4">Execution Failed</div>;
    
    // Fallback UI when API is missing but execution ID is set
    return <div className="text-yellow-500 font-semibold mb-4">Awaiting backend connection for execution ID: {executionId}</div>;
  };

  return (
    <div className="flex h-screen bg-slate-900 text-slate-200">
      <div className="w-16 border-r border-slate-800 flex flex-col items-center py-4 bg-slate-950 space-y-6">
        <ShieldCheck className="w-8 h-8 text-cyan-500 mb-4" />
        <button onClick={() => setActivePane('source')} className={`p-2 rounded ${activePane==='source'?'bg-cyan-900 text-cyan-400':'text-slate-400 hover:text-slate-200'}`}><Code size={20}/></button>
        <button onClick={() => setActivePane('analyze')} className={`p-2 rounded ${activePane==='analyze'?'bg-cyan-900 text-cyan-400':'text-slate-400 hover:text-slate-200'}`}><Settings size={20}/></button>
        <button onClick={() => setActivePane('tests')} className={`p-2 rounded ${activePane==='tests'?'bg-cyan-900 text-cyan-400':'text-slate-400 hover:text-slate-200'}`}><Beaker size={20}/></button>
        <button onClick={() => setActivePane('results')} className={`p-2 rounded ${activePane==='results'?'bg-cyan-900 text-cyan-400':'text-slate-400 hover:text-slate-200'}`}><FileText size={20}/></button>
      </div>

      <div className="flex-1 flex flex-col border-r border-slate-800">
        <div className="p-4 border-b border-slate-800 font-semibold bg-slate-950 capitalize">{activePane} Pane</div>
        <div className="flex-1 p-4 overflow-auto">
          {activePane === 'source' && (
             <div className="space-y-4 h-full flex flex-col">
               <h2 className="text-lg font-semibold">Source Retrieval & Upload</h2>
               <button className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 px-4 py-2 rounded w-max"><Upload size={16}/> Upload Source</button>
               {sourcesLoading ? <p>Loading sources...</p> : !sources ? <p className="text-slate-500">No sources found or backend unavailable.</p> : null}
               <div className="flex-1 bg-slate-950 rounded border border-slate-800">
                 <Editor height="100%" defaultLanguage="c" theme="vs-dark" value="int cabin_pressure_control(int pressure, int altitude) { ... }" options={{ minimap: { enabled: false } }} />
               </div>
             </div>
          )}

          {activePane === 'analyze' && (
             <div className="space-y-6">
               <h2 className="text-lg font-semibold">Analyze & Scope</h2>
               <button className="bg-cyan-600 hover:bg-cyan-500 px-4 py-2 rounded text-sm font-semibold">Run Analysis</button>
               <div className="bg-slate-800 p-4 rounded">
                 <h3 className="font-semibold mb-2">Analysis Results & Function Selection</h3>
                 <p className="text-sm text-slate-400">Available functions for scope:</p>
                 <label className="flex items-center gap-2 mt-2"><input type="checkbox" defaultChecked /> cabin_pressure_control</label>
               </div>
               <div className="bg-slate-800 p-4 rounded">
                 <h3 className="font-semibold mb-2">Dependency & Stub Configuration</h3>
                 <p className="text-sm text-slate-400">No external dependencies detected.</p>
                 <button className="mt-2 bg-slate-700 hover:bg-slate-600 px-3 py-1 rounded text-sm">Add Stub</button>
               </div>
             </div>
          )}

          {activePane === 'tests' && (
             <div className="space-y-6">
               <h2 className="text-lg font-semibold">Test Suites & Execution</h2>
               <form className="bg-slate-800 p-4 rounded" onSubmit={handleSubmit((d) => executeMutation.mutate(d))}>
                 <h3 className="font-semibold mb-4">Create Test Vector</h3>
                 <div className="grid grid-cols-2 gap-4 mb-4">
                   <div><label className="block text-xs mb-1 text-slate-400">Pressure</label><input type="number" {...register('pressure', { valueAsNumber: true })} className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1" />{errors.pressure && <p className="text-red-400 text-xs mt-1">{errors.pressure.message}</p>}</div>
                   <div><label className="block text-xs mb-1 text-slate-400">Altitude</label><input type="number" {...register('altitude', { valueAsNumber: true })} className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1" />{errors.altitude && <p className="text-red-400 text-xs mt-1">{errors.altitude.message}</p>}</div>
                 </div>
                 <button type="submit" disabled={executeMutation.isPending || (execution && ['QUEUED','BUILDING','RUNNING'].includes(execution.status))} className="bg-cyan-600 hover:bg-cyan-500 px-4 py-2 rounded text-sm font-semibold disabled:opacity-50 flex items-center gap-2">
                   <Play size={16} /> Run Execution
                 </button>
               </form>
               <div className="bg-slate-800 p-4 rounded">
                 <h3 className="font-semibold mb-2 text-cyan-400 flex items-center gap-2"><AlertTriangle size={16} /> Gap Advisor</h3>
                 <p className="text-sm text-slate-300">Suggested candidate vector to improve MC/DC:</p>
                 <p className="text-xs bg-slate-950 p-2 mt-2 rounded font-mono">pressure = 850, altitude = 5000</p>
               </div>
             </div>
          )}

          {activePane === 'results' && (
             <div className="space-y-4">
               {renderStatus()}
               <div className="flex border-b border-slate-800 text-sm mb-4">
                 {['coverage', 'mcdc', 'traceability', 'evidence'].map(tab => (
                   <button key={tab} onClick={() => setActiveResultTab(tab)} className={`px-4 py-2 capitalize ${activeResultTab === tab ? 'border-b-2 border-cyan-500 text-cyan-400' : 'text-slate-400 hover:text-slate-200'}`}>
                     {tab === 'mcdc' ? 'MC/DC' : tab}
                   </button>
                 ))}
               </div>
               
               {activeResultTab === 'coverage' && (
                 <div className="bg-slate-800 p-4 rounded">
                   <h3 className="font-semibold mb-2">Statement Coverage</h3>
                   {coverage ? <p>Statement: {coverage.statement}%</p> : <p className="text-slate-500">Awaiting backend data...</p>}
                 </div>
               )}
               {activeResultTab === 'mcdc' && (
                 <div className="bg-slate-800 p-4 rounded">
                   <h3 className="font-semibold mb-2">MC/DC Condition Table</h3>
                   {mcdc ? <pre className="text-xs">{JSON.stringify(mcdc, null, 2)}</pre> : <p className="text-slate-500">Awaiting backend data...</p>}
                 </div>
               )}
               {activeResultTab === 'traceability' && (
                 <div className="bg-slate-800 p-4 rounded">
                   <h3 className="font-semibold mb-2">Traceability View</h3>
                   {traceability ? <pre className="text-xs">{JSON.stringify(traceability, null, 2)}</pre> : <p className="text-slate-500">Awaiting backend data...</p>}
                 </div>
               )}
               {activeResultTab === 'evidence' && (
                 <div className="bg-slate-800 p-4 rounded">
                   <div className="flex justify-between items-center mb-4">
                     <h3 className="font-semibold">Evidence Package</h3>
                     <button className="flex items-center gap-1 bg-slate-700 hover:bg-slate-600 px-3 py-1 rounded text-sm"><Download size={14} /> Export Evidence</button>
                   </div>
                   <div className="flex items-center gap-2">
                     <span className="text-sm text-slate-400">Freshness:</span>
                     {evidence?.freshness === 'CURRENT' && <span className="px-2 py-1 rounded text-xs font-semibold bg-green-900/50 text-green-400 flex items-center gap-1"><CheckCircle size={12} /> CURRENT</span>}
                     {evidence?.freshness === 'STALE' && <span className="px-2 py-1 rounded text-xs font-semibold bg-yellow-900/50 text-yellow-400 flex items-center gap-1"><AlertTriangle size={12} /> STALE</span>}
                     {evidence?.freshness === 'INVALIDATED' && <span className="px-2 py-1 rounded text-xs font-semibold bg-red-900/50 text-red-400 flex items-center gap-1"><AlertTriangle size={12} /> INVALIDATED</span>}
                     {!evidence && <span className="px-2 py-1 rounded text-xs font-semibold bg-slate-800 text-slate-400">UNKNOWN</span>}
                   </div>
                   {!evidence && <p className="text-slate-500 mt-2 text-sm">Awaiting actual backend evidence data...</p>}
                 </div>
               )}
             </div>
          )}
        </div>
      </div>
    </div>
  );
}
