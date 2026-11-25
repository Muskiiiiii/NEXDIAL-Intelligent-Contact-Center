import React, { useState } from 'react';
import { Settings as SettingsIcon, Save, Database, Shield, Server, FileDown, CheckCircle2 } from 'lucide-react';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';

export const SettingsPage: React.FC = () => {
  const [safetyBuffer, setSafetyBuffer] = useState(0.15);
  const [circuitThreshold, setCircuitThreshold] = useState(5);
  const [recoveryTimeout, setRecoveryTimeout] = useState(10);
  const [maxPredictiveRatio, setMaxPredictiveRatio] = useState(2.5);
  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-text tracking-tight flex items-center gap-2.5">
            <SettingsIcon size={20} className="text-accent" />
            Platform & Safety Engine Settings
          </h1>
          <p className="text-xs text-text-muted mt-0.5">
            Configure safety thresholds, carrier circuit policies, and environment constants
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Form Settings */}
        <Card
          title="Safety & Pacing Policy Configurations"
          subtitle="Enforced globally across all active dialing campaigns"
          className="lg:col-span-2"
        >
          <form onSubmit={handleSave} className="space-y-4 text-xs">
            <div>
              <label className="block text-text-muted mb-1 font-medium">
                Default Safety Buffer Ratio ({Math.round(safetyBuffer * 100)}%)
              </label>
              <input
                type="range"
                min="0.05"
                max="0.4"
                step="0.05"
                value={safetyBuffer}
                onChange={(e) => setSafetyBuffer(parseFloat(e.target.value))}
                className="w-full accent-accent bg-[#101827] h-2 rounded-lg cursor-pointer"
              />
              <span className="text-[10px] text-text-subtle mt-1 block">
                Conservative deduction applied to raw predictive dial requirements.
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-text-muted mb-1 font-medium">Circuit Breaker Failure Threshold</label>
                <input
                  type="number"
                  min="2"
                  max="15"
                  value={circuitThreshold}
                  onChange={(e) => setCircuitThreshold(parseInt(e.target.value) || 5)}
                  className="w-full p-2 bg-[#101827] border border-card-border rounded-lg text-text focus:outline-none focus:border-accent"
                />
              </div>

              <div>
                <label className="block text-text-muted mb-1 font-medium">Circuit Recovery Cooldown (sec)</label>
                <input
                  type="number"
                  min="3"
                  max="60"
                  value={recoveryTimeout}
                  onChange={(e) => setRecoveryTimeout(parseInt(e.target.value) || 10)}
                  className="w-full p-2 bg-[#101827] border border-card-border rounded-lg text-text focus:outline-none focus:border-accent"
                />
              </div>
            </div>

            <div>
              <label className="block text-text-muted mb-1 font-medium">Max Predictive Multiplier Cap</label>
              <input
                type="number"
                step="0.1"
                min="1.0"
                max="4.0"
                value={maxPredictiveRatio}
                onChange={(e) => setMaxPredictiveRatio(parseFloat(e.target.value) || 2.5)}
                className="w-full p-2 bg-[#101827] border border-card-border rounded-lg text-text focus:outline-none focus:border-accent"
              />
              <span className="text-[10px] text-text-subtle mt-1 block">
                Hard upper ceiling: maximum simultaneous dials allowed per available agent (2.5x).
              </span>
            </div>

            <div className="pt-3 border-t border-card-border flex items-center justify-between">
              {saved && (
                <span className="text-success text-xs flex items-center gap-1 font-medium">
                  <CheckCircle2 size={14} /> Settings updated successfully!
                </span>
              )}
              {!saved && <div />}
              <button
                type="submit"
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white font-semibold text-xs shadow-glow-accent transition-all"
              >
                <Save size={13} />
                <span>Save Configurations</span>
              </button>
            </div>
          </form>
        </Card>

        {/* System & Architecture Info */}
        <div className="space-y-4">
          <Card title="System Environment & Persistence">
            <div className="space-y-2.5 text-xs">
              <div className="flex justify-between py-1 border-b border-card-border">
                <span className="text-text-muted">Environment</span>
                <span className="font-mono text-accent font-semibold">SIMULATION</span>
              </div>
              <div className="flex justify-between py-1 border-b border-card-border">
                <span className="text-text-muted">Database Mode</span>
                <span className="font-mono text-text font-semibold">SQLite WAL (Concurrent)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-card-border">
                <span className="text-text-muted">PostgreSQL Driver</span>
                <span className="font-mono text-text font-semibold">asyncpg / psycopg2</span>
              </div>
              <div className="flex justify-between py-1 border-b border-card-border">
                <span className="text-text-muted">Concurrency Model</span>
                <span className="font-mono text-success font-semibold">Row Conditional Locking</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-text-muted">WebSocket Status</span>
                <span className="font-mono text-success font-semibold">ACTIVE (Port 8000)</span>
              </div>
            </div>
          </Card>

          <Card title="System Export & Audits">
            <p className="text-xs text-text-muted mb-3 leading-relaxed">
              Export complete immutable audit trail, safety controller rulings, and call telemetry for review.
            </p>
            <button
              onClick={() => {
                window.open('/api/v1/safety/decisions', '_blank');
              }}
              className="w-full py-2 px-3 rounded-lg bg-[#101827] hover:bg-[#1E2C44] border border-card-border text-xs text-text flex items-center justify-center gap-2 font-medium transition-colors"
            >
              <FileDown size={14} />
              <span>Export Safety Audit JSON</span>
            </button>
          </Card>
        </div>
      </div>
    </div>
  );
};
