import React, { useState, useEffect } from 'react';
import { ShieldCheck, ShieldAlert, ShieldX, Activity, AlertTriangle, CheckCircle2, Lock, FileText, RefreshCw, Eye } from 'lucide-react';
import { api } from '../services/api';
import { useWebSocketEvent } from '../services/websocket';
import { SafetyCapacity, SafetyDecision } from '../types';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { StatusDot } from '../components/ui/StatusDot';

export const SafetyControllerPage: React.FC = () => {
  const [capacity, setCapacity] = useState<SafetyCapacity | null>(null);
  const [decisions, setDecisions] = useState<SafetyDecision[]>([]);
  const [selectedDecision, setSelectedDecision] = useState<SafetyDecision | null>(null);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const [cap, decs] = await Promise.all([
        api.getSafetyCapacity(),
        api.getSafetyDecisions(40),
      ]);
      setCapacity(cap);
      setDecisions(decs);
    } catch (err) {
      console.error('Failed to load safety data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 3000);
    return () => clearInterval(interval);
  }, []);

  useWebSocketEvent('SAFETY_DECISION', (data: any) => {
    setDecisions((prev) => [data, ...prev.slice(0, 39)]);
    loadData();
  });

  if (loading || !capacity) {
    return (
      <div className="flex items-center justify-center h-80 text-text-muted text-sm">
        Polling Safety Controller telemetry and immutable audit logs...
      </div>
    );
  }

  const approvedDecisions = decisions.filter((d) => d.decision === 'APPROVE').length;
  const reducedDecisions = decisions.filter((d) => d.decision === 'REDUCE').length;
  const rejectedDecisions = decisions.filter((d) => d.decision === 'REJECT').length;
  const fallbackDecisions = decisions.filter((d) => d.decision === 'FALLBACK_TO_PROGRESSIVE').length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-text tracking-tight flex items-center gap-2.5">
            <ShieldCheck size={22} className="text-success" />
            Independent Safety Controller — Central Authority
          </h1>
          <p className="text-xs text-text-muted mt-0.5">
            Strict algorithmic zero-abandonment enforcement, capacity bounds, and immutable audit logs
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge
            variant={capacity.is_safe ? 'success' : 'danger'}
            size="md"
            className="font-mono"
          >
            <StatusDot status={capacity.is_safe ? 'SAFE' : 'BLOCKED'} size="sm" pulse={capacity.is_safe} />
            STATUS: {capacity.is_safe ? 'SAFE TO DIAL' : 'DIALING RESTRICTED'}
          </Badge>
        </div>
      </div>

      {/* Safety Capacity & Meter Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <div className="bg-card border border-card-border p-3.5 rounded-xl">
          <span className="text-[10px] text-text-muted uppercase font-semibold">Safe Headroom</span>
          <p className="text-2xl font-bold text-success mt-0.5">{capacity.safe_dialing_capacity} Calls</p>
          <span className="text-[10px] text-text-subtle">Maximum safe new calls</span>
        </div>
        <div className="bg-card border border-card-border p-3.5 rounded-xl">
          <span className="text-[10px] text-text-muted uppercase font-semibold">Available Agents</span>
          <p className="text-2xl font-bold text-text mt-0.5">{capacity.available_agents}</p>
          <span className="text-[10px] text-text-subtle">Unassigned agent capacity</span>
        </div>
        <div className="bg-card border border-card-border p-3.5 rounded-xl">
          <span className="text-[10px] text-text-muted uppercase font-semibold">Reserved Agents</span>
          <p className="text-2xl font-bold text-warning mt-0.5">{capacity.reserved_agents}</p>
          <span className="text-[10px] text-text-subtle">Locked by in-setup calls</span>
        </div>
        <div className="bg-card border border-card-border p-3.5 rounded-xl">
          <span className="text-[10px] text-text-muted uppercase font-semibold">Ringing Calls</span>
          <p className="text-2xl font-bold text-[#38BDF8] mt-0.5">{capacity.ringing_calls}</p>
          <span className="text-[10px] text-text-subtle">Awaiting answer</span>
        </div>
        <div className="bg-card border border-card-border p-3.5 rounded-xl">
          <span className="text-[10px] text-text-muted uppercase font-semibold">Carrier Circuit</span>
          <p className="text-2xl font-bold text-accent mt-0.5">{capacity.circuit_status}</p>
          <span className="text-[10px] text-text-subtle">Upstream protection</span>
        </div>
        <div className="bg-card border border-card-border p-3.5 rounded-xl">
          <span className="text-[10px] text-text-muted uppercase font-semibold">Carrier Health</span>
          <p className="text-2xl font-bold text-success mt-0.5">
            {(capacity.provider_health_score * 100).toFixed(0)}%
          </p>
          <span className="text-[10px] text-text-subtle">Quality score</span>
        </div>
      </div>

      {/* Row 2: Active Constraints & Decision Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Active Constraints */}
        <Card
          title="Active Operational Constraints"
          subtitle="Real-time bounds enforced before any call can dispatch"
          className="lg:col-span-1"
        >
          <div className="space-y-2.5">
            <div className="p-2.5 rounded-lg bg-[#101827] border border-card-border text-xs flex items-start gap-2">
              <Lock size={14} className="text-success mt-0.5 flex-shrink-0" />
              <div>
                <span className="font-semibold text-text block">Zero Borrower Abandonment</span>
                <span className="text-[11px] text-text-muted">
                  Calls strictly forbidden unless an agent is guaranteed available upon borrower pickup.
                </span>
              </div>
            </div>

            <div className="p-2.5 rounded-lg bg-[#101827] border border-card-border text-xs flex items-start gap-2">
              <ShieldCheck size={14} className="text-accent mt-0.5 flex-shrink-0" />
              <div>
                <span className="font-semibold text-text block">In-Flight Headroom Deduction</span>
                <span className="text-[11px] text-text-muted">
                  Counts {capacity.reserved_agents + capacity.dialing_calls + capacity.ringing_calls} in-flight setup calls against available agent headroom.
                </span>
              </div>
            </div>

            {capacity.constraints.map((c, i) => (
              <div
                key={i}
                className="p-2.5 rounded-lg bg-warning/10 border border-warning/30 text-xs flex items-start gap-2"
              >
                <AlertTriangle size={14} className="text-warning mt-0.5 flex-shrink-0" />
                <span className="text-[11px] text-warning font-medium">{c}</span>
              </div>
            ))}
          </div>
        </Card>

        {/* Decisions Statistics */}
        <Card
          title="Safety Decision Audit Metrics"
          subtitle="Distribution of Safety Controller rulings across recent dialing requests"
          className="lg:col-span-2"
        >
          <div className="grid grid-cols-4 gap-3 text-center">
            <div className="bg-[#101827] p-3 rounded-lg border border-card-border">
              <span className="text-[10px] text-text-muted block uppercase font-semibold">Approved</span>
              <p className="text-2xl font-bold text-success mt-1">{approvedDecisions}</p>
              <span className="text-[10px] text-text-subtle">Fully within capacity</span>
            </div>
            <div className="bg-[#101827] p-3 rounded-lg border border-card-border">
              <span className="text-[10px] text-text-muted block uppercase font-semibold">Reduced</span>
              <p className="text-2xl font-bold text-warning mt-1">{reducedDecisions}</p>
              <span className="text-[10px] text-text-subtle">Capped to headroom</span>
            </div>
            <div className="bg-[#101827] p-3 rounded-lg border border-card-border">
              <span className="text-[10px] text-text-muted block uppercase font-semibold">Rejected</span>
              <p className="text-2xl font-bold text-danger mt-1">{rejectedDecisions}</p>
              <span className="text-[10px] text-text-subtle">Zero headroom / Carrier</span>
            </div>
            <div className="bg-[#101827] p-3 rounded-lg border border-card-border">
              <span className="text-[10px] text-text-muted block uppercase font-semibold">Fallback</span>
              <p className="text-2xl font-bold text-accent mt-1">{fallbackDecisions}</p>
              <span className="text-[10px] text-text-subtle">Progressive downgrade</span>
            </div>
          </div>

          <div className="mt-4 p-3 rounded-lg bg-[#101827] border border-card-border text-xs text-text-muted">
            <span className="font-semibold text-text block mb-1">Architectural Invariant:</span>
            Every row in the audit log is immutable and contains the complete DB state snapshot, active provider health, approved/rejected counts, and algorithmic justification.
          </div>
        </Card>
      </div>

      {/* Immutable Decisions Audit Table */}
      <Card title={`Safety Decisions Audit Log (${decisions.length})`}>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-card-border text-text-muted uppercase tracking-wider text-[10px]">
                <th className="py-2.5 px-3">Decision</th>
                <th className="py-2.5 px-3">Requested</th>
                <th className="py-2.5 px-3">Approved</th>
                <th className="py-2.5 px-3">Rejected</th>
                <th className="py-2.5 px-3">Reason & Capacity Context</th>
                <th className="py-2.5 px-3">Timestamp</th>
                <th className="py-2.5 px-3 text-right">Snapshot</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-card-border text-text">
              {decisions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-text-muted">
                    No safety decisions logged yet.
                  </td>
                </tr>
              ) : (
                decisions.map((d) => (
                  <tr key={d.id} className="hover:bg-[#101827] transition-colors">
                    <td className="py-2.5 px-3">
                      <Badge
                        variant={
                          d.decision === 'APPROVE'
                            ? 'success'
                            : d.decision === 'REDUCE'
                            ? 'warning'
                            : d.decision === 'FALLBACK_TO_PROGRESSIVE'
                            ? 'accent'
                            : 'danger'
                        }
                        size="sm"
                      >
                        {d.decision}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] font-semibold">{d.requested_calls}</td>
                    <td className="py-2.5 px-3 font-mono text-[11px] font-bold text-success">
                      {d.approved_calls}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] font-bold text-danger">
                      {d.rejected_calls}
                    </td>
                    <td className="py-2.5 px-3 text-text-muted text-[11px] max-w-md truncate">
                      {d.reason}
                    </td>
                    <td className="py-2.5 px-3 text-[11px] text-text-subtle font-mono">
                      {d.created_at ? new Date(d.created_at).toLocaleTimeString() : 'now'}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <button
                        onClick={() => setSelectedDecision(d)}
                        className="p-1 rounded bg-[#101827] hover:bg-card border border-card-border text-accent transition-colors"
                        title="View Capacity Snapshot"
                      >
                        <Eye size={13} />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Snapshot Modal */}
      {selectedDecision && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedDecision(null)}
          title={`Safety Decision: ${selectedDecision.decision}`}
          subtitle={`Audit Record ID: ${selectedDecision.id}`}
        >
          <div className="space-y-4 text-xs">
            <div>
              <span className="text-text-muted font-medium block mb-1">Reason:</span>
              <p className="p-2.5 bg-[#101827] border border-card-border rounded-lg text-text font-medium leading-relaxed">
                {selectedDecision.reason}
              </p>
            </div>

            <div>
              <span className="text-text-muted font-medium block mb-1">Capacity Snapshot:</span>
              <pre className="p-3 bg-[#101827] border border-card-border rounded-lg text-text font-mono text-[11px] overflow-x-auto">
                {JSON.stringify(selectedDecision.capacity_snapshot, null, 2)}
              </pre>
            </div>

            <div>
              <span className="text-text-muted font-medium block mb-1">Carrier Health Snapshot:</span>
              <pre className="p-3 bg-[#101827] border border-card-border rounded-lg text-text font-mono text-[11px] overflow-x-auto">
                {JSON.stringify(selectedDecision.provider_health_snapshot, null, 2)}
              </pre>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
