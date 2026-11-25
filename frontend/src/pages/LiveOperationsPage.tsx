import React, { useState, useEffect } from 'react';
import { Radio, PhoneCall, PhoneOff, UserCheck, ShieldCheck, Clock, Search, RefreshCw, Filter } from 'lucide-react';
import { api } from '../services/api';
import { useWebSocketEvent } from '../services/websocket';
import { Call, SafetyCapacity } from '../types';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { StatusDot } from '../components/ui/StatusDot';

export const LiveOperationsPage: React.FC = () => {
  const [calls, setCalls] = useState<Call[]>([]);
  const [capacity, setCapacity] = useState<SafetyCapacity | null>(null);
  const [search, setSearch] = useState('');
  const [filterState, setFilterState] = useState<string>('ALL');
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const [liveCalls, cap] = await Promise.all([
        api.getLiveCalls(50),
        api.getSafetyCapacity(),
      ]);
      setCalls(liveCalls);
      setCapacity(cap);
    } catch (e) {
      console.error('Failed to load live ops:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 3000);
    return () => clearInterval(interval);
  }, []);

  useWebSocketEvent('CALL_UPDATED', () => loadData());
  useWebSocketEvent('SIMULATION_TICK', () => loadData());

  const filteredCalls = calls.filter((c) => {
    const matchesSearch =
      !search ||
      (c.borrower_name && c.borrower_name.toLowerCase().includes(search.toLowerCase())) ||
      (c.borrower_phone && c.borrower_phone.includes(search)) ||
      (c.agent_name && c.agent_name.toLowerCase().includes(search.toLowerCase())) ||
      c.id.includes(search);
    const matchesFilter = filterState === 'ALL' || c.call_state === filterState;
    return matchesSearch && matchesFilter;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-text tracking-tight flex items-center gap-2.5">
            <Radio size={20} className="text-accent animate-pulse" />
            Live Operations Control
          </h1>
          <p className="text-xs text-text-muted mt-0.5">
            Real-time call progression, agent bindings, and carrier telemetrics
          </p>
        </div>
        {capacity && (
          <div className="flex items-center gap-2 bg-card border border-card-border px-3 py-1.5 rounded-lg text-xs">
            <ShieldCheck size={14} className={capacity.is_safe ? 'text-success' : 'text-warning'} />
            <span className="text-text-muted">Safe Capacity:</span>
            <span className="font-mono font-bold text-text">{capacity.safe_dialing_capacity} Dials</span>
          </div>
        )}
      </div>

      {/* Capacity & Quick Metrics Banner */}
      {capacity && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div className="bg-card border border-card-border p-3 rounded-xl">
            <span className="text-[10px] text-text-muted uppercase font-semibold">Available Agents</span>
            <p className="text-xl font-bold text-success mt-0.5">{capacity.available_agents}</p>
          </div>
          <div className="bg-card border border-card-border p-3 rounded-xl">
            <span className="text-[10px] text-text-muted uppercase font-semibold">Reserved Agents</span>
            <p className="text-xl font-bold text-warning mt-0.5">{capacity.reserved_agents}</p>
          </div>
          <div className="bg-card border border-card-border p-3 rounded-xl">
            <span className="text-[10px] text-text-muted uppercase font-semibold">In Setup (Dialing)</span>
            <p className="text-xl font-bold text-accent mt-0.5">{capacity.dialing_calls}</p>
          </div>
          <div className="bg-card border border-card-border p-3 rounded-xl">
            <span className="text-[10px] text-text-muted uppercase font-semibold">Ringing Calls</span>
            <p className="text-xl font-bold text-[#38BDF8] mt-0.5">{capacity.ringing_calls}</p>
          </div>
          <div className="bg-card border border-card-border p-3 rounded-xl">
            <span className="text-[10px] text-text-muted uppercase font-semibold">Active Connected</span>
            <p className="text-xl font-bold text-success mt-0.5">{capacity.active_connected_calls}</p>
          </div>
        </div>
      )}

      {/* Filters & Search */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between bg-card border border-card-border p-3 rounded-xl">
        <div className="relative w-full sm:w-72">
          <Search size={14} className="absolute left-3 top-2.5 text-text-muted" />
          <input
            type="text"
            placeholder="Search by borrower, phone, or agent..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-[#101827] border border-card-border rounded-lg text-xs text-text placeholder:text-text-subtle focus:outline-none focus:border-accent"
          />
        </div>

        <div className="flex items-center gap-2 overflow-x-auto w-full sm:w-auto">
          {['ALL', 'CONNECTED', 'RINGING', 'INITIATED', 'COMPLETED', 'FAILED'].map((st) => (
            <button
              key={st}
              onClick={() => setFilterState(st)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                filterState === st
                  ? 'bg-accent text-white'
                  : 'bg-[#101827] text-text-muted hover:text-text border border-card-border'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Live Calls Table */}
      <Card title={`Active Call Streams (${filteredCalls.length})`}>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-card-border text-text-muted uppercase tracking-wider text-[10px]">
                <th className="py-2.5 px-3">Call ID</th>
                <th className="py-2.5 px-3">Borrower</th>
                <th className="py-2.5 px-3">Assigned Agent</th>
                <th className="py-2.5 px-3">Provider</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Ring Time</th>
                <th className="py-2.5 px-3">Talk Time</th>
                <th className="py-2.5 px-3">Initiated</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-card-border text-text">
              {filteredCalls.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-10 text-center text-text-muted">
                    No calls match the current filter criteria.
                  </td>
                </tr>
              ) : (
                filteredCalls.map((call) => (
                  <tr key={call.id} className="hover:bg-[#101827] transition-colors">
                    <td className="py-2.5 px-3 font-mono text-accent text-[11px]">
                      {call.id.substring(0, 8)}...
                    </td>
                    <td className="py-2.5 px-3 font-medium">
                      {call.borrower_name || 'Borrower'}
                      <span className="block text-[10px] text-text-muted font-mono">{call.borrower_phone}</span>
                    </td>
                    <td className="py-2.5 px-3">
                      {call.agent_name ? (
                        <span className="text-text font-medium flex items-center gap-1.5">
                          <UserCheck size={12} className="text-success" />
                          {call.agent_name}
                        </span>
                      ) : (
                        <span className="text-text-subtle italic">Unassigned (Predictive)</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px]">
                      <Badge variant="outline" size="sm">
                        {call.provider_id}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3">
                      <Badge
                        variant={
                          call.call_state === 'CONNECTED'
                            ? 'success'
                            : call.call_state === 'RINGING'
                            ? 'warning'
                            : call.call_state === 'COMPLETED'
                            ? 'neutral'
                            : call.call_state === 'FAILED'
                            ? 'danger'
                            : 'accent'
                        }
                        size="sm"
                      >
                        <StatusDot status={call.call_state} size="sm" pulse={call.call_state === 'RINGING'} />
                        {call.call_state}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px]">
                      {call.ring_time_seconds ? `${Math.round(call.ring_time_seconds)}s` : '—'}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-success font-semibold">
                      {call.talk_time_seconds ? `${Math.round(call.talk_time_seconds)}s` : '—'}
                    </td>
                    <td className="py-2.5 px-3 text-[11px] text-text-muted font-mono">
                      {call.initiated_at ? new Date(call.initiated_at).toLocaleTimeString() : 'N/A'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
