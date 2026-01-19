import { useState, useEffect, useCallback, useMemo } from 'react';
import { Play, RotateCcw, Square, CheckCircle2, XCircle, Clock, Server, Monitor, Smartphone, Database, ChevronRight, AlertCircle, Zap, TestTube2 } from 'lucide-react';
import { containerEntryFlow } from './flowDefinition';
import { FlowExecutor } from './executor';
import type { ExecutionState, Stage, StageResult, StageStatus, SystemType, LogEntry, ExecutionMode } from './types';

// System icons and colors
const systemConfig: Record<SystemType, { icon: typeof Server; color: string; bg: string; label: string }> = {
  backend: { icon: Server, color: 'text-blue-400', bg: 'bg-blue-500/20', label: 'Backend API' },
  frontend: { icon: Monitor, color: 'text-green-400', bg: 'bg-green-500/20', label: 'Vue Frontend' },
  telegram: { icon: Smartphone, color: 'text-purple-400', bg: 'bg-purple-500/20', label: 'Telegram App' },
  database: { icon: Database, color: 'text-orange-400', bg: 'bg-orange-500/20', label: 'Database' },
};

const statusConfig: Record<StageStatus, { color: string; bg: string; border: string }> = {
  pending: { color: 'text-slate-400', bg: 'bg-slate-800', border: 'border-slate-600' },
  running: { color: 'text-blue-400', bg: 'bg-blue-900/50', border: 'border-blue-500' },
  passed: { color: 'text-emerald-400', bg: 'bg-emerald-900/30', border: 'border-emerald-500' },
  failed: { color: 'text-red-400', bg: 'bg-red-900/30', border: 'border-red-500' },
  skipped: { color: 'text-slate-500', bg: 'bg-slate-800/50', border: 'border-slate-700' },
};

