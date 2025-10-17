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
import asyncio
import logging

from execution_engine import FlowExecutor
from hardware_manager import HardwareManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SlickNXT - Node-RED Interface for NXT")

# Create flows directory if it doesn't exist
FLOWS_DIR = Path("flows")
FLOWS_DIR.mkdir(exist_ok=True)

# Global hardware manager
hardware_manager = HardwareManager()

# Global flow executor with hardware manager
executor = FlowExecutor(hardware_manager)
executor_task: Optional[asyncio.Task] = None

# WebSocket connections for state updates
active_connections: List[WebSocket] = []

# Current flow state (shared across all clients)
current_flow: Dict[str, Any] = {
    "nodes": [],
    "edges": []
}

# Execution state (shared across all clients)
is_executing: bool = False

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

@app.on_event("startup")
async def startup_event():
    """Start hardware monitoring on application startup"""
    # Register hardware change callback
    hardware_manager.add_change_callback(on_hardware_change)
    
    # Start monitoring
    hardware_manager.start_monitoring()
    logger.info("Hardware monitoring started")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    hardware_manager.stop_monitoring()
    hardware_manager.disconnect_brick()
    logger.info("Hardware monitoring stopped")


@app.get("/")
async def root():
    """Serve the main HTML page"""
    return FileResponse("app/static/index.html")

@app.get("/api/hardware/config")
async def get_hardware_config():
    """Get current hardware configuration"""
    return hardware_manager.get_hardware_config()


@app.post("/api/hardware/rescan")
async def rescan_hardware():
    """Manually trigger hardware detection and broadcast"""
    logger.info("Manual hardware rescan requested")
    
    # Force reconnect if needed
    if not hardware_manager.is_connected:
        hardware_manager.connect_brick()
    
    # Detect motors
    motors = hardware_manager.detect_motors()
    hardware_manager.connected_motors = motors
    
    # Get config and broadcast
    config = hardware_manager.get_hardware_config()
    logger.info(f"Manual scan result: {config}")
    
    # Broadcast to all clients
    await broadcast_hardware_config(config)
    
    return {"status": "scanned", "config": config}


@app.post("/api/hardware/sensors/config")
async def set_sensor_config(config: Dict[str, str]):
    """Set manual sensor configuration"""
    logger.info(f"Received sensor configuration: {config}")
    
    # Update hardware manager
    hardware_manager.set_manual_sensor_config(config)
    
    # Re-detect sensors with new config
    hardware_manager.connected_sensors = hardware_manager.detect_sensors()
    
    # Get updated config and broadcast
    hw_config = hardware_manager.get_hardware_config()
    await broadcast_hardware_config(hw_config)
    
    return {"status": "configured", "sensors": hardware_manager.connected_sensors}


@app.get("/api/flow/current")
async def get_current_flow():
    """Get the current flow state"""
    return current_flow

@app.get("/api/flow/execution-state")
async def get_execution_state():
    """Get the current execution state"""
    return {"isExecuting": is_executing}

@app.post("/api/flow/update")
async def update_current_flow(flow: Flow):
    """Update the current flow and broadcast to all clients"""
    global current_flow
    
    current_flow = flow.dict()
    
    # Reload into executor
    executor.load_flow(current_flow)
    
    # Broadcast initial state for all nodes
    for node_id, node in executor.nodes.items():
        await broadcast_state_update(node_id, node.get_state())
    
    # Broadcast flow update to all clients
    await broadcast_flow_update(current_flow)
    
    return {"status": "updated", "message": f"Flow updated with {len(flow.nodes)} nodes"}

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

