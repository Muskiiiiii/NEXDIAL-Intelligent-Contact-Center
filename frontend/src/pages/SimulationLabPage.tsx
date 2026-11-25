import React, { useState, useEffect } from 'react';
import {
  FlaskConical,
  Play,
  Pause,
  RotateCcw,
  StepForward,
  Sliders,
  Radio,
  Zap,
  Activity,
  PhoneCall,
  CheckCircle2,
  Clock,
  Sparkles,
} from 'lucide-react';
import { api } from '../services/api';
import { useWebSocketEvent } from '../services/websocket';
import { SimulationState, DialingMode } from '../types';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { StatusDot } from '../components/ui/StatusDot';

export const SimulationLabPage: React.FC = () => {
  const [state, setState] = useState<SimulationState | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedScenario, setSelectedScenario] = useState<string>('SCENARIO_B');

  // Interactive config state
  const [numAgents, setNumAgents] = useState(25);
  const [numBorrowers, setNumBorrowers] = useState(150);
  const [answerRate, setAnswerRate] = useState(0.5);
  const [avgTalkTime, setAvgTalkTime] = useState(90);
  const [dialingMode, setDialingMode] = useState<DialingMode>('PROGRESSIVE');
  const [providerId, setProviderId] = useState('PROVIDER_A');
  const [tickSpeed, setTickSpeed] = useState(1000);

  const [liveLog, setLiveLog] = useState<Array<{ id: string; time: string; text: string; type: string }>>([]);

  const loadState = async () => {
    try {
      const data = await api.getSimulationState();
      setState(data);
      if (data.config) {
        setNumAgents(data.config.num_agents);
        setNumBorrowers(data.config.num_borrowers);
        setAnswerRate(data.config.answer_rate);
        setAvgTalkTime(data.config.average_talk_time_sec);
        setDialingMode(data.config.dialing_mode);
        setProviderId(data.config.provider_id);
        setTickSpeed(data.config.tick_speed_ms);
        setSelectedScenario(data.active_scenario_code || 'SCENARIO_B');
      }
    } catch (e) {
      console.error('Failed to load simulation state:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadState();
  }, []);

  useWebSocketEvent('SIMULATION_TICK', (data: any) => {
    if (data.state) {
      setState(data.state);
    }
    const logItem = {
      id: Math.random().toString(),
      time: new Date().toLocaleTimeString(),
      text: `Tick #${data.tick}: Answer rate ${(data.answer_rate * 100).toFixed(0)}% • Allocator dispatched`,
      type: 'tick',
    };
    setLiveLog((prev) => [logItem, ...prev.slice(0, 30)]);
  });

  useWebSocketEvent('SAFETY_DECISION', (data: any) => {
    const logItem = {
      id: Math.random().toString(),
      time: new Date().toLocaleTimeString(),
      text: `Safety Controller: ${data.decision} (Approved ${data.approved_calls}, Rejected ${data.rejected_calls})`,
      type: data.decision === 'APPROVE' ? 'success' : 'warning',
    };
    setLiveLog((prev) => [logItem, ...prev.slice(0, 30)]);
  });

  const handleStart = async () => {
    await api.startSimulation({
      num_agents: numAgents,
      num_borrowers: numBorrowers,
      answer_rate: answerRate,
      average_talk_time_sec: avgTalkTime,
      dialing_mode: dialingMode,
      provider_id: providerId,
      tick_speed_ms: tickSpeed,
      scenario_code: selectedScenario,
    });
    loadState();
  };

  const handlePause = async () => {
    await api.pauseSimulation();
    loadState();
  };

  const handleResume = async () => {
    await api.resumeSimulation();
    loadState();
  };

  const handleReset = async () => {
    await api.resetSimulation();
    setLiveLog([]);
    loadState();
  };

  const handleStep = async () => {
    await api.stepSimulation();
    loadState();
  };

  const handlePresetSelect = async (code: string) => {
    setSelectedScenario(code);
    await api.applyPreset(code);
    loadState();
  };

  const handleConfigSync = async () => {
    await api.updateSimulationConfig({
      num_agents: numAgents,
      num_borrowers: numBorrowers,
      answer_rate: answerRate,
      average_talk_time_sec: avgTalkTime,
      dialing_mode: dialingMode,
      provider_id: providerId,
      tick_speed_ms: tickSpeed,
    });
  };

  if (loading || !state) {
    return <div className="text-center py-12 text-xs text-text-muted">Loading Simulation Lab...</div>;
  }

  const isRunning = state.is_running && !state.is_paused;

  return (
    <div className="space-y-6">
      {/* Header & Controls Strip */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-text tracking-tight flex items-center gap-2.5">
            <FlaskConical size={22} className="text-accent" />
            Interactive Simulation Lab
          </h1>
          <p className="text-xs text-text-muted mt-0.5">
            Full discrete-event simulation executing real backend business logic, allocation, and safety enforcement
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          {!state.is_running || state.is_paused ? (
            <button
              onClick={state.is_paused ? handleResume : handleStart}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-success hover:bg-success/90 text-white text-xs font-semibold shadow-glow-success transition-all"
            >
              <Play size={14} />
              <span>{state.is_paused ? 'Resume Simulation' : 'Run Simulation'}</span>
            </button>
          ) : (
            <button
              onClick={handlePause}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-warning hover:bg-warning/90 text-[#090D18] text-xs font-bold transition-all"
            >
              <Pause size={14} />
              <span>Pause</span>
            </button>
          )}

          <button
            onClick={handleStep}
            disabled={isRunning}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-card border border-card-border hover:border-[#2C3E5F] text-xs text-text transition-colors disabled:opacity-40"
            title="Step Forward 1 Tick"
          >
            <StepForward size={14} />
            <span>Step</span>
          </button>

          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-card border border-card-border hover:border-danger/40 text-xs text-danger transition-colors"
            title="Reset Simulation State"
          >
            <RotateCcw size={14} />
            <span>Reset</span>
          </button>
        </div>
      </div>

      {/* Preset Scenarios Strip */}
      <Card title="Preset Benchmark Scenarios (Section 15 Requirements)">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            {
              code: 'SCENARIO_A',
              name: 'Scenario A: Cold Outbound',
              desc: 'Answer Rate: 20% • Avg Talk Time: 120s • Predictive',
              accent: '#7C6CFF',
            },
            {
              code: 'SCENARIO_B',
              name: 'Scenario B: Standard Balanced',
              desc: 'Answer Rate: 50% • Avg Talk Time: 90s • Progressive',
              accent: '#20C997',
            },
            {
              code: 'SCENARIO_C',
              name: 'Scenario C: Warm Campaign',
              desc: 'Answer Rate: 70% • Avg Talk Time: 180s • Predictive',
              accent: '#F5B942',
            },
            {
              code: 'SCENARIO_D',
              name: 'Scenario D: Dynamic Volatility',
              desc: 'Dynamic fluctuating answer rate (20% to 75%) and talk times',
              accent: '#FF5C70',
            },
          ].map((sc) => (
            <button
              key={sc.code}
              onClick={() => handlePresetSelect(sc.code)}
              className={`p-3 rounded-xl border text-left transition-all relative overflow-hidden ${
                selectedScenario === sc.code
                  ? 'bg-[#151F30] border-accent shadow-glow-accent'
                  : 'bg-[#101827] border-card-border hover:border-[#2C3E5F]'
              }`}
            >
              <div
                className="absolute top-0 left-0 bottom-0 w-1"
                style={{ backgroundColor: sc.accent }}
              />
              <span className="font-semibold text-xs text-text block pl-1.5">{sc.name}</span>
              <span className="text-[11px] text-text-muted mt-1 block pl-1.5">{sc.desc}</span>
            </button>
          ))}
        </div>
      </Card>

      {/* Real-time Config Sliders & Live Telemetry */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Sliders Console */}
        <Card
          title="Interactive Simulator Parameters"
          subtitle="Adjust simulation dynamics in real-time"
          className="lg:col-span-2"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-text-muted font-medium">Borrower Answer Rate:</span>
                <span className="font-mono text-success font-bold">{(answerRate * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.05"
                max="1.0"
                step="0.05"
                value={answerRate}
                onChange={(e) => {
                  setAnswerRate(parseFloat(e.target.value));
                  handleConfigSync();
                }}
                className="w-full accent-success bg-[#101827] h-2 rounded-lg cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between mb-1">
                <span className="text-text-muted font-medium">Avg Talk Time:</span>
                <span className="font-mono text-accent font-bold">{avgTalkTime}s</span>
              </div>
              <input
                type="range"
                min="10"
                max="300"
                step="10"
                value={avgTalkTime}
                onChange={(e) => {
                  setAvgTalkTime(parseInt(e.target.value));
                  handleConfigSync();
                }}
                className="w-full accent-accent bg-[#101827] h-2 rounded-lg cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between mb-1">
                <span className="text-text-muted font-medium">Dialing Mode:</span>
                <span className="font-mono text-text font-bold">{dialingMode}</span>
              </div>
              <select
                value={dialingMode}
                onChange={(e) => {
                  setDialingMode(e.target.value as DialingMode);
                  handleConfigSync();
                }}
                className="w-full p-2 bg-[#101827] border border-card-border rounded-lg text-text focus:outline-none focus:border-accent"
              >
                <option value="PROGRESSIVE">Progressive (1:1 Ratio)</option>
                <option value="PREDICTIVE">Predictive Pacing Engine</option>
              </select>
            </div>

            <div>
              <div className="flex justify-between mb-1">
                <span className="text-text-muted font-medium">Provider Selection:</span>
                <span className="font-mono text-text font-bold">{providerId}</span>
              </div>
              <select
                value={providerId}
                onChange={(e) => {
                  setProviderId(e.target.value);
                  handleConfigSync();
                }}
                className="w-full p-2 bg-[#101827] border border-card-border rounded-lg text-text focus:outline-none focus:border-accent"
              >
                <option value="PROVIDER_A">Provider A (High Speed / Low Latency)</option>
                <option value="PROVIDER_B">Provider B (Simulated Latency & Jitter)</option>
              </select>
            </div>

            <div>
              <div className="flex justify-between mb-1">
                <span className="text-text-muted font-medium">Active Agent Pool:</span>
                <span className="font-mono text-text font-bold">{numAgents} Agents</span>
              </div>
              <input
                type="range"
                min="5"
                max="100"
                step="5"
                value={numAgents}
                onChange={(e) => {
                  setNumAgents(parseInt(e.target.value));
                  handleConfigSync();
                }}
                className="w-full accent-accent bg-[#101827] h-2 rounded-lg cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between mb-1">
                <span className="text-text-muted font-medium">Simulation Tick Speed:</span>
                <span className="font-mono text-text font-bold">{tickSpeed}ms</span>
              </div>
              <input
                type="range"
                min="200"
                max="3000"
                step="100"
                value={tickSpeed}
                onChange={(e) => {
                  setTickSpeed(parseInt(e.target.value));
                  handleConfigSync();
                }}
                className="w-full accent-accent bg-[#101827] h-2 rounded-lg cursor-pointer"
              />
            </div>
          </div>
        </Card>

        {/* Live Event Stream Terminal */}
        <Card title={`Simulation Stream (#${state.ticks_elapsed} Ticks)`}>
          <div className="h-64 overflow-y-auto space-y-1.5 font-mono text-[11px] pr-1">
            {liveLog.length === 0 ? (
              <p className="text-text-subtle py-10 text-center italic">
                Simulation idle. Click "Run Simulation" or "Step" to begin.
              </p>
            ) : (
              liveLog.map((log) => (
                <div
                  key={log.id}
                  className="p-1.5 rounded bg-[#101827] border border-card-border flex items-start justify-between text-xs"
                >
                  <span
                    className={
                      log.type === 'success'
                        ? 'text-success'
                        : log.type === 'warning'
                        ? 'text-warning'
                        : 'text-text-muted'
                    }
                  >
                    {log.text}
                  </span>
                  <span className="text-[10px] text-text-subtle ml-2 whitespace-nowrap">{log.time}</span>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>
    </div>
  );
};
