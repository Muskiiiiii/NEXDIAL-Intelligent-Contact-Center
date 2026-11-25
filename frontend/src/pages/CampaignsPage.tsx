import React, { useState, useEffect } from 'react';
import { Layers, Plus, Play, Pause, Square, RefreshCw, BarChart2, Shield, Settings2 } from 'lucide-react';
import { api } from '../services/api';
import { Campaign, DialingMode, CampaignStatus } from '../types';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { StatusDot } from '../components/ui/StatusDot';

export const CampaignsPage: React.FC = () => {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    dialing_mode: 'PROGRESSIVE' as DialingMode,
    priority: 1,
    max_attempts: 3,
    retry_interval_seconds: 300,
    target_abandon_rate: 0.03,
  });

  const loadCampaigns = async () => {
    try {
      const data = await api.getCampaigns();
      setCampaigns(data);
    } catch (err) {
      console.error('Failed to load campaigns:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCampaigns();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createCampaign(formData);
      setIsModalOpen(false);
      setFormData({
        name: '',
        dialing_mode: 'PROGRESSIVE',
        priority: 1,
        max_attempts: 3,
        retry_interval_seconds: 300,
        target_abandon_rate: 0.03,
      });
      loadCampaigns();
    } catch (err: any) {
      alert(`Error creating campaign: ${err.message}`);
    }
  };

  const handleStart = async (id: string) => {
    await api.startCampaign(id);
    loadCampaigns();
  };

  const handlePause = async (id: string) => {
    await api.pauseCampaign(id);
    loadCampaigns();
  };

  const handleResume = async (id: string) => {
    await api.resumeCampaign(id);
    loadCampaigns();
  };

  const handleStop = async (id: string) => {
    await api.stopCampaign(id);
    loadCampaigns();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-text tracking-tight flex items-center gap-2.5">
            <Layers size={20} className="text-accent" />
            Campaign Management
          </h1>
          <p className="text-xs text-text-muted mt-0.5">
            Configure Progressive and Predictive dialing campaigns with target abandonment limits
          </p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-xs font-semibold shadow-glow-accent transition-all"
        >
          <Plus size={15} />
          <span>New Campaign</span>
        </button>
      </div>

      {/* Campaigns Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {campaigns.map((camp) => {
          const progress =
            camp.total_borrowers > 0
              ? Math.round((camp.completed_borrowers / camp.total_borrowers) * 100)
              : 0;

          return (
            <Card key={camp.id} className="relative">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-semibold text-text">{camp.name}</h3>
                    <Badge
                      variant={camp.dialing_mode === 'PROGRESSIVE' ? 'accent' : 'warning'}
                      size="sm"
                    >
                      {camp.dialing_mode}
                    </Badge>
                  </div>
                  <span className="text-[10px] text-text-muted font-mono mt-0.5 block">
                    ID: {camp.id.substring(0, 8)}... • Priority {camp.priority}
                  </span>
                </div>

                <Badge
                  variant={
                    camp.status === 'RUNNING'
                      ? 'success'
                      : camp.status === 'PAUSED'
                      ? 'warning'
                      : 'neutral'
                  }
                  size="md"
                >
                  <StatusDot status={camp.status} size="sm" pulse={camp.status === 'RUNNING'} />
                  {camp.status}
                </Badge>
              </div>

              {/* Progress Bar */}
              <div className="mt-4">
                <div className="flex justify-between text-xs text-text-muted mb-1">
                  <span>Borrower Completion</span>
                  <span className="font-mono text-text font-semibold">
                    {camp.completed_borrowers} / {camp.total_borrowers} ({progress}%)
                  </span>
                </div>
                <div className="w-full bg-[#101827] h-2 rounded-full overflow-hidden border border-card-border">
                  <div
                    className="bg-accent h-full rounded-full transition-all duration-500"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>

              {/* Campaign Metrics */}
              <div className="grid grid-cols-3 gap-2 mt-4 pt-3 border-t border-card-border text-center text-xs">
                <div className="bg-[#101827] p-2 rounded-lg border border-card-border">
                  <span className="text-[10px] text-text-muted block">Max Attempts</span>
                  <span className="font-mono font-bold text-text mt-0.5 block">{camp.max_attempts}</span>
                </div>
                <div className="bg-[#101827] p-2 rounded-lg border border-card-border">
                  <span className="text-[10px] text-text-muted block">Retry Interval</span>
                  <span className="font-mono font-bold text-text mt-0.5 block">{camp.retry_interval_seconds}s</span>
                </div>
                <div className="bg-[#101827] p-2 rounded-lg border border-card-border">
                  <span className="text-[10px] text-text-muted block">Max Abandon</span>
                  <span className="font-mono font-bold text-success mt-0.5 block">
                    {(camp.target_abandon_rate * 100).toFixed(1)}%
                  </span>
                </div>
              </div>

              {/* Campaign Actions */}
              <div className="mt-4 pt-3 border-t border-card-border flex items-center justify-end gap-2">
                {camp.status === 'RUNNING' ? (
                  <button
                    onClick={() => handlePause(camp.id)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-warning/10 text-warning border border-warning/30 hover:bg-warning/20 text-xs font-medium transition-colors"
                  >
                    <Pause size={13} />
                    <span>Pause</span>
                  </button>
                ) : camp.status === 'PAUSED' ? (
                  <button
                    onClick={() => handleResume(camp.id)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-success/10 text-success border border-success/30 hover:bg-success/20 text-xs font-medium transition-colors"
                  >
                    <Play size={13} />
                    <span>Resume</span>
                  </button>
                ) : (
                  <button
                    onClick={() => handleStart(camp.id)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-success/10 text-success border border-success/30 hover:bg-success/20 text-xs font-medium transition-colors"
                  >
                    <Play size={13} />
                    <span>Start</span>
                  </button>
                )}

                {camp.status !== 'STOPPED' && (
                  <button
                    onClick={() => handleStop(camp.id)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-danger/10 text-danger border border-danger/30 hover:bg-danger/20 text-xs font-medium transition-colors"
                  >
                    <Square size={13} />
                    <span>Stop</span>
                  </button>
                )}
              </div>
            </Card>
          );
        })}
      </div>

      {/* Create Campaign Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Create Outbound Campaign"
        subtitle="Define dialing mode, retry policies, and regulatory thresholds"
      >
        <form onSubmit={handleCreate} className="space-y-4 text-xs">
          <div>
            <label className="block text-text-muted mb-1 font-medium">Campaign Name</label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g. Q4 Overdue Account Settlement"
              className="w-full px-3 py-2 bg-[#101827] border border-card-border rounded-lg text-text focus:outline-none focus:border-accent"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-text-muted mb-1 font-medium">Dialing Mode</label>
              <select
                value={formData.dialing_mode}
                onChange={(e) => setFormData({ ...formData, dialing_mode: e.target.value as DialingMode })}
                className="w-full px-3 py-2 bg-[#101827] border border-card-border rounded-lg text-text focus:outline-none focus:border-accent"
              >
                <option value="PROGRESSIVE">Progressive (1:1 Ratio)</option>
                <option value="PREDICTIVE">Predictive (Pacing Engine)</option>
              </select>
            </div>
            <div>
              <label className="block text-text-muted mb-1 font-medium">Priority (1-5)</label>
              <input
                type="number"
                min="1"
                max="5"
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) || 1 })}
                className="w-full px-3 py-2 bg-[#101827] border border-card-border rounded-lg text-text focus:outline-none focus:border-accent"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-text-muted mb-1 font-medium">Max Attempts Per Borrower</label>
              <input
                type="number"
                min="1"
                max="10"
                value={formData.max_attempts}
                onChange={(e) => setFormData({ ...formData, max_attempts: parseInt(e.target.value) || 3 })}
                className="w-full px-3 py-2 bg-[#101827] border border-card-border rounded-lg text-text focus:outline-none focus:border-accent"
              />
            </div>
            <div>
              <label className="block text-text-muted mb-1 font-medium">Retry Interval (seconds)</label>
              <input
                type="number"
                min="30"
                max="3600"
                value={formData.retry_interval_seconds}
                onChange={(e) =>
                  setFormData({ ...formData, retry_interval_seconds: parseInt(e.target.value) || 300 })
                }
                className="w-full px-3 py-2 bg-[#101827] border border-card-border rounded-lg text-text focus:outline-none focus:border-accent"
              />
            </div>
          </div>

          <div>
            <label className="block text-text-muted mb-1 font-medium">Target Max Abandon Rate</label>
            <input
              type="number"
              step="0.005"
              min="0.01"
              max="0.05"
              value={formData.target_abandon_rate}
              onChange={(e) =>
                setFormData({ ...formData, target_abandon_rate: parseFloat(e.target.value) || 0.03 })
              }
              className="w-full px-3 py-2 bg-[#101827] border border-card-border rounded-lg text-text focus:outline-none focus:border-accent"
            />
            <span className="text-[10px] text-text-subtle mt-1 block">
              Default is 3% (0.03) pursuant to telecom consumer protection rules.
            </span>
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
              Create Campaign
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