@app.post("/api/flow/start")
async def start_flow_execution():
    """Start executing the current flow"""
    global executor_task, is_executing
    
    if executor_task and not executor_task.done():
        return {"status": "already_running", "message": "Flow is already executing"}
    
    # Register state update callback (only if not already registered)
    if broadcast_state_update not in executor.state_callbacks:
        executor.add_state_callback(broadcast_state_update)
    
    # Start execution in background
    try:
        executor_task = asyncio.create_task(executor.run())
        is_executing = True
        
        # Broadcast execution state to all clients
        await broadcast_execution_state(True)
        
        return {"status": "started", "message": "Flow execution started"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to start: {str(e)}"}


@app.post("/api/flow/stop")
async def stop_flow_execution():
    """Stop executing the current flow"""
    global executor_task, is_executing
    
    if not executor_task or executor_task.done():
        return {"status": "not_running", "message": "Flow is not executing"}
    
    executor.stop()
    await executor_task
    executor_task = None
    is_executing = False
    
    # Broadcast execution state to all clients
    await broadcast_execution_state(False)
    
    return {"status": "stopped", "message": "Flow execution stopped"}


@app.post("/api/flow/load")
async def load_and_start_flow(flow: Flow):
    """Load a flow into the executor"""
    global executor_task, current_flow
    
    # Stop existing execution
    if executor_task and not executor_task.done():
        executor.stop()
        await executor_task
        executor_task = None
    
    # Update current flow
    current_flow = flow.dict()
    
    # Load the flow
    executor.load_flow(current_flow)
    
    # Broadcast initial state for all nodes
    for node_id, node in executor.nodes.items():
        await broadcast_state_update(node_id, node.get_state())
    
    return {"status": "loaded", "message": f"Flow loaded with {len(flow.nodes)} nodes"}


@app.post("/api/node/input")
async def handle_user_input(request: Dict[str, Any]):
    """Handle user input from UI"""
    node_id = request.get("nodeId")
    control = request.get("control")
    value = request.get("value")
    
    if not all([node_id, control is not None, value is not None]):
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    await executor.handle_user_input(node_id, control, value)
    
    return {"status": "success"}


async def broadcast_state_update(node_id: str, state: Dict[str, Any]):
    """Broadcast state update to all connected WebSocket clients"""
    message = json.dumps({
        "type": "node_state",
        "nodeId": node_id,
        "state": state
    })
    
    # Remove disconnected clients
    disconnected = []
    for connection in active_connections:
        try:
            await connection.send_text(message)
        except:
            disconnected.append(connection)
    
    for conn in disconnected:
        active_connections.remove(conn)


async def broadcast_flow_update(flow_data: Dict[str, Any]):
    """Broadcast flow update to all connected WebSocket clients"""
    message = json.dumps({
        "type": "flow_update",
        "flow": flow_data
    })
    
    # Remove disconnected clients
    disconnected = []
    for connection in active_connections:
        try:
            await connection.send_text(message)
        except:
            disconnected.append(connection)
    
    for conn in disconnected:
        active_connections.remove(conn)


async def broadcast_execution_state(executing: bool):
    """Broadcast execution state to all connected WebSocket clients"""
    message = json.dumps({
        "type": "execution_state",
        "isExecuting": executing
    })
    
    # Remove disconnected clients
    disconnected = []
    for connection in active_connections:
        try:
            await connection.send_text(message)
        except:
            disconnected.append(connection)
    
    for conn in disconnected:
        active_connections.remove(conn)


async def broadcast_hardware_config(hardware_config: Dict[str, Any]):
    """Broadcast hardware configuration to all connected WebSocket clients"""
    message = json.dumps({
        "type": "hardware_config",
        "config": hardware_config
    })
    
    logger.info(f"Broadcasting hardware config to {len(active_connections)} clients: {hardware_config}")
    
    # Remove disconnected clients
    disconnected = []
    for connection in active_connections:
        try:
            await connection.send_text(message)
            logger.debug(f"Sent hardware config to client")
        except Exception as e:
            logger.warning(f"Failed to send to client: {e}")
            disconnected.append(connection)
    
    for conn in disconnected:
        active_connections.remove(conn)
        logger.info(f"Removed disconnected client")


async def on_hardware_change(hardware_config: Dict[str, Any]):
    """Callback when hardware configuration changes"""
    logger.info(f"🔧 Hardware changed callback triggered: {hardware_config}")
    
    # Broadcast to all clients
    logger.info(f"Broadcasting to {len(active_connections)} active WebSocket connections")
    await broadcast_hardware_config(hardware_config)
    
    # Clean up nodes that are no longer available
    await cleanup_unavailable_nodes(hardware_config)
    logger.info("Hardware change processing complete")


async def cleanup_unavailable_nodes(hardware_config: Dict[str, Any]):
    """Remove nodes from the flow when hardware is disconnected"""
    global current_flow
    
    # Note: Motor nodes are manual and not auto-removed
    # Users must manually configure which port each motor uses
    # This function is kept for potential future sensor cleanup logic
    pass


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time state updates"""
    await websocket.accept()
    active_connections.append(websocket)
    logger.info(f"New WebSocket client connected. Total clients: {len(active_connections)}")
    
    # Send initial hardware configuration to new client
    try:
        hardware_config = hardware_manager.get_hardware_config()
        logger.info(f"Sending initial hardware config to new client: {hardware_config}")
        await websocket.send_text(json.dumps({
            "type": "hardware_config",
            "config": hardware_config
        }))
        logger.debug("Initial hardware config sent successfully")
    except Exception as e:
        logger.error(f"Error sending initial hardware config: {e}", exc_info=True)
    
    try:
        # Keep connection alive and listen for client messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types from client
            if message.get("type") == "user_input":
                await executor.handle_user_input(
                    message["nodeId"],
                    message["control"],
                    message["value"]
                )
            elif message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
                
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info("Client disconnected")

# Mount static files directory
app.mount("/static", StaticFiles(directory="app/static"), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
