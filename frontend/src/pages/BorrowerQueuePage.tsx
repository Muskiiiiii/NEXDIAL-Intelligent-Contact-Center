import React, { useState, useEffect } from 'react';
import { ListOrdered, UserPlus, Upload, RotateCcw, Search, Filter, ShieldCheck, CheckCircle2, AlertCircle } from 'lucide-react';
import { api } from '../services/api';
import { useWebSocketEvent } from '../services/websocket';
import { Borrower, BorrowerStatus } from '../types';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { StatusDot } from '../components/ui/StatusDot';

export const BorrowerQueuePage: React.FC = () => {
  const [borrowers, setBorrowers] = useState<Borrower[]>([]);
  const [summary, setSummary] = useState({ total: 0, queued: 0, conn: 0, comp: 0, fail: 0 });
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  // Modals
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);

  // Add form
  const [formData, setFormData] = useState({
    name: '',
    phone_number: '',
    priority: 1,
    eligible_for_call: true,
  });

  // Import form
  const [csvText, setCsvText] = useState('');

  const loadBorrowers = async () => {
    try {
      const data = await api.getBorrowers();
      setBorrowers(data.borrowers);
      setSummary({
        total: data.total,
        queued: data.queued_count,
        conn: data.connected_count,
        comp: data.completed_count,
        fail: data.failed_count,
      });
    } catch (err) {
      console.error('Failed to load borrowers:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBorrowers();
  }, []);

  useWebSocketEvent('BORROWER_UPDATED', () => loadBorrowers());
  useWebSocketEvent('BORROWER_CREATED', () => loadBorrowers());
  useWebSocketEvent('BORROWERS_IMPORTED', () => loadBorrowers());
  useWebSocketEvent('SIMULATION_TICK', () => loadBorrowers());

  const handleAddBorrower = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createBorrower(formData);
      setIsAddModalOpen(false);
      setFormData({ name: '', phone_number: '', priority: 1, eligible_for_call: true });
      loadBorrowers();
    } catch (err: any) {
      alert(`Error creating borrower: ${err.message}`);
    }
  };

  const handleImportCsv = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!csvText.trim()) return;
    try {
      // Parse simple CSV (Name, Phone, Priority)
      const lines = csvText.trim().split('\n');
      const items = [];
      for (const line of lines) {
        const parts = line.split(',').map((p) => p.trim());
        if (parts.length >= 2) {
          items.push({
            name: parts[0],
            phone_number: parts[1],
            priority: parseInt(parts[2]) || 1,
          });
        }
      }
      if (items.length === 0) {
        alert('No valid CSV rows found. Format: Name, Phone, Priority');
        return;
      }
      const res = await api.importBorrowers(items);
      alert(`Successfully imported ${res.imported_count} borrowers!`);
      setIsImportModalOpen(false);
      setCsvText('');
      loadBorrowers();
    } catch (err: any) {
      alert(`Error importing borrowers: ${err.message}`);
    }
  };

  const handleRetry = async (borrowerId: string) => {
    try {
      await api.retryBorrower(borrowerId);
      loadBorrowers();
    } catch (err: any) {
      alert(`Error retrying borrower: ${err.message}`);
    }
  };

  const filteredBorrowers = borrowers.filter((b) => {
    const matchesSearch =
      !search ||
      b.name.toLowerCase().includes(search.toLowerCase()) ||
      b.phone_number.includes(search) ||
      b.id.includes(search);
    const matchesStatus = statusFilter === 'ALL' || b.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-text tracking-tight flex items-center gap-2.5">
            <ListOrdered size={20} className="text-accent" />
            Borrower Queue & DNC Compliance
          </h1>
          <p className="text-xs text-text-muted mt-0.5">
            Prioritized borrower queues with consent enforcement and automatic retry management
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsImportModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-card border border-card-border hover:border-[#2C3E5F] text-xs text-text transition-colors"
          >
            <Upload size={14} />
            <span>Import CSV</span>
          </button>
          <button
            onClick={() => setIsAddModalOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-xs font-semibold shadow-glow-accent transition-all"
          >
            <UserPlus size={14} />
            <span>Add Borrower</span>
          </button>
        </div>
      </div>

      {/* Summary KPI Strip */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="bg-card border border-card-border p-3 rounded-xl">
          <span className="text-[10px] text-text-muted uppercase font-semibold">Total Queue</span>
          <p className="text-xl font-bold text-text mt-0.5">{summary.total}</p>
        </div>
        <div className="bg-card border border-card-border p-3 rounded-xl">
          <span className="text-[10px] text-text-muted uppercase font-semibold">Queued (Ready)</span>
          <p className="text-xl font-bold text-accent mt-0.5">{summary.queued}</p>
        </div>
        <div className="bg-card border border-card-border p-3 rounded-xl">
          <span className="text-[10px] text-text-muted uppercase font-semibold">Connected</span>
          <p className="text-xl font-bold text-[#38BDF8] mt-0.5">{summary.conn}</p>
        </div>
        <div className="bg-card border border-card-border p-3 rounded-xl">
          <span className="text-[10px] text-text-muted uppercase font-semibold">Completed</span>
          <p className="text-xl font-bold text-success mt-0.5">{summary.comp}</p>
        </div>
        <div className="bg-card border border-card-border p-3 rounded-xl">
          <span className="text-[10px] text-text-muted uppercase font-semibold">Failed / Exhausted</span>
          <p className="text-xl font-bold text-danger mt-0.5">{summary.fail}</p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between bg-card border border-card-border p-3 rounded-xl">
        <div className="relative w-full sm:w-72">
          <Search size={14} className="absolute left-3 top-2.5 text-text-muted" />
          <input
            type="text"
            placeholder="Search borrower name, phone, or ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-[#101827] border border-card-border rounded-lg text-xs text-text placeholder:text-text-subtle focus:outline-none focus:border-accent"
          />
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto">
          {['ALL', 'QUEUED', 'RESERVED', 'DIALING', 'CONNECTED', 'COMPLETED', 'FAILED'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                statusFilter === st
                  ? 'bg-accent text-white'
                  : 'bg-[#101827] text-text-muted hover:text-text border border-card-border'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Borrowers Table */}
      <Card title={`Borrower Records (${filteredBorrowers.length})`}>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-card-border text-text-muted uppercase tracking-wider text-[10px]">
                <th className="py-2.5 px-3">Borrower Name</th>
                <th className="py-2.5 px-3">Phone Number</th>
                <th className="py-2.5 px-3">Priority</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Attempts</th>
                <th className="py-2.5 px-3">Compliance</th>
                <th className="py-2.5 px-3">Last Attempt</th>
                <th className="py-2.5 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-card-border text-text">
              {filteredBorrowers.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-text-muted">
                    No borrower records found.
                  </td>
                </tr>
              ) : (
                filteredBorrowers.map((b) => (
                  <tr key={b.id} className="hover:bg-[#101827] transition-colors">
                    <td className="py-2.5 px-3 font-semibold text-text">
                      {b.name}
                      <span className="block text-[10px] text-text-subtle font-mono">{b.id.substring(0, 8)}...</span>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-accent">{b.phone_number}</td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${
                          b.priority === 1
                            ? 'bg-danger/20 text-danger border border-danger/30'
                            : b.priority === 2
                            ? 'bg-warning/20 text-warning border border-warning/30'
                            : 'bg-card border border-card-border text-text-muted'
                        }`}
                      >
                        P{b.priority}
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      <Badge
                        variant={
                          b.status === 'COMPLETED'
                            ? 'success'
                            : b.status === 'CONNECTED'
                            ? 'accent'
                            : b.status === 'FAILED'
                            ? 'danger'
                            : b.status === 'QUEUED'
                            ? 'neutral'
                            : 'warning'
                        }
                        size="sm"
                      >
                        <StatusDot status={b.status} size="sm" />
                        {b.status}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px]">
                      {b.attempt_count} / {b.max_attempts}
                    </td>
                    <td className="py-2.5 px-3">
                      {b.eligible_for_call ? (
                        <span className="text-success flex items-center gap-1 text-[11px]">
                          <ShieldCheck size={13} /> Consent Verified
                        </span>
                      ) : (
                        <span className="text-danger flex items-center gap-1 text-[11px]">
                          <AlertCircle size={13} /> DNC Blocked
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-[11px] text-text-muted font-mono">
                      {b.last_attempted_at ? new Date(b.last_attempted_at).toLocaleTimeString() : 'Never'}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      {b.status === 'FAILED' && (
                        <button
                          onClick={() => handleRetry(b.id)}
                          className="flex items-center gap-1 px-2.5 py-1 rounded bg-[#101827] hover:bg-accent/20 text-accent border border-card-border text-[11px] transition-colors"
                        >
                          <RotateCcw size={11} />
                          <span>Retry</span>
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Add Borrower Modal */}
      <Modal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        title="Add Borrower to Queue"
        subtitle="Record will be entered into active queue subject to campaign priority"
      >
        <form onSubmit={handleAddBorrower} className="space-y-4 text-xs">
          <div>
            <label className="block text-text-muted mb-1 font-medium">Borrower Full Name</label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g. Johnathan Doe"
              className="w-full px-3 py-2 bg-[#101827] border border-card-border rounded-lg text-text focus:outline-none focus:border-accent"
            />
          </div>

          <div>
            <label className="block text-text-muted mb-1 font-medium">Phone Number (E.164 or Standard)</label>
            <input
              type="text"
              required
              value={formData.phone_number}
              onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
              placeholder="e.g. +1-800-555-0199"
              className="w-full px-3 py-2 bg-[#101827] border border-card-border rounded-lg text-text focus:outline-none focus:border-accent"
            />
          </div>

          <div>
            <label className="block text-text-muted mb-1 font-medium">Priority (1 = Highest, 5 = Lowest)</label>
            <select
              value={formData.priority}
              onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) || 1 })}
              className="w-full px-3 py-2 bg-[#101827] border border-card-border rounded-lg text-text focus:outline-none focus:border-accent"
            >
              <option value="1">Priority 1 (Urgent / VIP)</option>
              <option value="2">Priority 2 (High)</option>
              <option value="3">Priority 3 (Normal)</option>
              <option value="4">Priority 4 (Low)</option>
              <option value="5">Priority 5 (Deferred)</option>
            </select>
          </div>

          <div className="flex items-center gap-2 pt-2">
            <input
              type="checkbox"
              id="consent"
              checked={formData.eligible_for_call}
              onChange={(e) => setFormData({ ...formData, eligible_for_call: e.target.checked })}
              className="rounded bg-[#101827] border-card-border text-accent focus:ring-0"
            />
            <label htmlFor="consent" className="text-text font-medium text-xs">
              Confirm Borrower Consent & Do-Not-Call (DNC) Clearance
            </label>
          </div>

          <div className="pt-3 border-t border-card-border flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setIsAddModalOpen(false)}
              className="px-4 py-2 rounded-lg bg-[#101827] text-text-muted hover:text-text border border-card-border transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white font-semibold shadow-glow-accent transition-all"
            >
              Enqueue Borrower
            </button>
          </div>
        </form>
      </Modal>

      {/* CSV Import Modal */}
      <Modal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        title="Batch Import Borrowers (CSV)"
        subtitle="Paste CSV text with columns: Name, Phone Number, Priority"
      >
        <form onSubmit={handleImportCsv} className="space-y-4 text-xs">
          <div>
            <label className="block text-text-muted mb-1 font-medium">CSV Data Format</label>
            <p className="text-[11px] text-text-subtle mb-2">
              One record per line: <code className="bg-[#101827] px-1.5 py-0.5 rounded text-accent font-mono">Name, +1-555-0101, 1</code>
            </p>
            <textarea
              rows={8}
              value={csvText}
              onChange={(e) => setCsvText(e.target.value)}
              placeholder="Marcus Vance, +1-800-555-0120, 1&#10;Elena Rostova, +1-800-555-0121, 2&#10;Liam O'Connor, +1-800-555-0122, 1"
              className="w-full p-3 bg-[#101827] border border-card-border rounded-lg text-text font-mono text-[11px] focus:outline-none focus:border-accent"
            />
          </div>

          <div className="pt-3 border-t border-card-border flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setIsImportModalOpen(false)}
              className="px-4 py-2 rounded-lg bg-[#101827] text-text-muted hover:text-text border border-card-border transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white font-semibold shadow-glow-accent transition-all"
            >
              Import Records
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
