import {
  Agent, Borrower, Campaign, Call, SafetyDecision, SafetyCapacity,
  PacingStatus, ProviderHealth, Worker, OverviewData, TimeSeriesPoint, SimulationState
} from '../types';

const API_BASE = '/api/v1';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });
  if (!res.ok) {
    let errorDetail = res.statusText;
    try {
      const err = await res.json();
      errorDetail = err.detail || errorDetail;
    } catch (_) {}
    throw new Error(errorDetail);
  }
  return res.json();
}

export const api = {
  // Analytics & Dashboard
  getOverview: () => fetchJson<OverviewData>(`${API_BASE}/analytics/overview`),
  getTimeSeries: (points = 12) => fetchJson<TimeSeriesPoint[]>(`${API_BASE}/analytics/timeseries?points=${points}`),

  // Agents
  getAgents: (status?: string) => {
    const q = status ? `?status=${status}` : '';
    return fetchJson<{ agents: Agent[]; total: number; available_count: number; reserved_count: number; connected_count: number; offline_count: number }>(`${API_BASE}/agents${q}`);
  },
  createAgent: (name: string, status = 'AVAILABLE') =>
    fetchJson<Agent>(`${API_BASE}/agents`, { method: 'POST', body: JSON.stringify({ name, status }) }),
  updateAgentStatus: (agentId: string, status: string) =>
    fetchJson<Agent>(`${API_BASE}/agents/${agentId}/status`, { method: 'PATCH', body: JSON.stringify({ status }) }),
  pauseAgent: (agentId: string) => fetchJson<Agent>(`${API_BASE}/agents/${agentId}/pause`, { method: 'POST' }),
  resumeAgent: (agentId: string) => fetchJson<Agent>(`${API_BASE}/agents/${agentId}/resume`, { method: 'POST' }),
  bringAgentOnline: (agentId: string) => fetchJson<Agent>(`${API_BASE}/agents/${agentId}/online`, { method: 'POST' }),
  takeAgentOffline: (agentId: string) => fetchJson<Agent>(`${API_BASE}/agents/${agentId}/offline`, { method: 'POST' }),

  // Borrowers
  getBorrowers: (params?: { campaign_id?: string; status?: string; search?: string; skip?: number; limit?: number }) => {
    const query = new URLSearchParams(params as any).toString();
    return fetchJson<{ borrowers: Borrower[]; total: number; queued_count: number; connected_count: number; completed_count: number; failed_count: number }>(`${API_BASE}/borrowers?${query}`);
  },
  createBorrower: (data: { name: string; phone_number: string; priority?: number; campaign_id?: string; eligible_for_call?: boolean }) =>
    fetchJson<Borrower>(`${API_BASE}/borrowers`, { method: 'POST', body: JSON.stringify(data) }),
  importBorrowers: (items: Array<{ name: string; phone_number: string; priority?: number }>, campaign_id?: string) =>
    fetchJson<{ status: string; imported_count: number }>(`${API_BASE}/borrowers/import${campaign_id ? `?campaign_id=${campaign_id}` : ''}`, {
      method: 'POST',
      body: JSON.stringify(items)
    }),
  retryBorrower: (borrowerId: string) => fetchJson<Borrower>(`${API_BASE}/borrowers/${borrowerId}/retry`, { method: 'POST' }),

  // Campaigns
  getCampaigns: () => fetchJson<Campaign[]>(`${API_BASE}/campaigns`),
  createCampaign: (data: Partial<Campaign>) => fetchJson<Campaign>(`${API_BASE}/campaigns`, { method: 'POST', body: JSON.stringify(data) }),
  startCampaign: (campaignId: string) => fetchJson<Campaign>(`${API_BASE}/campaigns/${campaignId}/start`, { method: 'POST' }),
  pauseCampaign: (campaignId: string) => fetchJson<Campaign>(`${API_BASE}/campaigns/${campaignId}/pause`, { method: 'POST' }),
  resumeCampaign: (campaignId: string) => fetchJson<Campaign>(`${API_BASE}/campaigns/${campaignId}/resume`, { method: 'POST' }),
  stopCampaign: (campaignId: string) => fetchJson<Campaign>(`${API_BASE}/campaigns/${campaignId}/stop`, { method: 'POST' }),

  // Calls
  getCalls: (params?: { state?: string; campaign_id?: string; skip?: number; limit?: number }) => {
    const query = new URLSearchParams(params as any).toString();
    return fetchJson<{ calls: Call[]; total: number; active_count: number; completed_count: number; failed_count: number }>(`${API_BASE}/calls?${query}`);
  },
  getLiveCalls: (limit = 30) => fetchJson<Call[]>(`${API_BASE}/calls/live?limit=${limit}`),

  // Safety
  getSafetyCapacity: () => fetchJson<SafetyCapacity>(`${API_BASE}/safety/capacity`),
  getSafetyDecisions: (limit = 25) => fetchJson<SafetyDecision[]>(`${API_BASE}/safety/decisions?limit=${limit}`),
  evaluateSafety: (campaignId: string, requestedCalls: number, dialingMode = 'PROGRESSIVE') =>
    fetchJson<SafetyDecision>(`${API_BASE}/safety/evaluate?campaign_id=${campaignId}&requested_calls=${requestedCalls}&dialing_mode=${dialingMode}`, { method: 'POST' }),

  // Pacing
  getPacingStatus: (campaignId?: string, riskFactor = 0.15) => {
    const q = campaignId ? `?campaign_id=${campaignId}&risk_factor=${riskFactor}` : `?risk_factor=${riskFactor}`;
    return fetchJson<PacingStatus>(`${API_BASE}/pacing/status${q}`);
  },

  // Providers
  getProviders: () => fetchJson<ProviderHealth[]>(`${API_BASE}/providers`),
  resetProviderCircuit: (providerId: string) => fetchJson<{ status: string; message: string }>(`${API_BASE}/providers/${providerId}/reset-circuit`, { method: 'POST' }),

  // Workers
  getWorkers: () => fetchJson<Worker[]>(`${API_BASE}/workers`),
  crashWorker: (name: string) => fetchJson<any>(`${API_BASE}/workers/${name}/crash`, { method: 'POST' }),
  recoverWorker: (name: string) => fetchJson<any>(`${API_BASE}/workers/${name}/recover`, { method: 'POST' }),

  // Simulation
  getSimulationState: () => fetchJson<SimulationState>(`${API_BASE}/simulation/state`),
  startSimulation: (config?: any) => fetchJson<any>(`${API_BASE}/simulation/start`, { method: 'POST', body: JSON.stringify(config || {}) }),
  pauseSimulation: () => fetchJson<any>(`${API_BASE}/simulation/pause`, { method: 'POST' }),
  resumeSimulation: () => fetchJson<any>(`${API_BASE}/simulation/resume`, { method: 'POST' }),
  resetSimulation: () => fetchJson<any>(`${API_BASE}/simulation/reset`, { method: 'POST' }),
  stepSimulation: () => fetchJson<any>(`${API_BASE}/simulation/step`, { method: 'POST' }),
  applyPreset: (code: string) => fetchJson<any>(`${API_BASE}/simulation/preset/${code}`, { method: 'POST' }),
  updateSimulationConfig: (config: any) => fetchJson<any>(`${API_BASE}/simulation/config`, { method: 'POST', body: JSON.stringify(config) }),

  // Failure Injection
  injectFailure: (type: string, payload?: Record<string, any>) =>
    fetchJson<any>(`${API_BASE}/failures/inject`, { method: 'POST', body: JSON.stringify({ type, ...(payload || {}) }) }),

  // Architecture
  getArchitectureComponents: () => fetchJson<{ nodes: any[]; edges: any[] }>(`${API_BASE}/architecture/components`),
};
