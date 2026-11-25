import React, { useState, useEffect } from 'react';
import { BrainCircuit, ShieldAlert, TrendingUp, Sliders, Calculator, CheckCircle2, XCircle, AlertTriangle, ArrowRight } from 'lucide-react';
import { api } from '../services/api';
import { useWebSocketEvent } from '../services/websocket';
import { PacingStatus, SafetyDecision } from '../types';
import { Card } from '../components/ui/Card';
import { MetricCard } from '../components/ui/MetricCard';
import { Badge } from '../components/ui/Badge';

export const PredictiveEnginePage: React.FC = () => {
  const [pacing, setPacing] = useState<PacingStatus | null>(null);
  const [riskFactor, setRiskFactor] = useState<number>(0.15);
  const [latestDecision, setLatestDecision] = useState<SafetyDecision | null>(null);
  const [loading, setLoading] = useState(true);

  const loadPacing = async () => {
    try {
      const [pacingData, decisions] = await Promise.all([
        api.getPacingStatus(undefined, riskFactor),
        api.getSafetyDecisions(1),
      ]);
      setPacing(pacingData);
      if (decisions.length > 0) {
        setLatestDecision(decisions[0]);
      }
    } catch (err) {
      console.error('Failed to load pacing data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPacing();
    const interval = setInterval(loadPacing, 3000);
    return () => clearInterval(interval);
  }, [riskFactor]);

  useWebSocketEvent('SAFETY_DECISION', (data: any) => {
    setLatestDecision(data);
    loadPacing();
  });

  useWebSocketEvent('SIMULATION_TICK', () => loadPacing());

  if (loading || !pacing) {
    return (
      <div className="flex items-center justify-center h-80 text-text-muted text-sm">
        Calculating statistical pacing formula inputs...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-text tracking-tight flex items-center gap-2.5">
            <BrainCircuit size={20} className="text-accent" />
            Statistical Predictive Pacing Engine
          </h1>
          <p className="text-xs text-text-muted mt-0.5">
            Statistical pacing models bounded by mandatory Safety Controller authorization
          </p>
        </div>
        <Badge variant="warning" size="md">
          <ShieldAlert size={14} className="text-warning" />
          <span>CANNOT DIRECTLY DIAL — GATED BY SAFETY CONTROLLER</span>
        </Badge>
      </div>

      {/* Live Explanation Banner */}
      <div className="bg-gradient-to-r from-[#151F30] to-[#101827] border border-[#7C6CFF44] rounded-xl p-5 shadow-glow-accent">
        <div className="flex items-start gap-3">
          <div className="w-9 h-9 rounded-lg bg-[#7C6CFF22] border border-[#7C6CFF66] flex items-center justify-center text-accent flex-shrink-0">
            <Calculator size={18} />
          </div>
          <div className="flex-1">
            <span className="text-[11px] font-mono text-accent uppercase tracking-wider font-bold">
              Live Pacing Calculation & Audit Explanation
            </span>
            <p className="text-sm font-medium text-text mt-1 leading-relaxed">
              "{pacing.formula_explanation}"
            </p>
            {latestDecision && (
              <div className="mt-3 pt-3 border-t border-card-border flex flex-wrap items-center gap-3 text-xs">
                <span className="text-text-muted">Safety Controller Audit:</span>
                <Badge
                  variant={
                    latestDecision.decision === 'APPROVE'
                      ? 'success'
                      : latestDecision.decision === 'REDUCE'
                      ? 'warning'
                      : 'danger'
                  }
                  size="sm"
                >
                  {latestDecision.decision}
                </Badge>
                <span className="text-text-subtle font-mono text-[11px]">
                  Approved: {latestDecision.approved_calls} • Rejected: {latestDecision.rejected_calls}
                </span>
                <span className="text-text-muted italic truncate max-w-md">
                  Reason: {latestDecision.reason}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Pacing Metrics Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <MetricCard
          label="Available Agents"
          value={pacing.available_agents}
          accentColor="#20C997"
        />
        <MetricCard
          label="Near-Term Releases"
          value={pacing.expected_near_term_releases.toFixed(1)}
          accentColor="#38BDF8"
        />
        <MetricCard
          label="Ringing Calls"
          value={pacing.ringing_calls}
          accentColor="#F5B942"
        />
        <MetricCard
          label="Smoothed Answer Rate"
          value={`${(pacing.smoothed_answer_rate * 100).toFixed(1)}%`}
          accentColor="#7C6CFF"
        />
        <MetricCard
          label="Requested Dials"
          value={pacing.requested_dial_count}
          accentColor="#A78BFA"
        />
        <MetricCard
          label="Predicted Answers"
          value={
            pacing.calculation_details.raw_dials_needed
              ? (pacing.requested_dial_count * pacing.smoothed_answer_rate).toFixed(1)
              : '0'
          }
          accentColor="#20C997"
        />
      </div>

      {/* Detailed Mathematical Formulation Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <Card
          title="Predictive Pacing Formula"
          subtitle="Configurable statistical variables and near-term capacity estimation"
          className="lg:col-span-2"
        >
          <div className="space-y-4 text-xs">
            <div className="bg-[#101827] p-3 rounded-lg border border-card-border font-mono text-[11px] leading-relaxed text-text">
              <span className="text-text-muted block mb-1">Mathematical Derivation:</span>
              <p className="text-accent">
                Expected_Available = Available_Agents ({pacing.available_agents}) + Imminent_Releases ({pacing.expected_near_term_releases.toFixed(1)})
              </p>
              <p className="text-text-muted mt-1">
                Net_Capacity_Needed = Expected_Available - (Ringing_Calls × Smoothed_Answer_Rate)
              </p>
              <p className="text-[#20C997] mt-1">
                Requested_Dials = (Net_Capacity_Needed / Smoothed_Answer_Rate) × (1 - Risk_Factor)
              </p>
            </div>

            {/* Risk Factor Slider */}
            <div className="pt-2">
              <div className="flex items-center justify-between mb-1.5">
                <span className="font-medium text-text flex items-center gap-1.5">
                  <Sliders size={14} className="text-accent" />
                  Conservative Risk Factor (Safety Buffer)
                </span>
                <span className="font-mono text-accent font-bold">{(riskFactor * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.0"
                max="0.5"
                step="0.05"
                value={riskFactor}
                onChange={(e) => setRiskFactor(parseFloat(e.target.value))}
                className="w-full accent-accent bg-[#101827] h-2 rounded-lg cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-text-subtle mt-1">
                <span>0% (Aggressive Pacing)</span>
                <span>25% (Balanced Enterprise)</span>
                <span>50% (Ultra Conservative)</span>
              </div>
            </div>

            {/* Flow to Safety Controller */}
            <div className="p-3 bg-[#101827] rounded-lg border border-card-border flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-accent/20 text-accent flex items-center justify-center font-bold">
                  P
                </div>
                <div>
                  <span className="text-text font-semibold block">Requested Dials: {pacing.requested_dial_count}</span>
                  <span className="text-text-muted text-[11px]">Sent to Safety Controller for independent verification</span>
                </div>
              </div>
              <ArrowRight size={16} className="text-accent" />
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-success/20 text-success flex items-center justify-center font-bold">
                  S
                </div>
                <div>
                  <span className="text-text font-semibold block">
                    Approved: {latestDecision ? latestDecision.approved_calls : 0}
                  </span>
                  <span className="text-text-muted text-[11px]">Enforced zero-abandonment cap</span>
                </div>
              </div>
            </div>
          </div>
        </Card>

        {/* Real-time Calculation Breakdown Card */}
        <Card title="Current Formula Variables">
          <div className="space-y-3 text-xs">
            <div className="flex justify-between items-center py-1.5 border-b border-card-border">
              <span className="text-text-muted">Dialing Mode</span>
              <Badge variant="accent" size="sm">
                {pacing.dialing_mode}
              </Badge>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b border-card-border">
              <span className="text-text-muted">Raw Answer Rate</span>
              <span className="font-mono text-text font-semibold">
                {(pacing.historical_answer_rate * 100).toFixed(1)}%
              </span>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b border-card-border">
              <span className="text-text-muted">Bayesian Smoothed Rate</span>
              <span className="font-mono text-success font-semibold">
                {(pacing.smoothed_answer_rate * 100).toFixed(1)}%
              </span>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b border-card-border">
              <span className="text-text-muted">Near-Term Releases</span>
              <span className="font-mono text-text font-semibold">
                {pacing.expected_near_term_releases.toFixed(1)}
              </span>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b border-card-border">
              <span className="text-text-muted">Applied Safety Buffer</span>
              <span className="font-mono text-warning font-semibold">
                {pacing.safety_buffer.toFixed(1)} Dials
              </span>
            </div>
            <div className="flex justify-between items-center py-1.5">
              <span className="text-text-muted">Max Multiplier Cap</span>
              <span className="font-mono text-text font-semibold">
                {pacing.calculation_details.max_pacing_limit || 'N/A'} (2.5x)
              </span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};
