#!/usr/bin/env python3
"""
SlickNXT Execution Engine
Runs node-based flows on the server side
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Set
from abc import ABC, abstractmethod
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Node(ABC):
    """Base class for all executable nodes"""
    
    def __init__(self, node_id: str, node_type: str, data: Dict[str, Any]):
        self.node_id = node_id
        self.node_type = node_type
        self.data = data
        self.inputs: Dict[str, Any] = {}
        self.outputs: Dict[str, Any] = {}
        self.connected_inputs: Set[str] = set()
        
    @abstractmethod
    async def execute(self) -> Dict[str, Any]:
        """
        Execute node logic and return outputs
        Returns: Dict of output_port_name -> value
        """
        pass
    
    def set_input(self, port: str, value: Any):
        """Set input value from connected node"""
        self.inputs[port] = value
        
    def get_output(self, port: str) -> Any:
        """Get output value for connected nodes"""
        return self.outputs.get(port)
    
    def set_user_input(self, control: str, value: Any):
        """Handle user input from UI (e.g., slider change)"""
        # Override in nodes that have user controls
        pass
    
    def get_state(self) -> Dict[str, Any]:
        """Get current state for UI display"""
        return {
            "inputs": self.inputs.copy(),
            "outputs": self.outputs.copy(),
            "data": self.data.copy()
        }


class FlowExecutor:
    """
    Executes a node-based flow graph
    Handles value propagation and execution order
    """
    
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Dict[str, str]] = []
        self.execution_order: List[str] = []
        self.running = False
        self.state_callbacks = []  # Callbacks for state updates
        
    def load_flow(self, flow_data: Dict[str, Any]):
        """Load a flow from saved data"""
        self.nodes.clear()
        self.edges = flow_data.get("edges", [])
        
        # Create node instances
        for node_data in flow_data.get("nodes", []):
            node = self._create_node(node_data)
            if node:
                self.nodes[node.node_id] = node
        
        # Build execution order (topological sort)
        self._build_execution_order()
        
        # Mark connected inputs
        for edge in self.edges:
            target_id = edge["target"]
            target_handle = edge.get("targetHandle", "")
            if target_id in self.nodes:
                # Convert handle ID to input key
                input_key = self._handle_to_input_key(target_handle)
                self.nodes[target_id].connected_inputs.add(input_key)
        
        logger.info(f"Loaded flow with {len(self.nodes)} nodes, {len(self.edges)} edges")
        
    def _create_node(self, node_data: Dict[str, Any]) -> Optional[Node]:
        """Factory method to create node instances"""
        node_type = node_data.get("type")
        node_id = node_data.get("id")
        data = node_data.get("data", {})
        
        # Import node classes
        node_classes = {
            "dialNode": DialNode,
            "switchNode": SwitchNode,
            "motorNode": MotorNode,
            "numberDisplayNode": NumberDisplayNode,
            "boolDisplayNode": BoolDisplayNode,
            "andNode": AndNode,
            "orNode": OrNode,
            "xorNode": XorNode,
            "notNode": NotNode,
            "pulseTimerNode": PulseTimerNode,
            "delayTimerNode": DelayTimerNode,
            "comparatorNode": ComparatorNode,
            "boolGateNode": BoolGateNode,
            "capNode": CapNode,
            "addNode": AddNode,
            "subtractNode": SubtractNode,
            "historyDisplayNode": HistoryDisplayNode,
            "integratorNode": IntegratorNode,
            "pControllerNode": PControllerNode,
        }
        
        node_class = node_classes.get(node_type)
        if node_class:
            return node_class(node_id, node_type, data)
        else:
            logger.warning(f"Unknown node type: {node_type}")
            return None
    
    def _handle_to_input_key(self, handle: str) -> str:
        """Convert handle ID (kebab-case) to input key (camelCase)"""
        if not handle.startswith("in-"):
            return handle
        
        parts = handle[3:].split("-")
        if len(parts) == 1:
            return parts[0]
        
        return parts[0] + "".join(word.capitalize() for word in parts[1:])
    
    def _build_execution_order(self):
        """Build topological execution order using Kahn's algorithm"""
        # Build adjacency list
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        
        # Initialize all nodes
        for node_id in self.nodes:
            in_degree[node_id] = 0
        
        # Build graph
        for edge in self.edges:
            source = edge["source"]
            target = edge["target"]
            if source in self.nodes and target in self.nodes:
                graph[source].append(target)
                in_degree[target] += 1
        
        # Find nodes with no incoming edges
        queue = [node_id for node_id in self.nodes if in_degree[node_id] == 0]
        execution_order = []
        
        while queue:
            node_id = queue.pop(0)
            execution_order.append(node_id)
            
            for neighbor in graph[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # If we couldn't order all nodes, there's a cycle
        if len(execution_order) != len(self.nodes):
            logger.warning("Flow contains cycles, using simple order")
            execution_order = list(self.nodes.keys())
        
        self.execution_order = execution_order
        logger.info(f"Execution order: {execution_order}")
    
    async def execute_cycle(self):
        """Execute one cycle of the flow"""
        # Propagate values through edges first
        for edge in self.edges:
            source_id = edge["source"]
            target_id = edge["target"]
            source_handle = edge.get("sourceHandle", "")
            target_handle = edge.get("targetHandle", "")
            
            if source_id in self.nodes and target_id in self.nodes:
                source_node = self.nodes[source_id]
                target_node = self.nodes[target_id]
                
                # Get output from source
                output_key = source_handle.replace("out-", "") if source_handle.startswith("out-") else "output"
                value = source_node.get_output(output_key)
                
                # Set input on target
                input_key = self._handle_to_input_key(target_handle)
                target_node.set_input(input_key, value)
        
        # Execute nodes in order
        for node_id in self.execution_order:
            node = self.nodes[node_id]
            try:
                outputs = await node.execute()
                node.outputs = outputs
                
                # Notify state change
                await self._notify_state_change(node_id, node.get_state())
            except Exception as e:
                logger.error(f"Error executing node {node_id}: {e}", exc_info=True)
    
    async def run(self):
        """Run the flow continuously"""
        self.running = True
        logger.info("Flow execution started")
        
        while self.running:
            await self.execute_cycle()
            await asyncio.sleep(0.1)  # 10Hz execution rate
    
    def stop(self):
        """Stop flow execution"""
        self.running = False
        logger.info("Flow execution stopped")
    
    async def handle_user_input(self, node_id: str, control: str, value: Any):
        """Handle user input from UI"""
        if node_id in self.nodes:
            self.nodes[node_id].set_user_input(control, value)
            logger.debug(f"User input: {node_id}.{control} = {value}")
    
    def add_state_callback(self, callback):
        """Add callback for state updates"""
        self.state_callbacks.append(callback)
    
    async def _notify_state_change(self, node_id: str, state: Dict[str, Any]):
        """Notify all callbacks of state change"""
        for callback in self.state_callbacks:
            try:
                await callback(node_id, state)
            except Exception as e:
                logger.error(f"Error in state callback: {e}")


# ============================================================================
# NODE IMPLEMENTATIONS
# ============================================================================

class DialNode(Node):
    """Virtual dial/slider input (0-100)"""
    
    def __init__(self, node_id: str, node_type: str, data: Dict[str, Any]):
        super().__init__(node_id, node_type, data)
        self.value = 50
        self.outputs = {"value": self.value}
    
    async def execute(self) -> Dict[str, Any]:
        return {"value": self.value}
    
    def set_user_input(self, control: str, value: Any):
        if control == "value":
            self.value = int(value)


class SwitchNode(Node):
    """Virtual on/off switch"""
    
    def __init__(self, node_id: str, node_type: str, data: Dict[str, Any]):
        super().__init__(node_id, node_type, data)
        self.value = False
        self.outputs = {"value": self.value}
    
    async def execute(self) -> Dict[str, Any]:
        return {"value": self.value}
    
    def set_user_input(self, control: str, value: Any):
        if control == "value":
            self.value = bool(value)


class MotorNode(Node):
    """Motor controller node"""
    
    def __init__(self, node_id: str, node_type: str, data: Dict[str, Any]):
        super().__init__(node_id, node_type, data)
        self.on_off = False
        self.forward = True
        self.speed = 50
    
    async def execute(self) -> Dict[str, Any]:
        # Use connected inputs if available, otherwise use internal state
        on_off = self.inputs.get("onOff", self.on_off)
        forward = self.inputs.get("forward", self.forward)
        speed = self.inputs.get("speed", self.speed)
        
        # Clamp speed
        speed = max(0, min(100, speed))
        
        # TODO: In future, interface with NXT-Python here
        # nxt.Motor(...).run(speed if on_off else 0, forward)
        
        return {
            "onOff": on_off,
            "forward": forward,
            "speed": speed
        }
    
    def set_user_input(self, control: str, value: Any):
        if control == "onOff" and "onOff" not in self.connected_inputs:
            self.on_off = bool(value)
        elif control == "forward" and "forward" not in self.connected_inputs:
            self.forward = bool(value)
        elif control == "speed" and "speed" not in self.connected_inputs:
            self.speed = int(value)


class NumberDisplayNode(Node):
    """Display numeric value"""
    
    async def execute(self) -> Dict[str, Any]:
        # Just passes through the value
        value = self.inputs.get("value", 0)
        self.data["displayValue"] = value
        return {}


class BoolDisplayNode(Node):
    """Display boolean value"""
    
    async def execute(self) -> Dict[str, Any]:
        # Just passes through the value
        value = self.inputs.get("value", False)
        self.data["displayValue"] = value
        return {}


class AndNode(Node):
    """Logical AND gate"""
    
    async def execute(self) -> Dict[str, Any]:
        a = self.inputs.get("a", False)
        b = self.inputs.get("b", False)
        return {"output": a and b}


class OrNode(Node):
    """Logical OR gate"""
    
    async def execute(self) -> Dict[str, Any]:
        a = self.inputs.get("a", False)
        b = self.inputs.get("b", False)
        return {"output": a or b}


class XorNode(Node):
    """Logical XOR gate"""
    
    async def execute(self) -> Dict[str, Any]:
        a = self.inputs.get("a", False)
        b = self.inputs.get("b", False)
        return {"output": a != b}


class NotNode(Node):
    """Logical NOT gate"""
    
    async def execute(self) -> Dict[str, Any]:
        input_val = self.inputs.get("input", False)
        return {"output": not input_val}


class PulseTimerNode(Node):
    """Pulse timer - generates repeating on/off pulses"""
    
    def __init__(self, node_id: str, node_type: str, data: Dict[str, Any]):
        super().__init__(node_id, node_type, data)
        self.on_duration = 2.0
        self.off_duration = 2.0
        self.enabled = False
        self.output = False
        self.last_toggle = time.time()
        self.state = "off"  # "on" or "off"
    
    async def execute(self) -> Dict[str, Any]:
        # Update from inputs
        self.on_duration = self.inputs.get("onDuration", self.on_duration)
        self.off_duration = self.inputs.get("offDuration", self.off_duration)
        enabled = self.inputs.get("enable", self.enabled)
        
        # If just enabled, start fresh
        if enabled and not self.enabled:
            self.state = "off"
            self.output = False
            self.last_toggle = time.time()
        
        self.enabled = enabled
        
        if not self.enabled:
            self.output = False
        else:
            now = time.time()
            elapsed = now - self.last_toggle
            
            if self.state == "off" and elapsed >= self.off_duration:
                self.output = True
                self.state = "on"
                self.last_toggle = now
            elif self.state == "on" and elapsed >= self.on_duration:
                self.output = False
                self.state = "off"
                self.last_toggle = now
        
        return {"output": self.output}
    
    def set_user_input(self, control: str, value: Any):
        if control == "onDuration":
            self.on_duration = float(value)
        elif control == "offDuration":
            self.off_duration = float(value)
        elif control == "enabled":
            self.enabled = bool(value)


class DelayTimerNode(Node):
    """Delay timer - delays signal by specified time"""
    
    def __init__(self, node_id: str, node_type: str, data: Dict[str, Any]):
        super().__init__(node_id, node_type, data)
        self.delay = 1.0
        self.queue = []  # (timestamp, value) pairs
    
    async def execute(self) -> Dict[str, Any]:
        self.delay = self.inputs.get("delay", self.delay)
        input_val = self.inputs.get("input", None)
        
        now = time.time()
        
        # Add new value to queue
        if input_val is not None:
            self.queue.append((now + self.delay, input_val))
        
        # Check if any delayed values are ready
        output = None
        while self.queue and self.queue[0][0] <= now:
            _, output = self.queue.pop(0)
        
        return {"output": output}
    
    def set_user_input(self, control: str, value: Any):
        if control == "delay":
            self.delay = float(value)


class ComparatorNode(Node):
    """Compares two numbers"""
    
    def __init__(self, node_id: str, node_type: str, data: Dict[str, Any]):
        super().__init__(node_id, node_type, data)
        self.mode = ">"
    
    async def execute(self) -> Dict[str, Any]:
        a = self.inputs.get("a", 0)
        b = self.inputs.get("b", 0)
        
        if self.mode == ">":
            result = a > b
        elif self.mode == "<":
            result = a < b
        else:  # "=="
            result = a == b
        
        return {"output": result}
    
    def set_user_input(self, control: str, value: Any):
        if control == "mode":
            self.mode = value


class BoolGateNode(Node):
    """Passes signal through only if enabled"""
    
    async def execute(self) -> Dict[str, Any]:
        signal = self.inputs.get("signal", None)
        enable = self.inputs.get("enable", False)
        
        return {"output": signal if enable else None}


class CapNode(Node):
    """Clamps value between min and max"""
    
    def __init__(self, node_id: str, node_type: str, data: Dict[str, Any]):
        super().__init__(node_id, node_type, data)
        self.min_val = 0
        self.max_val = 100
    
    async def execute(self) -> Dict[str, Any]:
        input_val = self.inputs.get("input", 50)
        min_val = self.inputs.get("min", self.min_val)
        max_val = self.inputs.get("max", self.max_val)
        
        clamped = max(min_val, min(max_val, input_val))
        return {"output": clamped}
    
    def set_user_input(self, control: str, value: Any):
        if control == "min":
            self.min_val = int(value)
        elif control == "max":
            self.max_val = int(value)


class AddNode(Node):
    """Adds two numbers"""
    
    async def execute(self) -> Dict[str, Any]:
        a = self.inputs.get("a", 0)
        b = self.inputs.get("b", 0)
        return {"output": a + b}


class SubtractNode(Node):
    """Subtracts two numbers"""
    
    async def execute(self) -> Dict[str, Any]:
        a = self.inputs.get("a", 0)
        b = self.inputs.get("b", 0)
        return {"output": a - b}


class HistoryDisplayNode(Node):
    """Displays historical values (stores in backend)"""
    
    def __init__(self, node_id: str, node_type: str, data: Dict[str, Any]):
        super().__init__(node_id, node_type, data)
        self.history = []
        self.max_points = 50
        self.sample_rate = 0.5
        self.last_sample = time.time()
    
    async def execute(self) -> Dict[str, Any]:
        value = self.inputs.get("value", None)
        sample_rate = self.inputs.get("sampleRate", self.sample_rate)
        
        now = time.time()
        if value is not None and now - self.last_sample >= sample_rate:
            self.history.append(value)
            if len(self.history) > self.max_points:
                self.history.pop(0)
            self.last_sample = now
        
        self.data["history"] = self.history.copy()
        return {}
    
    def set_user_input(self, control: str, value: Any):
        if control == "sampleRate":
            self.sample_rate = float(value)


class IntegratorNode(Node):
    """Integrator/Accumulator"""
    
    def __init__(self, node_id: str, node_type: str, data: Dict[str, Any]):
        super().__init__(node_id, node_type, data)
        self.accumulator = 0.0
        self.enabled = True
        self.last_update = time.time()
    
    async def execute(self) -> Dict[str, Any]:
        input_val = self.inputs.get("input", 0)
        enabled = self.inputs.get("enabled", self.enabled)
        reset = self.inputs.get("reset", False)
        
        if reset:
            self.accumulator = 0.0
        elif enabled:
            now = time.time()
            dt = now - self.last_update
            self.accumulator += input_val * dt
            # Clamp to reasonable range
            self.accumulator = max(-1000, min(1000, self.accumulator))
            self.last_update = now
        
        self.enabled = enabled
        return {"output": round(self.accumulator)}
    
    def set_user_input(self, control: str, value: Any):
        if control == "enabled":
            self.enabled = bool(value)
        elif control == "reset":
            self.accumulator = 0.0


class PControllerNode(Node):
    """Proportional controller"""
    
    def __init__(self, node_id: str, node_type: str, data: Dict[str, Any]):
        super().__init__(node_id, node_type, data)
        self.enabled = False
        self.p_gain = 1.0
        self.setpoint = 50
        self.current_value = 0
    
    async def execute(self) -> Dict[str, Any]:
        enabled = self.inputs.get("enabled", self.enabled)
        p_gain = self.inputs.get("pGain", self.p_gain)
        setpoint = self.inputs.get("setpoint", self.setpoint)
        current = self.inputs.get("currentValue", self.current_value)
        
        if enabled:
            error = setpoint - current
            output = round(p_gain * error)
        else:
            output = 0
        
        self.enabled = enabled
        self.p_gain = p_gain
        self.setpoint = setpoint
        self.current_value = current
        
        return {"output": output}
    
    def set_user_input(self, control: str, value: Any):
        if control == "enabled":
            self.enabled = bool(value)
        elif control == "pGain":
            self.p_gain = float(value)