export default function App() {
  const [executor] = useState(() => new FlowExecutor(containerEntryFlow));
  const [state, setState] = useState<ExecutionState>(executor.getState());
  const [selectedStage, setSelectedStage] = useState<string | null>(null);
  const [mode, setMode] = useState<ExecutionMode>(executor.getMode());

  useEffect(() => {
    const unsubscribe = executor.subscribe(setState);
    return unsubscribe;
  }, [executor]);

  const handleRun = useCallback(async () => {
    executor.reset();
    setSelectedStage(null);
    await executor.execute();
  }, [executor]);

  const handleReset = useCallback(() => {
    executor.reset();
    setSelectedStage(null);
  }, [executor]);

  const handleStop = useCallback(() => {
    executor.abort();
  }, [executor]);

  const handleModeToggle = useCallback(() => {
    const newMode = mode === 'simulation' ? 'real' : 'simulation';
    setMode(newMode);
    executor.setMode(newMode);
  }, [mode, executor]);

  const completedStages = useMemo(() => {
    return containerEntryFlow.stages.filter(s => {
      const result = state.results.get(s.id);
      return result?.status === 'passed' || result?.status === 'failed';
    }).length;
  }, [state.results]);

  const progress = (completedStages / containerEntryFlow.stages.length) * 100;

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
              <span className="text-3xl">🔄</span>
              FlowTest
              <span className="text-sm font-normal text-slate-400 ml-2">Business Flow Testing Platform</span>
            </h1>
          </div>
          <div className="flex items-center gap-3">
            {/* Mode Toggle */}
            <button
              onClick={handleModeToggle}
              disabled={state.status === 'running'}
              className={`
                flex items-center gap-2 px-3 py-2 rounded-lg font-medium transition-all
                ${mode === 'simulation'
                  ? 'bg-purple-600/20 text-purple-400 border border-purple-500/50 hover:bg-purple-600/30'
                  : 'bg-amber-600/20 text-amber-400 border border-amber-500/50 hover:bg-amber-600/30'
                }
                disabled:opacity-50 disabled:cursor-not-allowed
              `}
              title={mode === 'simulation' ? 'Switch to Real Mode' : 'Switch to Simulation Mode'}
            >
              {mode === 'simulation' ? (
                <>
                  <TestTube2 size={18} />
                  <span>Simulation</span>
                </>
              ) : (
                <>
                  <Zap size={18} />
                  <span>Real Mode</span>
                </>
              )}
            </button>

            {state.status === 'running' ? (
              <button
                onClick={handleStop}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg font-medium transition-colors"
              >
                <Square size={18} />
                Stop
              </button>
            ) : (
              <>
                <button
                  onClick={handleReset}
                  disabled={state.status === 'idle'}
                  className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg font-medium transition-colors"
                >
                  <RotateCcw size={18} />
                  Reset
                </button>
                <button
                  onClick={handleRun}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium transition-colors"
                >
                  <Play size={18} />
                  Run Flow
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Flow Info Bar */}
      <div className="bg-slate-800/50 border-b border-slate-700 px-6 py-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">{containerEntryFlow.name}</h2>
            <p className="text-sm text-slate-400">{containerEntryFlow.description}</p>
          </div>
          <div className="flex items-center gap-6 text-sm">
            <div>
              <span className="text-slate-400">Stages:</span>
              <span className="ml-2 font-medium">{containerEntryFlow.stages.length}</span>
            </div>
            <div>
              <span className="text-slate-400">Status:</span>
              <span className={`ml-2 font-medium ${
                state.status === 'passed' ? 'text-emerald-400' :
                state.status === 'failed' ? 'text-red-400' :
                state.status === 'running' ? 'text-blue-400' : 'text-slate-400'
              }`}>
                {state.status === 'idle' ? 'Ready' : state.status.charAt(0).toUpperCase() + state.status.slice(1)}
              </span>
            </div>
            {state.startTime && (
              <div>
                <span className="text-slate-400">Duration:</span>
                <span className="ml-2 font-medium">
                  {((state.endTime || Date.now()) - state.startTime) / 1000}s
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Progress Bar */}
        {state.status !== 'idle' && (
          <div className="mt-3">
            <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${
                  state.status === 'passed' ? 'bg-emerald-500' :
                  state.status === 'failed' ? 'bg-red-500' : 'bg-blue-500'
                }`}
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="mt-1 text-xs text-slate-400">
              {completedStages} / {containerEntryFlow.stages.length} stages completed
            </div>
          </div>
        )}
      </div>

      {/* Main Content */}
      <div className="flex h-[calc(100vh-180px)]">
        {/* Flow Graph - Left Side */}
        <div className="w-1/2 p-6 border-r border-slate-700 overflow-auto">
          <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Flow Execution</h3>
          <div className="space-y-3">
            {containerEntryFlow.stages.map((stage, index) => (
              <StageNode
                key={stage.id}
                stage={stage}
                result={state.results.get(stage.id)}
                isCurrent={state.currentStage === stage.id}
                isSelected={selectedStage === stage.id}
                onClick={() => setSelectedStage(stage.id)}
                showConnector={index < containerEntryFlow.stages.length - 1}
              />
            ))}
          </div>
        </div>

        {/* Right Side - Details + Log */}
        <div className="w-1/2 flex flex-col">
          {/* Stage Details - Top Right */}
          <div className="flex-1 p-6 border-b border-slate-700 overflow-auto">
            <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
              {selectedStage ? 'Stage Details' : 'Select a stage to view details'}
            </h3>
            {selectedStage ? (
              <StageDetails
                stage={containerEntryFlow.stages.find(s => s.id === selectedStage)!}
                result={state.results.get(selectedStage)}
              />
            ) : (
              <div className="text-slate-500 text-center py-12">
                <AlertCircle size={48} className="mx-auto mb-3 opacity-50" />
                <p>Click on a stage to view its details</p>
              </div>
            )}
          </div>

          {/* Live Log - Bottom Right */}
          <div className="h-64 p-4 bg-slate-950 overflow-auto">
            <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Live Log</h3>
            <div className="font-mono text-xs space-y-1">
              {state.logs.length === 0 ? (
                <div className="text-slate-600">Waiting for execution...</div>
              ) : (
                state.logs.map((log, i) => (
                  <LogLine key={i} log={log} />
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Stage Node Component
function StageNode({
  stage,
  result,
  isCurrent,
  isSelected,
  onClick,
  showConnector,
}: {
  stage: Stage;
  result?: StageResult;
  isCurrent: boolean;
  isSelected: boolean;
  onClick: () => void;
  showConnector: boolean;
}) {
  const status: StageStatus = result?.status || 'pending';
  const config = statusConfig[status];
  const system = systemConfig[stage.system];
  const SystemIcon = system.icon;

  return (
    <div className="relative">
      <div
        onClick={onClick}
        className={`
          relative p-4 rounded-lg border-2 cursor-pointer transition-all
          ${config.bg} ${config.border}
          ${isSelected ? 'ring-2 ring-blue-500 ring-offset-2 ring-offset-slate-900' : ''}
          ${isCurrent ? 'animate-pulse-glow' : ''}
          hover:brightness-110
        `}
      >
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3">
            {/* Status Icon */}
            <div className={`mt-0.5 ${config.color}`}>
              {status === 'passed' && <CheckCircle2 size={20} />}
              {status === 'failed' && <XCircle size={20} />}
              {status === 'running' && <Clock size={20} className="animate-spin" />}
              {status === 'pending' && <div className="w-5 h-5 rounded-full border-2 border-current" />}
            </div>

            {/* Stage Info */}
            <div>
              <div className="font-semibold text-white">{stage.name}</div>
              <div className="text-sm text-slate-400 mt-0.5">{stage.description}</div>

              {/* Actions/Verifications counts */}
              {result && (
                <div className="flex items-center gap-4 mt-2 text-xs">
                  <span className="text-slate-400">
                    Actions: {result.actions.filter(a => a.success).length}/{stage.actions.length}
                  </span>
                  <span className={result.verifications.every(v => v.passed) ? 'text-emerald-400' : 'text-red-400'}>
                    Checks: {result.verifications.filter(v => v.passed).length}/{stage.verifications.length}
                  </span>
                  {result.endTime && result.startTime && (
                    <span className="text-slate-500">
                      {((result.endTime - result.startTime) / 1000).toFixed(1)}s
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* System Badge */}
          <div className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs ${system.bg} ${system.color}`}>
            <SystemIcon size={14} />
            {system.label}
          </div>
        </div>

        {/* Expand indicator */}
        <ChevronRight
          size={16}
          className={`absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 transition-transform ${
            isSelected ? 'rotate-90' : ''
          }`}
        />
      </div>

      {/* Connector line */}
      {showConnector && (
        <div className="flex justify-center py-1">
          <div className={`w-0.5 h-4 ${isCurrent ? 'bg-blue-500 animate-pulse' : 'bg-slate-600'}`} />
        </div>
      )}
    </div>
  );
}

// Stage Details Component
function StageDetails({
  stage,
  result,
}: {
  stage: Stage;
  result?: StageResult;
}) {
  const system = systemConfig[stage.system];
  const SystemIcon = system.icon;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <SystemIcon size={20} className={system.color} />
          <h4 className="text-lg font-semibold text-white">{stage.name}</h4>
        </div>
        <p className="text-slate-400">{stage.description}</p>
      </div>

      {/* Actions */}
      <div>
        <h5 className="text-sm font-semibold text-slate-300 mb-2">Actions</h5>
        <div className="space-y-2">
          {stage.actions.map((action, i) => {
            const actionResult = result?.actions[i];
            return (
              <div
                key={i}
                className={`flex items-start gap-2 p-2 rounded ${
                  actionResult?.success ? 'bg-emerald-900/20' : actionResult ? 'bg-red-900/20' : 'bg-slate-800'
                }`}
              >
                {actionResult ? (
                  actionResult.success ? (
                    <CheckCircle2 size={16} className="text-emerald-400 mt-0.5 flex-shrink-0" />
                  ) : (
                    <XCircle size={16} className="text-red-400 mt-0.5 flex-shrink-0" />
                  )
                ) : (
                  <div className="w-4 h-4 rounded-full border border-slate-600 mt-0.5 flex-shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-slate-200 truncate">{action.description}</div>
                  {actionResult?.details && (
                    <div className="text-xs text-slate-500 mt-0.5">{actionResult.details}</div>
                  )}
                </div>
                {actionResult && (
                  <span className="text-xs text-slate-500">{actionResult.duration}ms</span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Verifications */}
      <div>
        <h5 className="text-sm font-semibold text-slate-300 mb-2">Verifications</h5>
        <div className="space-y-2">
          {stage.verifications.map((verification, i) => {
            const verifyResult = result?.verifications[i];
            return (
              <div
                key={i}
                className={`flex items-start gap-2 p-2 rounded ${
                  verifyResult?.passed ? 'bg-emerald-900/20' : verifyResult ? 'bg-red-900/20' : 'bg-slate-800'
                }`}
              >
                {verifyResult ? (
                  verifyResult.passed ? (
                    <CheckCircle2 size={16} className="text-emerald-400 mt-0.5 flex-shrink-0" />
                  ) : (
                    <XCircle size={16} className="text-red-400 mt-0.5 flex-shrink-0" />
                  )
                ) : (
                  <div className="w-4 h-4 rounded-full border border-slate-600 mt-0.5 flex-shrink-0" />
                )}
                <span className="text-sm text-slate-200">{verification.description}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Captured Data */}
      {result?.captured && Object.keys(result.captured).length > 0 && (
        <div>
          <h5 className="text-sm font-semibold text-slate-300 mb-2">Captured Data</h5>
          <div className="bg-slate-800 rounded p-3 font-mono text-sm">
            {Object.entries(result.captured).map(([key, value]) => (
              <div key={key} className="flex gap-2">
                <span className="text-blue-400">{key}:</span>
                <span className="text-emerald-400">{String(value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Screenshot placeholder */}
      {result?.screenshot && (
        <div>
          <h5 className="text-sm font-semibold text-slate-300 mb-2">Screenshot</h5>
          <div className="bg-slate-800 rounded-lg p-8 text-center border-2 border-dashed border-slate-600">
            <Monitor size={48} className="mx-auto mb-2 text-slate-500" />
            <p className="text-slate-500 text-sm">Screenshot captured</p>
            <p className="text-slate-600 text-xs mt-1">{result.screenshot}</p>
          </div>
        </div>
      )}
    </div>
  );
}

// Log Line Component
function LogLine({ log }: { log: LogEntry }) {
  const time = new Date(log.timestamp).toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  const levelColors = {
    info: 'text-slate-400',
    success: 'text-emerald-400',
    error: 'text-red-400',
    warning: 'text-amber-400',
  };

  return (
    <div className={`flex gap-2 ${levelColors[log.level]}`}>
      <span className="text-slate-600">[{time}]</span>
      <span>{log.message}</span>
    </div>
  );
}
