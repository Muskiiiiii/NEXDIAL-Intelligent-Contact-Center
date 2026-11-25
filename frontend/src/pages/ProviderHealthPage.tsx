import React, { useState, useEffect } from 'react';
import { Server, Activity, ShieldCheck, AlertTriangle, RotateCcw, Clock, CheckCircle2, Zap } from 'lucide-react';
import { api } from '../services/api';
import { ProviderHealth } from '../types';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { StatusDot } from '../components/ui/StatusDot';

export const ProviderHealthPage: React.FC = () => {
  const [providers, setProviders] = useState<ProviderHealth[]>([]);
  const [loading, setLoading] = useState(true);

  const loadProviders = async () => {
    try {
      const data = await api.getProviders();
      setProviders(data);
    } catch (err) {
      console.error('Failed to load providers:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProviders();
    const interval = setInterval(loadProviders, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleResetCircuit = async (providerId: string) => {
    try {
      await api.resetProviderCircuit(providerId);
      loadProviders();
    } catch (err: any) {
      alert(`Error resetting circuit: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-text tracking-tight flex items-center gap-2.5">
            <Server size={20} className="text-accent" />
            Telecom Provider Interface & Circuit Breakers
          </h1>
          <p className="text-xs text-text-muted mt-0.5">
            Upstream carrier telemetry, circuit breaker states, and idempotent event processing
          </p>
        </div>
      </div>

      {/* Provider Cards Comparison */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {providers.map((p) => {
          const cb = p.circuit_breaker;
          const isA = p.provider_id === 'PROVIDER_A';

          return (
            <Card key={p.provider_id} className="relative">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-semibold text-text">{p.provider_id}</h3>
                    <Badge variant={isA ? 'accent' : 'warning'} size="sm">
                      {isA ? 'Primary Tier (Low Latency)' : 'Secondary Tier (Simulated Jitter)'}
                    </Badge>
                  </div>
                  <span className="text-[10px] text-text-muted font-mono mt-0.5 block">
                    Target setup: {isA ? '40-120ms' : '250-700ms'} • Fail threshold: {cb.failure_threshold}
                  </span>
                </div>

                <Badge
                  variant={
                    cb.state === 'CLOSED'
                      ? 'success'
                      : cb.state === 'HALF_OPEN'
                      ? 'warning'
                      : 'danger'
                  }
                  size="md"
                >
                  <StatusDot status={cb.state} size="sm" pulse={cb.state !== 'CLOSED'} />
                  CIRCUIT: {cb.state}
                </Badge>
              </div>

              {/* Health and Latency Strip */}
              <div className="grid grid-cols-3 gap-2 mt-5 text-center text-xs">
                <div className="bg-[#101827] p-2.5 rounded-lg border border-card-border">
                  <span className="text-[10px] text-text-muted uppercase block font-semibold">Quality Score</span>
                  <p className="text-xl font-bold text-success mt-0.5">
                    {(p.health_score * 100).toFixed(0)}%
                  </p>
                </div>
                <div className="bg-[#101827] p-2.5 rounded-lg border border-card-border">
                  <span className="text-[10px] text-text-muted uppercase block font-semibold">Avg Latency</span>
                  <p className="text-xl font-bold text-accent mt-0.5">{p.avg_latency_ms.toFixed(0)}ms</p>
                </div>
                <div className="bg-[#101827] p-2.5 rounded-lg border border-card-border">
                  <span className="text-[10px] text-text-muted uppercase block font-semibold">Error Rate</span>
                  <p
                    className={`text-xl font-bold mt-0.5 ${
                      cb.failure_rate > 0.1 ? 'text-danger' : 'text-text'
                    }`}
                  >
                    {(cb.failure_rate * 100).toFixed(1)}%
                  </p>
                </div>
              </div>

              {/* Circuit Breaker Detailed Metrics */}
              <div className="mt-4 pt-3 border-t border-card-border space-y-2 text-xs">
                <div className="flex justify-between items-center text-text-muted">
                  <span>Total Calls Routed:</span>
                  <span className="font-mono text-text font-semibold">{cb.total_calls}</span>
                </div>
                <div className="flex justify-between items-center text-text-muted">
                  <span>Successful Handshakes:</span>
                  <span className="font-mono text-success font-semibold">{cb.total_successes}</span>
                </div>
                <div className="flex justify-between items-center text-text-muted">
                  <span>Consecutive Failures:</span>
                  <span className="font-mono text-danger font-semibold">{cb.consecutive_failures} / {cb.failure_threshold}</span>
                </div>
                <div className="flex justify-between items-center text-text-muted">
                  <span>Simulated Outage Mode:</span>
                  <span className="font-mono font-semibold">
                    {p.outage_mode ? (
                      <span className="text-danger">ACTIVE OUTAGE</span>
                    ) : (
                      <span className="text-success">HEALTHY</span>
                    )}
                  </span>
                </div>
              </div>

              {/* Actions */}
              <div className="mt-4 pt-3 border-t border-card-border flex items-center justify-between">
                <span className="text-[10px] text-text-subtle font-mono">
                  State timer: {cb.seconds_since_state_change}s ago
                </span>
                {cb.state !== 'CLOSED' && (
                  <button
                    onClick={() => handleResetCircuit(p.provider_id)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent/20 hover:bg-accent/30 text-accent border border-accent/40 text-xs font-semibold transition-colors"
                  >
                    <RotateCcw size={12} />
                    <span>Reset Circuit Breaker</span>
                  </button>
                )}
              </div>
            </Card>
          );
        })}
      </div>

      {/* Circuit Breaker Behavior Explainer */}
      <Card title="Circuit Breaker Architecture & Fallback Semantics">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-text-muted">
          <div className="p-3 bg-[#101827] rounded-lg border border-card-border">
            <span className="text-success font-semibold flex items-center gap-1.5 mb-1">
              <CheckCircle2 size={14} /> CLOSED (Normal)
            </span>
            <p className="text-[11px] leading-relaxed">
              Traffic flows normally. Failures increment consecutive error counters. Latencies are exponentially smoothed.
            </p>
          </div>
          <div className="p-3 bg-[#101827] rounded-lg border border-card-border">
            <span className="text-danger font-semibold flex items-center gap-1.5 mb-1">
              <AlertTriangle size={14} /> OPEN (Tripped)
            </span>
            <p className="text-[11px] leading-relaxed">
              Consecutive failures exceed threshold. Carrier protected: all new calls rejected instantly without touching network.
            </p>
          </div>
          <div className="p-3 bg-[#101827] rounded-lg border border-card-border">
            <span className="text-warning font-semibold flex items-center gap-1.5 mb-1">
              <Activity size={14} /> HALF_OPEN (Trial)
            </span>
            <p className="text-[11px] leading-relaxed">
              Cooldown timer elapses. Sends single probe call. Success resets to CLOSED; failure immediately re-trips to OPEN.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};
