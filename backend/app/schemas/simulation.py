from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from app.models.enums import DialingMode

class SimulationConfig(BaseModel):
    num_agents: int = Field(default=20, ge=1, le=500)
    num_borrowers: int = Field(default=100, ge=1, le=5000)
    answer_rate: float = Field(default=0.45, ge=0.05, le=1.0)
    average_talk_time_sec: float = Field(default=60.0, ge=5.0, le=600.0)
    call_setup_latency_sec: float = Field(default=1.5, ge=0.2, le=10.0)
    provider_failure_rate: float = Field(default=0.05, ge=0.0, le=0.9)
    num_workers: int = Field(default=3, ge=1, le=10)
    dialing_mode: DialingMode = DialingMode.PROGRESSIVE
    provider_id: str = "PROVIDER_A"
    tick_speed_ms: int = Field(default=1000, ge=200, le=5000)

class SimulationPreset(BaseModel):
    id: str
    code: str
    name: str
    description: str
    config: SimulationConfig

class SimulationStateResponse(BaseModel):
    is_running: bool
    is_paused: bool
    ticks_elapsed: int
    active_scenario_code: Optional[str] = None
    config: SimulationConfig
    agents_count: int
    borrowers_queued: int
    calls_initiated: int
    calls_connected: int
    calls_completed: int
    calls_failed: int
    current_agent_utilization: float
    current_answer_rate: float
