import React, { useState, useEffect } from 'react';
import { Network, Database, ShieldCheck, Cpu, ArrowDown, ArrowRight, Layers, Radio, Server, Code, AlertTriangle } from 'lucide-react';
import { api } from '../services/api';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';

export const SystemArchitecturePage: React.FC = () => {
  const [components, setComponents] = useState<any[]>([]);
  const [selectedNode, setSelectedNode] = useState<any | null>(null);

  useEffect(() => {
    api.getArchitectureComponents().then((data) => {
      setComponents(data.nodes);
      if (data.nodes.length > 2) {
        // default select Safety Controller
        setSelectedNode(data.nodes.find((n: any) => n.id === 'safety_controller') || data.nodes[0]);
      }
    });
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-text tracking-tight flex items-center gap-2.5">
            <Network size={20} className="text-accent" />
            System Architecture & Distributed Pipeline
          </h1>
          <p className="text-xs text-text-muted mt-0.5">
            Clean Modular Monolith: Campaign Management, Independent Safety Controller, and Carrier Abstraction
          </p>
        </div>
        <Badge variant="accent" size="md">
          <span>CLEAN MODULAR MONOLITH</span>
        </Badge>
      </div>

      {/* Interactive Visual Flow Diagram */}
      <Card title="Interactive Pipeline Flow (Click components to inspect responsibilities & failure handling)">
        <div className="p-4 bg-[#090D18] rounded-xl border border-card-border overflow-x-auto">
          {/* Main Dialing Pipeline */}
          <div className="min-w-[700px] flex flex-col items-center gap-4">
            {/* Step 1: Campaign Manager */}
            {(() => {
              const node = components.find((n) => n.id === 'campaign_manager');
              const isSel = selectedNode?.id === 'campaign_manager';
              return (
                <div
                  onClick={() => setSelectedNode(node)}
                  className={`w-80 p-3 rounded-xl border cursor-pointer transition-all text-center ${
                    isSel
                      ? 'bg-accent/20 border-accent shadow-glow-accent'
                      : 'bg-[#151F30] border-card-border hover:border-[#2C3E5F]'
                  }`}
                >
                  <span className="text-[10px] text-accent uppercase font-mono font-bold block">Layer 1: Orchestration</span>
                  <span className="text-xs font-bold text-text">Campaign Manager</span>
                  <span className="text-[10px] text-text-muted block mt-0.5">Priorities, Abandon Targets, Worker Leases</span>
                </div>
              );
            })()}

            <ArrowDown size={18} className="text-accent" />

            {/* Step 2: Pacing Engine */}
            {(() => {
              const node = components.find((n) => n.id === 'pacing_engine');
              const isSel = selectedNode?.id === 'pacing_engine';
              return (
                <div
                  onClick={() => setSelectedNode(node)}
                  className={`w-80 p-3 rounded-xl border cursor-pointer transition-all text-center ${
                    isSel
                      ? 'bg-accent/20 border-accent shadow-glow-accent'
                      : 'bg-[#151F30] border-card-border hover:border-[#2C3E5F]'
                  }`}
                >
                  <span className="text-[10px] text-accent uppercase font-mono font-bold block">Layer 2: Algorithmic Pacing</span>
                  <span className="text-xs font-bold text-text">Pacing Engine (Progressive / Predictive)</span>
                  <span className="text-[10px] text-text-muted block mt-0.5">Formula Calculations (NEVER directly calls)</span>
                </div>
              );
            })()}

            <ArrowDown size={18} className="text-accent" />

            {/* Step 3: Safety Controller (THE CRITICAL GATE) */}
            {(() => {
              const node = components.find((n) => n.id === 'safety_controller');
              const isSel = selectedNode?.id === 'safety_controller';
              return (
                <div
                  onClick={() => setSelectedNode(node)}
                  className={`w-96 p-4 rounded-xl border-2 cursor-pointer transition-all text-center relative ${
                    isSel
                      ? 'bg-success/20 border-success shadow-glow-success'
                      : 'bg-[#151F30] border-success/60 hover:border-success'
                  }`}
                >
                  <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded bg-success text-[#090D18] text-[9px] font-extrabold tracking-wider uppercase">
                    MANDATORY INDEPENDENT GATE
                  </div>
                  <span className="text-[10px] text-success uppercase font-mono font-bold block">Layer 3: Governance</span>
                  <span className="text-sm font-extrabold text-text flex items-center justify-center gap-1.5">
                    <ShieldCheck size={16} className="text-success" />
                    Safety Controller
                  </span>
                  <span className="text-[10px] text-text-muted block mt-1">
                    Enforces Zero Abandonment: APPROVE | REDUCE | REJECT | FALLBACK
                  </span>
                </div>
              );
            })()}

            <ArrowDown size={18} className="text-success" />

            {/* Step 4: Call Allocator */}
            {(() => {
              const node = components.find((n) => n.id === 'call_allocator');
              const isSel = selectedNode?.id === 'call_allocator';
              return (
                <div
                  onClick={() => setSelectedNode(node)}
                  className={`w-80 p-3 rounded-xl border cursor-pointer transition-all text-center ${
                    isSel
                      ? 'bg-accent/20 border-accent shadow-glow-accent'
                      : 'bg-[#151F30] border-card-border hover:border-[#2C3E5F]'
                  }`}
                >
                  <span className="text-[10px] text-accent uppercase font-mono font-bold block">Layer 4: Atomic Execution</span>
                  <span className="text-xs font-bold text-text">Call Allocator</span>
                  <span className="text-[10px] text-text-muted block mt-0.5">Atomic Reservations & Transactional Rollbacks</span>
                </div>
              );
            })()}

            <ArrowDown size={18} className="text-accent" />

            {/* Step 5: Telecom Abstraction Layer */}
            {(() => {
              const node = components.find((n) => n.id === 'telecom_layer');
              const isSel = selectedNode?.id === 'telecom_layer';
              return (
                <div
                  onClick={() => setSelectedNode(node)}
                  className={`w-80 p-3 rounded-xl border cursor-pointer transition-all text-center ${
                    isSel
                      ? 'bg-accent/20 border-accent shadow-glow-accent'
                      : 'bg-[#151F30] border-card-border hover:border-[#2C3E5F]'
                  }`}
                >
                  <span className="text-[10px] text-accent uppercase font-mono font-bold block">Layer 5: Carrier Interface</span>
                  <span className="text-xs font-bold text-text">Telecom Provider Abstraction</span>
                  <span className="text-[10px] text-text-muted block mt-0.5">Circuit Breakers (CLOSED, OPEN, HALF_OPEN)</span>
                </div>
              );
            })()}

            {/* Providers Dual Split */}
            <div className="flex items-center gap-6 mt-1">
              <div className="w-44 p-2.5 rounded-lg bg-[#101827] border border-card-border text-center">
                <span className="text-[10px] text-success font-bold block">Mock Provider A</span>
                <span className="text-[9px] text-text-muted">High Reliability (75ms)</span>
              </div>
              <div className="w-44 p-2.5 rounded-lg bg-[#101827] border border-card-border text-center">
                <span className="text-[10px] text-warning font-bold block">Mock Provider B</span>
                <span className="text-[9px] text-text-muted">Simulated Jitter & OOO</span>
              </div>
            </div>

            {/* Infrastructure Tier Below */}
            <div className="w-full pt-4 mt-2 border-t border-card-border flex items-center justify-center gap-4 text-xs">
              {['database', 'worker_pool', 'event_processor'].map((id) => {
                const node = components.find((n) => n.id === id);
                const isSel = selectedNode?.id === id;
                return (
                  <button
                    key={id}
                    onClick={() => setSelectedNode(node)}
                    className={`px-4 py-2 rounded-lg border text-left transition-all ${
                      isSel
                        ? 'bg-accent/20 border-accent text-white shadow-glow-accent'
                        : 'bg-[#151F30] border-card-border text-text-muted hover:text-text'
                    }`}
                  >
                    <span className="font-semibold block text-xs">{node?.name}</span>
                    <span className="text-[10px] text-text-subtle font-mono">{node?.layer}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </Card>

      {/* Component Inspector Panel */}
      {selectedNode && (
        <Card
          title={`Component Inspector: ${selectedNode.name}`}
          subtitle={`Layer: ${selectedNode.layer}`}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <span className="text-[10px] text-text-muted uppercase font-semibold block mb-1">
                Primary Responsibility
              </span>
              <p className="p-3 bg-[#101827] rounded-lg border border-card-border text-text leading-relaxed">
                {selectedNode.responsibility}
              </p>

              <span className="text-[10px] text-text-muted uppercase font-semibold block mt-3 mb-1">
                Failure Handling & Resilience
              </span>
              <p className="p-3 bg-[#101827] rounded-lg border border-card-border text-warning leading-relaxed flex items-start gap-2">
                <AlertTriangle size={14} className="mt-0.5 flex-shrink-0" />
                {selectedNode.failure_handling}
              </p>
            </div>

            <div>
              <span className="text-[10px] text-text-muted uppercase font-semibold block mb-1">
                Inputs & Ingestion
              </span>
              <div className="p-2.5 bg-[#101827] rounded-lg border border-card-border space-y-1 mb-3">
                {selectedNode.inputs.map((inp: string, i: number) => (
                  <span key={i} className="block text-text-muted text-[11px]">• {inp}</span>
                ))}
              </div>

              <span className="text-[10px] text-text-muted uppercase font-semibold block mb-1">
                Outputs & Dispatches
              </span>
              <div className="p-2.5 bg-[#101827] rounded-lg border border-card-border space-y-1 mb-3">
                {selectedNode.outputs.map((out: string, i: number) => (
                  <span key={i} className="block text-text-muted text-[11px]">• {out}</span>
                ))}
              </div>

              <div className="p-2 bg-[#101827] rounded-lg border border-card-border flex items-center justify-between text-[11px] font-mono">
                <span className="text-text-muted">Backend Module:</span>
                <span className="text-accent">{selectedNode.backend_module}</span>
              </div>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};
