export type AgentStatus =
  | 'OFFLINE'
  | 'AVAILABLE'
  | 'RESERVED'
  | 'DIALING'
  | 'CONNECTED'
  | 'WRAP_UP'
  | 'PAUSED';

export type BorrowerStatus =
  | 'QUEUED'
  | 'RESERVED'
  | 'DIALING'
  | 'CONNECTED'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED';

export type DialingMode = 'PROGRESSIVE' | 'PREDICTIVE';

export type CampaignStatus = 'DRAFT' | 'RUNNING' | 'PAUSED' | 'STOPPED' | 'COMPLETED';

export type CallState =
  | 'INITIATED'
  | 'RINGING'
  | 'ANSWERED'
  | 'CONNECTED'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED';

export type CallOutcome =
  | 'PENDING'
  | 'SUCCESS'
  | 'BUSY'
  | 'UNANSWERED'
  | 'FAILED'
  | 'ABANDONED'
  | 'CANCELLED'
  | 'WORKER_CRASH_ORPHANED';

export type SafetyDecisionType =
  | 'APPROVE'
  | 'REDUCE'
  | 'REJECT'
  | 'FALLBACK_TO_PROGRESSIVE';

export type CircuitState = 'CLOSED' | 'OPEN' | 'HALF_OPEN';

export interface Agent {
  id: string;
  name: string;
  status: AgentStatus;
  current_call_id: string | null;
  total_calls: number;
  total_talk_time_seconds: number;
  average_talk_time: number;
  last_status_change: string | null;
  created_at: string | null;
}

export interface Borrower {
  id: string;
  name: string;
  phone_number: string;
  priority: number;
  campaign_id: string | null;
  status: BorrowerStatus;
  attempt_count: number;
  max_attempts: number;
  eligible_for_call: boolean;
  last_attempted_at: string | null;
  created_at: string | null;
}

export interface Campaign {
  id: string;
  name: string;
  dialing_mode: DialingMode;
  status: CampaignStatus;
  priority: number;
  total_borrowers: number;
  completed_borrowers: number;
  assigned_agents: number;
  max_attempts: number;
  retry_interval_seconds: number;
  target_abandon_rate: number;
  pacing_ratio: number;
  created_at: string | null;
}

export interface Call {
  id: string;
  campaign_id: string;
  borrower_id: string;
  agent_id: string | null;
  provider_id: string;
  provider_call_id: string | null;
  call_state: CallState;
  outcome: CallOutcome;
  ring_time_seconds: number;
  talk_time_seconds: number;
  total_duration_seconds: number;
  initiated_at: string | null;
  ringing_at: string | null;
  answered_at: string | null;
  connected_at: string | null;
  ended_at: string | null;
  error_message: string | null;
  created_at: string | null;
  borrower_name?: string;
  borrower_phone?: string;
  agent_name?: string;
}

export interface SafetyDecision {
  id: string;
  campaign_id: string;
  decision: SafetyDecisionType;
  requested_calls: number;
  approved_calls: number;
  rejected_calls: number;
  available_agents: number;
  reserved_agents: number;
  ringing_calls: number;
  active_calls: number;
  provider_health_score: number;
  reason: string;
  capacity_snapshot: Record<string, any>;
  provider_health_snapshot: Record<string, any>;
  created_at: string | null;
}

export interface SafetyCapacity {
  available_agents: number;
  reserved_agents: number;
  dialing_calls: number;
  ringing_calls: number;
  active_connected_calls: number;
  safe_dialing_capacity: number;
  provider_health_score: number;
  circuit_status: CircuitState;
  is_safe: boolean;
  constraints: string[];
}

export interface PacingStatus {
  campaign_id: string;
  dialing_mode: DialingMode;
  available_agents: number;
  reserved_agents: number;
  connected_calls: number;
  ringing_calls: number;
  historical_answer_rate: number;
  smoothed_answer_rate: number;
  expected_near_term_releases: number;
  risk_factor: number;
  safety_buffer: number;
  requested_dial_count: number;
  formula_explanation: string;
  calculation_details: Record<string, any>;
}

export interface ProviderHealth {
  provider_id: string;
  status: 'ACTIVE' | 'DEGRADED' | 'OFFLINE';
  health_score: number;
  circuit_breaker: {
    name: string;
    state: CircuitState;
    consecutive_failures: number;
    failure_threshold: number;
    total_calls: number;
    total_successes: number;
    total_failures: number;
    failure_rate: number;
    recovery_time_seconds: number;
    seconds_since_state_change: number;
  };
  avg_latency_ms: number;
  outage_mode: boolean;
}

export interface Worker {
  id: string;
  worker_name: string;
  status: 'IDLE' | 'PROCESSING' | 'STOPPED' | 'CRASHED';
  active_job_id: string | null;
  jobs_processed: number;
  jobs_failed: number;
  jobs_recovered: number;
  last_heartbeat: string | null;
}

export interface OverviewKPIs {
  total_agents: number;
  available_agents: number;
  reserved_agents: number;
  active_calls: number;
  connected_calls: number;
  calls_initiated: number;
  agent_utilization_pct: number;
  answer_rate_pct: number;
  average_talk_time_sec: number;
  provider_health_pct: number;
}

export interface TimeSeriesPoint {
  timestamp: string;
  initiated: number;
  answered: number;
  connected: number;
  completed: number;
  failed: number;
}

export interface OverviewData {
  kpis: OverviewKPIs;
  time_series: TimeSeriesPoint[];
  agent_distribution: Record<AgentStatus, number>;
  call_outcomes: Record<string, number>;
  recent_events: Array<{
    id: string;
    event_type: string;
    entity_type: string;
    message: string;
    created_at: string;
  }>;
}

export interface SimulationState {
  is_running: boolean;
  is_paused: boolean;
  ticks_elapsed: number;
  active_scenario_code: string;
  config: {
    num_agents: number;
    num_borrowers: number;
    answer_rate: number;
    average_talk_time_sec: number;
    call_setup_latency_sec: number;
    provider_failure_rate: number;
    num_workers: number;
    dialing_mode: DialingMode;
    provider_id: string;
    tick_speed_ms: number;
  };
}
