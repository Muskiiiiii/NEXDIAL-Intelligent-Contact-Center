import React, { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, Percent, Clock, Users, PhoneCall, Filter, RefreshCw } from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, BarChart, Bar, Cell } from 'recharts';
import { api } from '../services/api';
import { OverviewData } from '../types';
import { Card } from '../components/ui/Card';
import { MetricCard } from '../components/ui/MetricCard';

export const AnalyticsPage: React.FC = () => {
  const [data, setData] = useState<OverviewData | null>(null);
  const [timeWindow, setTimeWindow] = useState<'5m' | '15m' | '1h' | 'today'>('15m');
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const points = timeWindow === '5m' ? 6 : timeWindow === '15m' ? 12 : timeWindow === '1h' ? 24 : 36;
      const [overview, ts] = await Promise.all([
        api.getOverview(),
        api.getTimeSeries(points),
      ]);
      overview.time_series = ts;
      setData(overview);
    } catch (err) {
      console.error('Failed to load analytics:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [timeWindow]);

  if (loading || !data) {
    return <div className="text-center py-12 text-xs text-text-muted">Loading analytics data...</div>;
  }

  const kpis = data.kpis;
  const totalCalls = Math.max(1, kpis.calls_initiated);
  const connectionRatePct = ((kpis.connected_calls / totalCalls) * 100).toFixed(1);
  const completedCalls = data.call_outcomes['SUCCESS'] || 0;
  const completionRatePct = ((completedCalls / totalCalls) * 100).toFixed(1);
  const failedCalls = (data.call_outcomes['FAILED'] || 0) + (data.call_outcomes['BUSY'] || 0);
  const failureRatePct = ((failedCalls / totalCalls) * 100).toFixed(1);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-text tracking-tight flex items-center gap-2.5">
            <BarChart3 size={20} className="text-accent" />
            Operational Performance & Contact Center Analytics
          </h1>
          <p className="text-xs text-text-muted mt-0.5">
            Real historical metrics derived directly from normalized PostgreSQL / SQLite call records
          </p>
        </div>

        {/* Time Window Selector */}
        <div className="flex items-center gap-1.5 bg-card border border-card-border p-1 rounded-lg">
          {[
            { id: '5m', label: 'Last 5m' },
            { id: '15m', label: 'Last 15m' },
            { id: '1h', label: 'Last 1h' },
            { id: 'today', label: 'Today' },
          ].map((w) => (
            <button
              key={w.id}
              onClick={() => setTimeWindow(w.id as any)}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                timeWindow === w.id
                  ? 'bg-accent text-white'
                  : 'text-text-muted hover:text-text'
              }`}
            >
              {w.label}
            </button>
          ))}
        </div>
      </div>

      {/* Analytics KPIs Strip */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <MetricCard
          label="Agent Utilization"
          value={`${kpis.agent_utilization_pct}%`}
          icon={Percent}
          accentColor="#7C6CFF"
        />
        <MetricCard
          label="Answer Rate"
          value={`${kpis.answer_rate_pct}%`}
          icon={TrendingUp}
          accentColor="#20C997"
        />
        <MetricCard
          label="Connection Rate"
          value={`${connectionRatePct}%`}
          icon={PhoneCall}
          accentColor="#38BDF8"
        />
        <MetricCard
          label="Completion Rate"
          value={`${completionRatePct}%`}
          icon={TrendingUp}
          accentColor="#20C997"
        />
        <MetricCard
          label="Failed / Busy Rate"
          value={`${failureRatePct}%`}
          icon={Percent}
          accentColor="#FF5C70"
        />
        <MetricCard
          label="Avg Talk Time"
          value={`${kpis.average_talk_time_sec}s`}
          icon={Clock}
          accentColor="#F5B942"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Card
          title="Historical Throughput & Connected Concurrency"
          subtitle={`Telemetry across ${timeWindow} time-series window`}
        >
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data.time_series}>
                <defs>
                  <linearGradient id="anInitiated" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#7C6CFF" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#7C6CFF" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="anConnected" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#20C997" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#20C997" stopOpacity={0.0} />
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
                  fill="url(#anInitiated)"
                />
                <Area
                  type="monotone"
                  dataKey="connected"
                  name="Connected"
                  stroke="#20C997"
                  strokeWidth={2}
                  fill="url(#anConnected)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card
          title="Call Outcome Disposition Breakdown"
          subtitle="Detailed classification of completed calls"
        >
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={Object.entries(data.call_outcomes).map(([name, count]) => ({
                  name,
                  count,
                }))}
              >
                <XAxis dataKey="name" stroke="#55637D" fontSize={10} tickLine={false} />
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
                <Bar dataKey="count" fill="#7C6CFF" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </div>
  );
};
