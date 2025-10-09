#!/usr/bin/env python3

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import json
import uvicorn
from pathlib import Path
from datetime import datetime
import os

app = FastAPI(title="SlickNXT - Node-RED Interface for NXT")

# Create flows directory if it doesn't exist
FLOWS_DIR = Path("flows")
FLOWS_DIR.mkdir(exist_ok=True)

# Store active node states
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

class SaveFlowRequest(BaseModel):
    name: str
    flow: Flow
    overwrite: bool = False

@app.get("/")
async def root():
    """Serve the main HTML page"""
    return FileResponse("app/static/index.html")

@app.get("/api/flows/list")
async def list_flows():
    """List all available flows sorted by modification time"""
    flows = []
    for flow_file in FLOWS_DIR.glob("*.json"):
        stat = flow_file.stat()
        flows.append({
            "name": flow_file.stem,
            "filename": flow_file.name,
            "modified": stat.st_mtime,
            "size": stat.st_size
        })
    
    # Sort by modification time (newest first)
    flows.sort(key=lambda x: x["modified"], reverse=True)
    return {"flows": flows}

@app.post("/api/flows/save")
async def save_flow(request: SaveFlowRequest):
    """Save a flow to a JSON file"""
    # Sanitize filename
    safe_name = "".join(c for c in request.name if c.isalnum() or c in (' ', '-', '_')).strip()
    if not safe_name:
        raise HTTPException(status_code=400, detail="Invalid flow name")
    
    flow_path = FLOWS_DIR / f"{safe_name}.json"
    
    # Check if file exists and overwrite flag
    if flow_path.exists() and not request.overwrite:
        raise HTTPException(
            status_code=409, 
            detail=f"Flow '{safe_name}' already exists. Set overwrite=true to replace it."
        )
    
    # Save flow to file
    flow_data = request.flow.dict()
    flow_data["metadata"] = {
        "name": safe_name,
        "created": datetime.now().isoformat(),
        "modified": datetime.now().isoformat()
    }
    
    with open(flow_path, 'w') as f:
        json.dump(flow_data, f, indent=2)
    
    return {
        "status": "success", 
        "message": f"Flow '{safe_name}' saved successfully",
        "filename": flow_path.name
    }

@app.get("/api/flows/load/{filename}")
async def load_flow(filename: str):
    """Load a flow from a JSON file"""
    flow_path = FLOWS_DIR / filename
    
    if not flow_path.exists():
        raise HTTPException(status_code=404, detail=f"Flow '{filename}' not found")
    
    try:
        with open(flow_path, 'r') as f:
            flow_data = json.load(f)
        return flow_data
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Invalid JSON in flow '{filename}'")

@app.delete("/api/flows/delete/{filename}")
async def delete_flow(filename: str):
    """Delete a flow file"""
    flow_path = FLOWS_DIR / filename
    
    if not flow_path.exists():
        raise HTTPException(status_code=404, detail=f"Flow '{filename}' not found")
    
    try:
        flow_path.unlink()
        return {
            "status": "success",
            "message": f"Flow '{filename}' deleted successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting flow: {str(e)}")

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
