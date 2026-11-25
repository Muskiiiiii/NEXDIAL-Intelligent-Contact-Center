import React, { useState, useEffect } from 'react';
import { PhoneCall, Search, Filter, Clock, CheckCircle2, XCircle, AlertCircle, RefreshCw } from 'lucide-react';
import { api } from '../services/api';
import { Call, CallState } from '../types';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { StatusDot } from '../components/ui/StatusDot';

export const CallHistoryPage: React.FC = () => {
  const [calls, setCalls] = useState<Call[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [stateFilter, setStateFilter] = useState<string>('ALL');

  const loadCalls = async () => {
    try {
      const data = await api.getCalls({
        state: stateFilter !== 'ALL' ? stateFilter : undefined,
        limit: 100,
      });
      setCalls(data.calls);
      setTotal(data.total);
    } catch (err) {
      console.error('Failed to load call history:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCalls();
  }, [stateFilter]);

  const filtered = calls.filter((c) => {
    if (!search) return true;
    return (
      (c.borrower_name && c.borrower_name.toLowerCase().includes(search.toLowerCase())) ||
      (c.borrower_phone && c.borrower_phone.includes(search)) ||
      (c.agent_name && c.agent_name.toLowerCase().includes(search.toLowerCase())) ||
      c.id.includes(search)
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-text tracking-tight flex items-center gap-2.5">
            <PhoneCall size={20} className="text-accent" />
            Call History & Disposition Archive
          </h1>
          <p className="text-xs text-text-muted mt-0.5">
            Complete transactional call records with carrier event timing and telemetry
          </p>
        </div>
        <button
          onClick={loadCalls}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-card border border-card-border hover:border-[#2C3E5F] text-xs text-text-muted hover:text-text transition-colors"
        >
          <RefreshCw size={13} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between bg-card border border-card-border p-3 rounded-xl">
        <div className="relative w-full sm:w-72">
          <Search size={14} className="absolute left-3 top-2.5 text-text-muted" />
          <input
            type="text"
            placeholder="Search by borrower, agent, or call ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-[#101827] border border-card-border rounded-lg text-xs text-text placeholder:text-text-subtle focus:outline-none focus:border-accent"
          />
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto">
          {['ALL', 'COMPLETED', 'FAILED', 'CONNECTED', 'RINGING', 'CANCELLED'].map((st) => (
            <button
              key={st}
              onClick={() => setStateFilter(st)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                stateFilter === st
                  ? 'bg-accent text-white'
                  : 'bg-[#101827] text-text-muted hover:text-text border border-card-border'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Calls Table */}
      <Card title={`Historical Call Records (${filtered.length} of ${total})`}>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-card-border text-text-muted uppercase tracking-wider text-[10px]">
                <th className="py-2.5 px-3">Call ID</th>
                <th className="py-2.5 px-3">Borrower</th>
                <th className="py-2.5 px-3">Agent</th>
                <th className="py-2.5 px-3">Carrier</th>
                <th className="py-2.5 px-3">State</th>
                <th className="py-2.5 px-3">Outcome</th>
                <th className="py-2.5 px-3">Ring Time</th>
                <th className="py-2.5 px-3">Talk Time</th>
                <th className="py-2.5 px-3">Initiated Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-card-border text-text">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-8 text-center text-text-muted">
                    No calls match current search criteria.
                  </td>
                </tr>
              ) : (
                filtered.map((c) => (
                  <tr key={c.id} className="hover:bg-[#101827] transition-colors">
                    <td className="py-2.5 px-3 font-mono text-accent text-[11px]">
                      {c.id.substring(0, 8)}...
                    </td>
                    <td className="py-2.5 px-3 font-medium">
                      {c.borrower_name || 'Borrower'}
                      <span className="block text-[10px] text-text-muted font-mono">{c.borrower_phone}</span>
                    </td>
                    <td className="py-2.5 px-3">
                      {c.agent_name || <span className="text-text-subtle italic">Unassigned</span>}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px]">
                      <Badge variant="outline" size="sm">
                        {c.provider_id}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3">
                      <Badge
                        variant={
                          c.call_state === 'COMPLETED'
                            ? 'success'
                            : c.call_state === 'FAILED'
                            ? 'danger'
                            : c.call_state === 'CONNECTED'
                            ? 'accent'
                            : 'warning'
                        }
                        size="sm"
                      >
                        <StatusDot status={c.call_state} size="sm" />
                        {c.call_state}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`font-semibold font-mono text-[11px] ${
                          c.outcome === 'SUCCESS'
                            ? 'text-success'
                            : c.outcome === 'FAILED'
                            ? 'text-danger'
                            : 'text-warning'
                        }`}
                      >
                        {c.outcome}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px]">
                      {c.ring_time_seconds ? `${Math.round(c.ring_time_seconds)}s` : '—'}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] font-semibold text-text">
                      {c.talk_time_seconds ? `${Math.round(c.talk_time_seconds)}s` : '—'}
                    </td>
                    <td className="py-2.5 px-3 text-[11px] text-text-muted font-mono">
                      {c.initiated_at ? new Date(c.initiated_at).toLocaleTimeString() : 'N/A'}
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
