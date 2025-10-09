#!/usr/bin/env python3

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import json
import uvicorn
from pathlib import Path

app = FastAPI(title="SlickNXT - Node-RED Interface for NXT")

# Store active flows and their states
flows: Dict[str, Any] = {}
node_states: Dict[str, Dict] = {}

class NodeData(BaseModel):
    id: str
    type: str
    position: Dict[str, float]
    data: Dict[str, Any]

class Edge(BaseModel):
    id: str
    source: str
    target: str
    sourceHandle: Optional[str] = None
    targetHandle: Optional[str] = None

class Flow(BaseModel):
    nodes: List[NodeData]
    edges: List[Edge]

@app.get("/")
async def root():
    """Serve the main HTML page"""
    return FileResponse("app/static/index.html")

@app.post("/api/flows/save")
async def save_flow(flow: Flow):
    """Save the current flow configuration"""
    flows["current"] = flow.dict()
    return {"status": "success", "message": "Flow saved successfully"}

@app.get("/api/flows/load")
async def load_flow():
    """Load the saved flow configuration"""
    return flows.get("current", {"nodes": [], "edges": []})

@app.post("/api/nodes/execute")
async def execute_node(node_id: str, inputs: Dict[str, Any]):
    """Execute a node with given inputs"""
    # This will simulate motor node execution
    # In real implementation, this would interface with nxt-python
    
    if node_id not in node_states:
        node_states[node_id] = {}
    
    # Simulate motor node execution
    outputs = {
        "actual_on_off": inputs.get("on_off", False),
        "actual_speed": inputs.get("speed", 0),
        "actual_forward": inputs.get("forward", True)
    }
    
    node_states[node_id] = {
        "inputs": inputs,
        "outputs": outputs
    }
    
    return {
        "status": "success",
        "node_id": node_id,
        "outputs": outputs
    }

@app.get("/api/nodes/{node_id}/state")
async def get_node_state(node_id: str):
    """Get the current state of a node"""
    return node_states.get(node_id, {})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time node state updates"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "execute_node":
                node_id = message["node_id"]
                inputs = message["inputs"]
                
                # Execute node and get outputs
                outputs = {
                    "actual_on_off": inputs.get("on_off", False),
                    "actual_speed": inputs.get("speed", 0),
                    "actual_forward": inputs.get("forward", True)
                }
                
                node_states[node_id] = {
                    "inputs": inputs,
                    "outputs": outputs
                }
                
                # Send back the results
                await websocket.send_text(json.dumps({
                    "type": "node_state_update",
                    "node_id": node_id,
                    "outputs": outputs
                }))
                
    except WebSocketDisconnect:
        print("Client disconnected")

# Mount static files directory
app.mount("/static", StaticFiles(directory="app/static"), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
