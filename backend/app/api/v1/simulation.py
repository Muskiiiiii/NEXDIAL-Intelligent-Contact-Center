from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.services.simulation_engine import simulation_engine

router = APIRouter(prefix="/simulation", tags=["Simulation Lab"])

@router.get("/state")
async def get_simulation_state():
    return simulation_engine.get_state()

@router.post("/start")
async def start_simulation(payload: Dict[str, Any] = {}):
    await simulation_engine.start(payload)
    return {"status": "STARTED", "state": simulation_engine.get_state()}

@router.post("/pause")
async def pause_simulation():
    await simulation_engine.pause()
    return {"status": "PAUSED", "state": simulation_engine.get_state()}

@router.post("/resume")
async def resume_simulation():
    await simulation_engine.resume()
    return {"status": "RESUMED", "state": simulation_engine.get_state()}

@router.post("/reset")
async def reset_simulation():
    await simulation_engine.reset()
    return {"status": "RESET", "state": simulation_engine.get_state()}

@router.post("/step")
async def step_simulation():
    await simulation_engine.step_forward()
    return {"status": "STEPPED", "state": simulation_engine.get_state()}

@router.post("/preset/{scenario_code}")
async def apply_preset(scenario_code: str):
    if scenario_code not in ("SCENARIO_A", "SCENARIO_B", "SCENARIO_C", "SCENARIO_D"):
        raise HTTPException(status_code=400, detail="Invalid scenario code. Allowed: SCENARIO_A, SCENARIO_B, SCENARIO_C, SCENARIO_D")
    await simulation_engine.apply_preset(scenario_code)
    return {"status": "PRESET_APPLIED", "scenario": scenario_code, "state": simulation_engine.get_state()}

@router.post("/config")
async def update_simulation_config(config: Dict[str, Any]):
    simulation_engine.apply_config(config)
    return {"status": "CONFIG_UPDATED", "state": simulation_engine.get_state()}
