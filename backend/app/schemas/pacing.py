from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.models.enums import DialingMode

class PacingCalculationResponse(BaseModel):
    campaign_id: str
    dialing_mode: DialingMode
    available_agents: int
    reserved_agents: int
    connected_calls: int
    ringing_calls: int
    historical_answer_rate: float
    smoothed_answer_rate: float
    expected_near_term_releases: float
    risk_factor: float
    safety_buffer: float
    requested_dial_count: int
    formula_explanation: str
    calculation_details: Dict[str, Any]
