import React, { useState, useEffect } from 'react';
import {
  Users,
  UserCheck,
  PhoneCall,
  PhoneForwarded,
  Activity,
  CheckCircle2,
  TrendingUp,
  Percent,
  RefreshCw,
  Clock,
  Radio,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  Legend,
} from 'recharts';

import { api } from '../services/api';
import { useWebSocketEvent } from '../services/websocket';
import { OverviewData, Call } from '../types';
import { Card } from '../components/ui/Card';
import { MetricCard } from '../components/ui/MetricCard';
import { Badge } from '../components/ui/Badge';
import { StatusDot } from '../components/ui/StatusDot';

const AGENT_COLORS: Record<string, string> = {
  AVAILABLE: '#20C997',
  RESERVED: '#F5B942',
  DIALING: '#7C6CFF',
  CONNECTED: '#38BDF8',
  WRAP_UP: '#A78BFA',
  PAUSED: '#F97316',
  OFFLINE: '#64748B',
};

const OUTCOME_COLORS: Record<string, string> = {
  SUCCESS: '#20C997',
  BUSY: '#F5B942',
  UNANSWERED: '#8B96AA',
  FAILED: '#FF5C70',
  ABANDONED: '#EC4899',
  CANCELLED: '#64748B',
};

export const OverviewPage: React.FC = () => {
  const [data, setData] = useState<OverviewData | null>(null);
  const [liveCalls, setLiveCalls] = useState<Call[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  const loadData = async () => {
    try {
      const [overview, calls] = await Promise.all([
        api.getOverview(),
        api.getLiveCalls(15),
      ]);
      setData(overview);
      setLiveCalls(calls);
    } catch (err) {
      console.error('Failed to load overview data:', err);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(() => {
      loadData();
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  // Live WebSocket updates
  useWebSocketEvent('SIMULATION_TICK', () => {
    loadData();
  });

  useWebSocketEvent('CALL_UPDATED', () => {
    loadData();
  });

  useWebSocketEvent('AGENT_UPDATED', () => {
    loadData();
  });

  const handleManualRefresh = () => {
    setIsRefreshing(true);
    loadData();
  };

  if (loading || !data) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="animate-spin text-accent" size={32} />
          <span className="text-sm text-text-muted">Loading live operations telemetry...</span>
        </div>
      </div>
    );
  }

  const agentPieData = Object.entries(data.agent_distribution).map(([name, value]) => ({
    name,
    value,
    color: AGENT_COLORS[name] || '#7C6CFF',
  }));

  const callOutcomeData = Object.entries(data.call_outcomes).map(([name, value]) => ({
    name,
    count: value,
    color: OUTCOME_COLORS[name] || '#7C6CFF',
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-text tracking-tight flex items-center gap-2.5">
            Real-Time Operations Dashboard
            <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
          </h1>
          <p className="text-xs text-text-muted mt-0.5">
            Progressive & Predictive SmartDialer telemetric control plane
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleManualRefresh}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-card border border-card-border hover:border-[#2C3E5F] text-xs text-text-muted hover:text-text transition-all"
          >
            <RefreshCw size={13} className={isRefreshing ? 'animate-spin' : ''} />
            <span>Sync</span>
          </button>
        </div>
      </div>

      {/* Top KPI Cards (8 Required Metrics) */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
        <MetricCard
          label="Total Agents"
          value={data.kpis.total_agents}
          icon={Users}
          accentColor="#7C6CFF"
        />
        <MetricCard
          label="Available"
          value={data.kpis.available_agents}
          icon={UserCheck}
          accentColor="#20C997"
        />
        <MetricCard
          label="Reserved"
          value={data.kpis.reserved_agents}
          icon={Activity}
          accentColor="#F5B942"
        />
        <MetricCard
          label="Active Calls"
          value={data.kpis.active_calls}
          icon={PhoneCall}
          accentColor="#38BDF8"
        />
        <MetricCard
          label="Connected"
          value={data.kpis.connected_calls}
          icon={CheckCircle2}
          accentColor="#20C997"
        />
        <MetricCard
          label="Calls Initiated"
          value={data.kpis.calls_initiated}
          icon={PhoneForwarded}
          accentColor="#A78BFA"
        />
        <MetricCard
          label="Agent Utilization"
          value={`${data.kpis.agent_utilization_pct}%`}
          icon={Percent}
          accentColor="#7C6CFF"
        />
        <MetricCard
          label="Answer Rate"
          value={`${data.kpis.answer_rate_pct}%`}
          icon={TrendingUp}
          accentColor="#20C997"
        />
      </div>

      {/* Row 2: Charts (Call Activity & Agent Distribution) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* A. Live Call Activity Chart */}
        <Card
          title="Live Call Activity Over Time"
          subtitle="Real-time calls initiated, answered, connected, completed, and failed"
          className="lg:col-span-2"
        >
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data.time_series}>
                <defs>
                  <linearGradient id="colorInitiated" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#7C6CFF" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#7C6CFF" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="colorConnected" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#20C997" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#20C997" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="colorFailed" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#FF5C70" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#FF5C70" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="timestamp" stroke="#55637D" fontSize={10} tickLine={false} />
                <YAxis stroke="#55637D" fontSize={10} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#151F30',
                    borderColor: '#1E2C44',
                    borderRadius: '8px',
                    fontSize: '11px',
                    color: '#F5F7FF',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="initiated"
                  name="Initiated"
                  stroke="#7C6CFF"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorInitiated)"
                />
                <Area
                  type="monotone"
                  dataKey="connected"
                  name="Connected"
                  stroke="#20C997"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorConnected)"
                />
                <Area
                  type="monotone"
                  dataKey="failed"
                  name="Failed"
                  stroke="#FF5C70"
                  strokeWidth={1.5}
                  fillOpacity={1}
                  fill="url(#colorFailed)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="flex items-center justify-center gap-6 mt-2 pt-2 border-t border-card-border text-[11px] text-text-muted">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-[#7C6CFF]" /> Initiated
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-[#20C997]" /> Connected
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-[#FF5C70]" /> Failed
            </span>
          </div>
        </Card>

        {/* B. Agent Availability Distribution */}
        <Card
          title="Agent Availability Distribution"
          subtitle="Real-time breakdown of all agent states"
        >
          <div className="h-56 w-full flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={agentPieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={80}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {agentPieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#151F30',
                    borderColor: '#1E2C44',
                    borderRadius: '8px',
                    fontSize: '11px',
                    color: '#F5F7FF',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-2 gap-x-3 gap-y-1 mt-1 text-[11px] text-text-muted">
            {agentPieData.map((d) => (
              <div key={d.name} className="flex items-center justify-between">
                <span className="flex items-center gap-1.5 truncate">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: d.color }} />
                  {d.name}
                </span>
                <span className="font-mono font-semibold text-text">{d.value}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Row 3: Call Outcomes & Recent Activity Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* C. Call Outcome Analytics */}
        <Card
          title="Call Outcome Analytics"
          subtitle="Disposition breakdown across completed attempts"
          className="lg:col-span-1"
        >
          <div className="h-60 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={callOutcomeData} layout="vertical" margin={{ left: 20 }}>
                <XAxis type="number" stroke="#55637D" fontSize={10} tickLine={false} />
                <YAxis
                  type="category"
                  dataKey="name"
                  stroke="#8B96AA"
                  fontSize={10}
                  tickLine={false}
                  width={75}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#151F30',
                    borderColor: '#1E2C44',
                    borderRadius: '8px',
                    fontSize: '11px',
                    color: '#F5F7FF',
                  }}
                />
                <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                  {callOutcomeData.map((entry, index) => (
                    <Cell key={`bar-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* D. Recent Activity Feed */}
        <Card
          title="Recent Activity Feed"
          subtitle="Immutable audit log of allocation & safety events"
          className="lg:col-span-2"
        >
          <div className="h-60 overflow-y-auto space-y-2 pr-1">
            {data.recent_events.length === 0 ? (
              <p className="text-xs text-text-muted py-6 text-center">No recent activity logged yet.</p>
            ) : (
              data.recent_events.map((evt) => (
                <div
                  key={evt.id}
                  className="flex items-start justify-between p-2 rounded-lg bg-[#101827] border border-card-border text-xs transition-colors hover:border-[#2C3E5F]"
                >
                  <div className="flex items-start gap-2.5">
                    <StatusDot status={evt.event_type} size="sm" />
                    <div>
                      <span className="font-medium text-text text-[11px] block">{evt.message}</span>
                      <span className="text-[10px] text-text-subtle font-mono">
                        {evt.event_type} • {evt.entity_type}
                      </span>
                    </div>
                  </div>
                  <span className="text-[10px] text-text-subtle font-mono whitespace-nowrap">
                    {evt.created_at ? new Date(evt.created_at).toLocaleTimeString() : 'now'}
                  </span>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>

      {/* E. Live Operations Table */}
      <Card
        title="Live Operations Table"
        subtitle="Active call tracking with carrier status and conversation duration"
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-card-border text-text-muted uppercase tracking-wider text-[10px]">
                <th className="py-2.5 px-3">Call ID</th>
                <th className="py-2.5 px-3">Borrower</th>
                <th className="py-2.5 px-3">Agent</th>
                <th className="py-2.5 px-3">Provider</th>
                <th className="py-2.5 px-3">Call State</th>
                <th className="py-2.5 px-3">Duration</th>
                <th className="py-2.5 px-3">Initiated</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-card-border text-text">
              {liveCalls.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-6 text-center text-text-muted">
                    No active calls in flight. Start a campaign or simulation to initiate dialing.
                  </td>
                </tr>
              ) : (
                liveCalls.map((call) => (
                  <tr key={call.id} className="hover:bg-[#101827] transition-colors">
                    <td className="py-2.5 px-3 font-mono text-accent text-[11px]">
                      {call.id.substring(0, 8)}...
                    </td>
                    <td className="py-2.5 px-3 font-medium">
                      {call.borrower_name || 'Borrower'}
                      <span className="block text-[10px] text-text-muted font-mono">
                        {call.borrower_phone}
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      {call.agent_name ? (
                        <span className="text-text font-medium">{call.agent_name}</span>
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
                      {call.call_state === 'CONNECTED'
                        ? `${Math.round(call.talk_time_seconds || 0)}s`
                        : `${Math.round(call.total_duration_seconds || 0)}s`}
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
