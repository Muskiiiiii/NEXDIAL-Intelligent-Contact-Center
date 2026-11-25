import React, { useState, useEffect } from 'react';
import { Users, UserPlus, Pause, Play, Power, PowerOff, Search, Clock, PhoneCall, RefreshCw, ShieldCheck } from 'lucide-react';
import { api } from '../services/api';
import { useWebSocketEvent } from '../services/websocket';
import { Agent, AgentStatus } from '../types';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { StatusDot } from '../components/ui/StatusDot';

export const AgentManagementPage: React.FC = () => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [summary, setSummary] = useState({ total: 0, avail: 0, res: 0, conn: 0, off: 0 });
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newAgentName, setNewAgentName] = useState('');

  const loadAgents = async () => {
    try {
      const data = await api.getAgents();
      setAgents(data.agents);
      setSummary({
        total: data.total,
        avail: data.available_count,
        res: data.reserved_count,
        conn: data.connected_count,
        off: data.offline_count,
      });
    } catch (err) {
      console.error('Failed to load agents:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAgents();
  }, []);

  useWebSocketEvent('AGENT_UPDATED', () => loadAgents());
  useWebSocketEvent('AGENT_CREATED', () => loadAgents());
  useWebSocketEvent('SIMULATION_TICK', () => loadAgents());

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAgentName.trim()) return;
    try {
      await api.createAgent(newAgentName.trim(), 'AVAILABLE');
      setIsModalOpen(false);
      setNewAgentName('');
      loadAgents();
    } catch (err: any) {
      alert(`Error creating agent: ${err.message}`);
    }
  };

  const handleAction = async (agentId: string, action: 'pause' | 'resume' | 'online' | 'offline') => {
    try {
      if (action === 'pause') await api.pauseAgent(agentId);
      else if (action === 'resume') await api.resumeAgent(agentId);
      else if (action === 'online') await api.bringAgentOnline(agentId);
      else if (action === 'offline') await api.takeAgentOffline(agentId);
      loadAgents();
    } catch (err: any) {
      alert(`Action failed: ${err.message}`);
    }
  };

  const filteredAgents = agents.filter((ag) => {
    const matchesSearch = !search || ag.name.toLowerCase().includes(search.toLowerCase()) || ag.id.includes(search);
    const matchesStatus = selectedStatus === 'ALL' || ag.status === selectedStatus;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-text tracking-tight flex items-center gap-2.5">
            <Users size={20} className="text-accent" />
            Agent Management & Lifecycle Control
          </h1>
          <p className="text-xs text-text-muted mt-0.5">
            State-machine enforcement with atomic conditional database row locking
          </p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-xs font-semibold shadow-glow-accent transition-all"
        >
          <UserPlus size={15} />
          <span>Add Agent</span>
        </button>
      </div>

      {/* Summary KPI Strip */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="bg-card border border-card-border p-3 rounded-xl">
          <span className="text-[10px] text-text-muted uppercase font-semibold">Total Agents</span>
          <p className="text-xl font-bold text-text mt-0.5">{summary.total}</p>
        </div>
        <div className="bg-card border border-card-border p-3 rounded-xl">
          <span className="text-[10px] text-text-muted uppercase font-semibold">Available</span>
          <p className="text-xl font-bold text-success mt-0.5">{summary.avail}</p>
        </div>
        <div className="bg-card border border-card-border p-3 rounded-xl">
          <span className="text-[10px] text-text-muted uppercase font-semibold">Reserved / Dialing</span>
          <p className="text-xl font-bold text-warning mt-0.5">{summary.res}</p>
        </div>
        <div className="bg-card border border-card-border p-3 rounded-xl">
          <span className="text-[10px] text-text-muted uppercase font-semibold">In Conversation</span>
          <p className="text-xl font-bold text-[#38BDF8] mt-0.5">{summary.conn}</p>
        </div>
        <div className="bg-card border border-card-border p-3 rounded-xl">
          <span className="text-[10px] text-text-muted uppercase font-semibold">Offline</span>
          <p className="text-xl font-bold text-text-muted mt-0.5">{summary.off}</p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between bg-card border border-card-border p-3 rounded-xl">
        <div className="relative w-full sm:w-72">
          <Search size={14} className="absolute left-3 top-2.5 text-text-muted" />
          <input
            type="text"
            placeholder="Search agents by name or ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-[#101827] border border-card-border rounded-lg text-xs text-text placeholder:text-text-subtle focus:outline-none focus:border-accent"
          />
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto">
          {['ALL', 'AVAILABLE', 'RESERVED', 'DIALING', 'CONNECTED', 'WRAP_UP', 'PAUSED', 'OFFLINE'].map((st) => (
            <button
              key={st}
              onClick={() => setSelectedStatus(st)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                selectedStatus === st
                  ? 'bg-accent text-white'
                  : 'bg-[#101827] text-text-muted hover:text-text border border-card-border'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Agents Table */}
      <Card title={`Registered Agents (${filteredAgents.length})`}>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-card-border text-text-muted uppercase tracking-wider text-[10px]">
                <th className="py-2.5 px-3">Agent</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Current Binding</th>
                <th className="py-2.5 px-3">Calls Handled</th>
                <th className="py-2.5 px-3">Avg Talk Time</th>
                <th className="py-2.5 px-3">Last Activity</th>
                <th className="py-2.5 px-3 text-right">Lifecycle Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-card-border text-text">
              {filteredAgents.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-text-muted">
                    No agents match the current filter.
                  </td>
                </tr>
              ) : (
                filteredAgents.map((ag) => (
                  <tr key={ag.id} className="hover:bg-[#101827] transition-colors">
                    <td className="py-2.5 px-3 font-medium">
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded-full bg-[#1E2C44] flex items-center justify-center text-[10px] text-accent font-bold">
                          {ag.name.substring(0, 2).toUpperCase()}
                        </div>
                        <div>
                          <span className="text-text block font-semibold">{ag.name}</span>
                          <span className="text-[10px] text-text-subtle font-mono">{ag.id.substring(0, 8)}...</span>
                        </div>
                      </div>
                    </td>

                    <td className="py-2.5 px-3">
                      <Badge
                        variant={
                          ag.status === 'AVAILABLE'
                            ? 'success'
                            : ag.status === 'CONNECTED'
                            ? 'accent'
                            : ag.status === 'RESERVED' || ag.status === 'DIALING'
                            ? 'warning'
                            : ag.status === 'PAUSED'
                            ? 'warning'
                            : 'neutral'
                        }
                        size="sm"
                      >
                        <StatusDot status={ag.status} size="sm" pulse={ag.status === 'CONNECTED'} />
                        {ag.status}
                      </Badge>
                    </td>

                    <td className="py-2.5 px-3 font-mono text-[11px]">
                      {ag.current_call_id ? (
                        <span className="text-[#38BDF8] flex items-center gap-1">
                          <PhoneCall size={12} />
                          Call: {ag.current_call_id.substring(0, 8)}...
                        </span>
                      ) : (
                        <span className="text-text-subtle">Idle / Unassigned</span>
                      )}
                    </td>

                    <td className="py-2.5 px-3 font-mono text-[11px] font-semibold">{ag.total_calls}</td>

                    <td className="py-2.5 px-3 font-mono text-[11px]">
                      {ag.average_talk_time ? `${Math.round(ag.average_talk_time)}s` : '0s'}
                    </td>

                    <td className="py-2.5 px-3 text-[11px] text-text-muted font-mono">
                      {ag.last_status_change ? new Date(ag.last_status_change).toLocaleTimeString() : 'N/A'}
                    </td>

                    <td className="py-2.5 px-3 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {ag.status === 'AVAILABLE' && (
                          <button
                            onClick={() => handleAction(ag.id, 'pause')}
                            title="Pause Agent"
                            className="p-1 rounded bg-[#101827] hover:bg-warning/20 text-warning border border-card-border transition-colors"
                          >
                            <Pause size={12} />
                          </button>
                        )}

                        {ag.status === 'PAUSED' && (
                          <button
                            onClick={() => handleAction(ag.id, 'resume')}
                            title="Resume Agent"
                            className="p-1 rounded bg-[#101827] hover:bg-success/20 text-success border border-card-border transition-colors"
                          >
                            <Play size={12} />
                          </button>
                        )}

                        {ag.status === 'OFFLINE' ? (
                          <button
                            onClick={() => handleAction(ag.id, 'online')}
                            title="Bring Agent Online"
                            className="p-1 rounded bg-[#101827] hover:bg-success/20 text-success border border-card-border transition-colors"
                          >
                            <Power size={12} />
                          </button>
                        ) : (
                          <button
                            onClick={() => handleAction(ag.id, 'offline')}
                            title="Take Agent Offline"
                            className="p-1 rounded bg-[#101827] hover:bg-danger/20 text-danger border border-card-border transition-colors"
                          >
                            <PowerOff size={12} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Add Agent Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Register New Agent"
        subtitle="Agent will be initialized in AVAILABLE state ready for automatic allocation"
      >
        <form onSubmit={handleCreate} className="space-y-4 text-xs">
          <div>
            <label className="block text-text-muted mb-1 font-medium">Agent Full Name</label>
            <input
              type="text"
              required
              value={newAgentName}
              onChange={(e) => setNewAgentName(e.target.value)}
              placeholder="e.g. Rachel Zane"
              className="w-full px-3 py-2 bg-[#101827] border border-card-border rounded-lg text-text focus:outline-none focus:border-accent"
            />
          </div>

          <div className="pt-3 border-t border-card-border flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="px-4 py-2 rounded-lg bg-[#101827] text-text-muted hover:text-text border border-card-border transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white font-semibold shadow-glow-accent transition-all"
            >
              Add Agent
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
