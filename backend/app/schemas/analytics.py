from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class TimeSeriesPoint(BaseModel):
    timestamp: str
    initiated: int = 0
    answered: int = 0
    connected: int = 0
    completed: int = 0
    failed: int = 0

class AgentDistribution(BaseModel):
    available: int = 0
    reserved: int = 0
    dialing: int = 0
    connected: int = 0
    wrap_up: int = 0
    paused: int = 0
    offline: int = 0

class CallOutcomeDistribution(BaseModel):
    success: int = 0
    busy: int = 0
    unanswered: int = 0
    failed: int = 0
    abandoned: int = 0
    cancelled: int = 0

class OverviewMetrics(BaseModel):
    total_agents: int = 0
    available_agents: int = 0
    reserved_agents: int = 0
    active_calls: int = 0
    connected_calls: int = 0
    calls_initiated: int = 0
    agent_utilization_pct: float = 0.0
    answer_rate_pct: float = 0.0
    average_talk_time_sec: float = 0.0
    provider_health_pct: float = 100.0

class AnalyticsOverviewResponse(BaseModel):
    kpis: OverviewMetrics
    time_series: List[TimeSeriesPoint]
    agent_distribution: AgentDistribution
    call_outcomes: CallOutcomeDistribution
    recent_events: List[Dict[str, Any]]
