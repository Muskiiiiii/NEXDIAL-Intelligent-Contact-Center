import React, { useState } from 'react';
import {
  ZapOff,
  Flame,
  AlertOctagon,
  Users,
  Copy,
  Clock,
  TrendingDown,
  Activity,
  Layers,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
} from 'lucide-react';
import { api } from '../services/api';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';

export const FailureInjectionPage: React.FC = () => {
  const [activeResult, setActiveResult] = useState<any | null>(null);
  const [injecting, setInjecting] = useState<string | null>(null);

  const handleInject = async (type: string, payload?: Record<string, any>) => {
    setInjecting(type);
    try {
      const res = await api.injectFailure(type, payload);
      setActiveResult(res);
    } catch (err: any) {
      alert(`Injection error: ${err.message}`);
    } finally {
      setInjecting(null);
    }
  };

  const failureScenarios = [
    {
      id: 'worker_crash',
      title: '1. Distributed Worker Crash',
      desc: 'Abruptly terminates worker process while holding active job leases. Tests heartbeat loss and stale reservation recovery.',
      icon: ZapOff,
      accent: '#FF5C70',
      payload: { worker_name: 'Dialer-Worker-1' },
    },
    {
      id: 'provider_outage',
      title: '2. Upstream Carrier Outage',
      desc: 'Simulates complete 503 carrier outage on Provider A. Tests circuit breaker trip to OPEN and automatic Safety Controller blocking.',
      icon: Flame,
      accent: '#FF5C70',
      payload: { provider_id: 'PROVIDER_A' },
    },
    {
      id: 'agent_drop',
      title: '3. Sudden Agent Availability Drop',
      desc: 'Simulates 15 agents abruptly going offline (e.g. network disconnect). Tests instant capacity recalculation.',
      icon: Users,
      accent: '#F5B942',
      payload: { count: 15 },
    },
    {
      id: 'duplicate_event',
      title: '4. Duplicate Carrier Webhook Event',
      desc: 'Dispatches identical event payload twice to verify idempotency filtering and prevent duplicate agent allocation.',
      icon: Copy,
      accent: '#7C6CFF',
      payload: {},
    },
    {
      id: 'out_of_order_event',
      title: '5. Out-of-Order Late Carrier Event',
      desc: 'Dispatches late RINGING event after a call is already COMPLETED. Tests monotonic state progression and regression prevention.',
      icon: Clock,
      accent: '#7C6CFF',
      payload: {},
    },
    {
      id: 'answer_rate_plunge',
      title: '6. Answer Rate Plunge (70% → 10%)',
      desc: 'Simulates sudden borrower pickup collapse. Tests predictive pacing variance detection and progressive fallback.',
      icon: TrendingDown,
      accent: '#F5B942',
      payload: {},
    },
    {
      id: 'latency_spike',
      title: '7. Carrier Latency Spike (2500ms)',
      desc: 'Spikes carrier network handshake to 2500ms. Tests pacing setup window expansion and in-flight throttling.',
      icon: Activity,
      accent: '#F5B942',
      payload: { provider_id: 'PROVIDER_B' },
    },
    {
      id: 'concurrency_race',
      title: '8. Concurrent Allocation Race (10 Workers)',
      desc: 'Fires 10 simultaneous asynchronous workers attempting to reserve the exact same agent. Proves zero double-allocations.',
      icon: Layers,
      accent: '#20C997',
      payload: {},
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-text tracking-tight flex items-center gap-2.5">
            <AlertOctagon size={22} className="text-danger" />
            Failure Injection & Chaos Engineering Center
          </h1>
          <p className="text-xs text-text-muted mt-0.5">
            Subject the contact center to carrier outages, worker crashes, race conditions, and event anomalies
          </p>
        </div>
      </div>

      {/* Grid of 8 Failure Injection Scenarios */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {failureScenarios.map((sc) => {
          const Icon = sc.icon;
          const isCurrent = injecting === sc.id;

          return (
            <Card
              key={sc.id}
              className="flex flex-col justify-between hover:border-[#2C3E5F] transition-all relative overflow-hidden"
            >
              <div
                className="absolute top-0 left-0 right-0 h-1"
                style={{ backgroundColor: sc.accent }}
              />
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <div
                    className="w-7 h-7 rounded-lg flex items-center justify-center"
                    style={{ backgroundColor: `${sc.accent}18`, color: sc.accent }}
                  >
                    <Icon size={15} />
                  </div>
                  <h3 className="font-semibold text-xs text-text">{sc.title}</h3>
                </div>
                <p className="text-[11px] text-text-muted leading-relaxed mb-4">{sc.desc}</p>
              </div>

              <button
                onClick={() => handleInject(sc.id, sc.payload)}
                disabled={isCurrent}
                className="w-full py-1.5 px-3 rounded-lg bg-[#101827] hover:bg-[#1E2C44] border border-card-border text-xs font-semibold text-text flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50"
              >
                <ZapOff size={13} className={isCurrent ? 'animate-spin' : ''} />
                <span>{isCurrent ? 'Injecting...' : 'Trigger Scenario'}</span>
              </button>
            </Card>
          );
        })}
      </div>

      {/* Real-time System Response Panel */}
      {activeResult && (
        <Card
          title="Chaos Test Execution & System Response"
          subtitle="Real-time reaction recorded by the Safety Controller and Event Processor"
          action={
            <button
              onClick={() => setActiveResult(null)}
              className="text-xs text-text-muted hover:text-text"
            >
              Dismiss
            </button>
          }
        >
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="bg-[#101827] p-3 rounded-lg border border-card-border">
                <span className="text-[10px] text-text-muted block uppercase font-semibold">
                  Failure Injected
                </span>
                <p className="text-sm font-bold text-danger mt-1">
                  {activeResult.failure_injected}
                </p>
              </div>

              <div className="bg-[#101827] p-3 rounded-lg border border-card-border">
                <span className="text-[10px] text-text-muted block uppercase font-semibold">
                  Safety Controller Action
                </span>
                <p className="text-sm font-bold text-warning mt-1">
                  {activeResult.safety_controller_action || 'Capacity Revalidated'}
                </p>
              </div>

              <div className="bg-[#101827] p-3 rounded-lg border border-card-border">
                <span className="text-[10px] text-text-muted block uppercase font-semibold">
                  Recovery Status
                </span>
                <p className="text-sm font-bold text-success mt-1">
                  {activeResult.recovery_status || 'Automated reconciliation ready'}
                </p>
              </div>
            </div>

            <div className="bg-[#101827] p-3.5 rounded-lg border border-card-border">
              <span className="text-text-muted font-semibold block mb-1">
                Verified System Behavior:
              </span>
              <p className="text-text text-[11px] leading-relaxed">
                {activeResult.system_response}
              </p>

              {activeResult.details && (
                <pre className="mt-3 p-2.5 bg-[#090D18] border border-card-border rounded-lg text-accent font-mono text-[10px] overflow-x-auto">
                  {JSON.stringify(activeResult.details, null, 2)}
                </pre>
              )}
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};
