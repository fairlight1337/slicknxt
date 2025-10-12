#!/usr/bin/env python3
"""
Unit tests for execution engine nodes.
Tests the input/output behavior of all blocks.
"""

import pytest
import asyncio
import time
from app.execution_engine import (
    DialNode, SwitchNode, MotorNode, NumberDisplayNode, BoolDisplayNode,
    AndNode, OrNode, XorNode, NotNode, ToggleNode,
    PulseTimerNode, DelayTimerNode, ComparatorNode, BoolGateNode,
    CapNode, AddNode, SubtractNode, HistoryDisplayNode,
    IntegratorNode, PControllerNode
)


# ============================================================================
# INPUT/OUTPUT NODES
# ============================================================================

class TestDialNode:
    """Test DialNode - virtual slider input (0-100)"""
    
    def test_default_value(self):
        node = DialNode("test-1", "dialNode", {})
        result = asyncio.run(node.execute())
        assert result["value"] == 50
    
    def test_set_user_input(self):
        node = DialNode("test-1", "dialNode", {})
        node.set_user_input("value", 75)
        result = asyncio.run(node.execute())
        assert result["value"] == 75
        assert node.outputs["value"] == 75
    
    def test_value_range(self):
        node = DialNode("test-1", "dialNode", {})
        node.set_user_input("value", 0)
        assert asyncio.run(node.execute())["value"] == 0
        node.set_user_input("value", 100)
        assert asyncio.run(node.execute())["value"] == 100


class TestSwitchNode:
    """Test SwitchNode - on/off switch"""
    
    def test_default_value(self):
        node = SwitchNode("test-1", "switchNode", {})
        result = asyncio.run(node.execute())
        assert result["value"] is False
    
    def test_toggle_on(self):
        node = SwitchNode("test-1", "switchNode", {})
        node.set_user_input("value", True)
        result = asyncio.run(node.execute())
        assert result["value"] is True
        assert node.outputs["value"] is True
    
    def test_toggle_off(self):
        node = SwitchNode("test-1", "switchNode", {})
        node.set_user_input("value", True)
        node.set_user_input("value", False)
        result = asyncio.run(node.execute())
        assert result["value"] is False


class TestMotorNode:
    """Test MotorNode - motor controller"""
    
    def test_default_values(self):
        node = MotorNode("test-1", "motorNode", {})
        result = asyncio.run(node.execute())
        assert result["onOff"] is False
        assert result["forward"] is True
        assert result["speed"] == 50
    
    def test_set_speed(self):
        node = MotorNode("test-1", "motorNode", {})
        node.set_user_input("speed", 75)
        result = asyncio.run(node.execute())
        assert result["speed"] == 75
    
    def test_speed_clamping(self):
        node = MotorNode("test-1", "motorNode", {})
        node.inputs["speed"] = 150  # Above max
        result = asyncio.run(node.execute())
        assert result["speed"] == 100
        
        node.inputs["speed"] = -20  # Below min
        result = asyncio.run(node.execute())
        assert result["speed"] == 0
    
    def test_connected_inputs_override(self):
        node = MotorNode("test-1", "motorNode", {})
        node.set_user_input("speed", 50)
        node.inputs["speed"] = 80  # Simulating connected input
        result = asyncio.run(node.execute())
        assert result["speed"] == 80  # Connected input takes precedence


class TestNumberDisplayNode:
    """Test NumberDisplayNode - display numeric value"""
    
    def test_no_input(self):
        node = NumberDisplayNode("test-1", "numberDisplayNode", {})
        result = asyncio.run(node.execute())
        assert result["value"] == 0
    
    def test_with_input(self):
        node = NumberDisplayNode("test-1", "numberDisplayNode", {})
        node.inputs["value"] = 42
        result = asyncio.run(node.execute())
        assert result["value"] == 42


class TestBoolDisplayNode:
    """Test BoolDisplayNode - display boolean value"""
    
    def test_no_input(self):
        node = BoolDisplayNode("test-1", "boolDisplayNode", {})
        result = asyncio.run(node.execute())
        assert result["value"] is False
    
    def test_with_input(self):
        node = BoolDisplayNode("test-1", "boolDisplayNode", {})
        node.inputs["value"] = True
        result = asyncio.run(node.execute())
        assert result["value"] is True


# ============================================================================
# LOGIC GATES
# ============================================================================

class TestAndNode:
    """Test AndNode - logical AND"""
    
    def test_false_false(self):
        node = AndNode("test-1", "andNode", {})
        node.inputs = {"a": False, "b": False}
        result = asyncio.run(node.execute())
        assert result["output"] is False
    
    def test_false_true(self):
        node = AndNode("test-1", "andNode", {})
        node.inputs = {"a": False, "b": True}
        result = asyncio.run(node.execute())
        assert result["output"] is False
    
    def test_true_false(self):
        node = AndNode("test-1", "andNode", {})
        node.inputs = {"a": True, "b": False}
        result = asyncio.run(node.execute())
        assert result["output"] is False
    
    def test_true_true(self):
        node = AndNode("test-1", "andNode", {})
        node.inputs = {"a": True, "b": True}
        result = asyncio.run(node.execute())
        assert result["output"] is True


class TestOrNode:
    """Test OrNode - logical OR"""
    
    def test_false_false(self):
        node = OrNode("test-1", "orNode", {})
        node.inputs = {"a": False, "b": False}
        result = asyncio.run(node.execute())
        assert result["output"] is False
    
    def test_false_true(self):
        node = OrNode("test-1", "orNode", {})
        node.inputs = {"a": False, "b": True}
        result = asyncio.run(node.execute())
        assert result["output"] is True
    
    def test_true_false(self):
        node = OrNode("test-1", "orNode", {})
        node.inputs = {"a": True, "b": False}
        result = asyncio.run(node.execute())
        assert result["output"] is True
    
    def test_true_true(self):
        node = OrNode("test-1", "orNode", {})
        node.inputs = {"a": True, "b": True}
        result = asyncio.run(node.execute())
        assert result["output"] is True


class TestXorNode:
    """Test XorNode - logical XOR"""
    
    def test_false_false(self):
        node = XorNode("test-1", "xorNode", {})
        node.inputs = {"a": False, "b": False}
        result = asyncio.run(node.execute())
        assert result["output"] is False
    
    def test_false_true(self):
        node = XorNode("test-1", "xorNode", {})
        node.inputs = {"a": False, "b": True}
        result = asyncio.run(node.execute())
        assert result["output"] is True
    
    def test_true_false(self):
        node = XorNode("test-1", "xorNode", {})
        node.inputs = {"a": True, "b": False}
        result = asyncio.run(node.execute())
        assert result["output"] is True
    
    def test_true_true(self):
        node = XorNode("test-1", "xorNode", {})
        node.inputs = {"a": True, "b": True}
        result = asyncio.run(node.execute())
        assert result["output"] is False


class TestNotNode:
    """Test NotNode - logical NOT"""
    
    def test_false_input(self):
        node = NotNode("test-1", "notNode", {})
        node.inputs = {"input": False}
        result = asyncio.run(node.execute())
        assert result["output"] is True
    
    def test_true_input(self):
        node = NotNode("test-1", "notNode", {})
        node.inputs = {"input": True}
        result = asyncio.run(node.execute())
        assert result["output"] is False


class TestToggleNode:
    """Test ToggleNode - edge-triggered flip-flop"""
    
    def test_default_state(self):
        node = ToggleNode("test-1", "toggleNode", {})
        result = asyncio.run(node.execute())
        assert result["output"] is False
    
    def test_rising_edge_toggle(self):
        node = ToggleNode("test-1", "toggleNode", {})
        node.edge_mode = "rising"
        
        # Initial state
        node.inputs["input"] = False
        asyncio.run(node.execute())
        assert node.output_state is False
        
        # Rising edge - should toggle
        node.inputs["input"] = True
        result = asyncio.run(node.execute())
        assert result["output"] is True
        
        # Stay high - no toggle
        node.inputs["input"] = True
        result = asyncio.run(node.execute())
        assert result["output"] is True
        
        # Falling edge - no toggle in rising mode
        node.inputs["input"] = False
        result = asyncio.run(node.execute())
        assert result["output"] is True
        
        # Rising edge again - should toggle
        node.inputs["input"] = True
        result = asyncio.run(node.execute())
        assert result["output"] is False
    
    def test_falling_edge_toggle(self):
        node = ToggleNode("test-1", "toggleNode", {})
        node.edge_mode = "falling"
        
        # Start high
        node.inputs["input"] = True
        asyncio.run(node.execute())
        assert node.output_state is False
        
        # Falling edge - should toggle
        node.inputs["input"] = False
        result = asyncio.run(node.execute())
        assert result["output"] is True
        
        # Rising edge - no toggle in falling mode
        node.inputs["input"] = True
        result = asyncio.run(node.execute())
        assert result["output"] is True
        
        # Falling edge again - should toggle
        node.inputs["input"] = False
        result = asyncio.run(node.execute())
        assert result["output"] is False
    
    def test_edge_mode_change(self):
        node = ToggleNode("test-1", "toggleNode", {})
        assert node.edge_mode == "rising"
        node.set_user_input("edgeMode", "falling")
        assert node.edge_mode == "falling"


# ============================================================================
# TIMING BLOCKS
# ============================================================================

class TestPulseTimerNode:
    """Test PulseTimerNode - generates timed pulses"""
    
    def test_disabled_by_default(self):
        node = PulseTimerNode("test-1", "pulseTimerNode", {})
        result = asyncio.run(node.execute())
        assert result["output"] is False
    
    def test_enable_starts_pulse(self):
        node = PulseTimerNode("test-1", "pulseTimerNode", {})
        node.on_duration = 0.1
        node.off_duration = 0.1
        node.set_user_input("enable", True)
        
        # Should start in OFF state
        result = asyncio.run(node.execute())
        assert result["output"] is False
    
    def test_pulse_timing(self):
        node = PulseTimerNode("test-1", "pulseTimerNode", {})
        node.on_duration = 0.05
        node.off_duration = 0.05
        node.set_user_input("enable", True)
        
        # Start OFF
        asyncio.run(node.execute())
        assert node.output is False
        
        # Wait and transition to ON
        time.sleep(0.06)
        asyncio.run(node.execute())
        assert node.output is True
        
        # Wait and transition back to OFF
        time.sleep(0.06)
        asyncio.run(node.execute())
        assert node.output is False


class TestDelayTimerNode:
    """Test DelayTimerNode - delays signal"""
    
    def test_no_delay(self):
        node = DelayTimerNode("test-1", "delayTimerNode", {})
        node.delay = 0
        node.inputs["input"] = 42
        result = asyncio.run(node.execute())
        assert result["output"] == 42
    
    def test_initial_delay(self):
        node = DelayTimerNode("test-1", "delayTimerNode", {})
        node.delay = 0.1
        node.inputs["input"] = 42
        
        # Should output None initially (nothing ready yet)
        result = asyncio.run(node.execute())
        assert result["output"] is None
        
        # After delay, should output delayed value
        time.sleep(0.11)
        result = asyncio.run(node.execute())
        assert result["output"] == 42
    
    def test_delay_change(self):
        node = DelayTimerNode("test-1", "delayTimerNode", {})
        node.set_user_input("delay", 2.5)
        assert node.delay == 2.5


# ============================================================================
# COMPARISON & FILTERING
# ============================================================================

class TestComparatorNode:
    """Test ComparatorNode - integer comparison"""
    
    def test_greater_than(self):
        node = ComparatorNode("test-1", "comparatorNode", {})
        node.mode = ">"
        node.inputs = {"a": 10, "b": 5}
        result = asyncio.run(node.execute())
        assert result["output"] is True
        
        node.inputs = {"a": 5, "b": 10}
        result = asyncio.run(node.execute())
        assert result["output"] is False
    
    def test_less_than(self):
        node = ComparatorNode("test-1", "comparatorNode", {})
        node.mode = "<"
        node.inputs = {"a": 5, "b": 10}
        result = asyncio.run(node.execute())
        assert result["output"] is True
        
        node.inputs = {"a": 10, "b": 5}
        result = asyncio.run(node.execute())
        assert result["output"] is False
    
    def test_equal(self):
        node = ComparatorNode("test-1", "comparatorNode", {})
        node.mode = "=="
        node.inputs = {"a": 7, "b": 7}
        result = asyncio.run(node.execute())
        assert result["output"] is True
        
        node.inputs = {"a": 7, "b": 8}
        result = asyncio.run(node.execute())
        assert result["output"] is False


class TestBoolGateNode:
    """Test BoolGateNode - passes signal only if gate is open"""
    
    def test_gate_closed(self):
        node = BoolGateNode("test-1", "boolGateNode", {})
        node.inputs = {"value": 42, "gate": False}
        result = asyncio.run(node.execute())
        assert result["output"] == 0
    
    def test_gate_open(self):
        node = BoolGateNode("test-1", "boolGateNode", {})
        node.inputs = {"value": 42, "gate": True}
        result = asyncio.run(node.execute())
        assert result["output"] == 42
    
    def test_no_gate_input(self):
        node = BoolGateNode("test-1", "boolGateNode", {})
        node.inputs = {"value": 42}
        result = asyncio.run(node.execute())
        assert result["output"] == 0  # Default gate is closed


class TestCapNode:
    """Test CapNode - clamps value to min/max range"""
    
    def test_within_range(self):
        node = CapNode("test-1", "capNode", {})
        node.min_val = 0
        node.max_val = 100
        node.inputs["input"] = 50
        result = asyncio.run(node.execute())
        assert result["output"] == 50
    
    def test_below_minimum(self):
        node = CapNode("test-1", "capNode", {})
        node.min_val = 0
        node.max_val = 100
        node.inputs["input"] = -10
        result = asyncio.run(node.execute())
        assert result["output"] == 0
    
    def test_above_maximum(self):
        node = CapNode("test-1", "capNode", {})
        node.min_val = 0
        node.max_val = 100
        node.inputs["input"] = 150
        result = asyncio.run(node.execute())
        assert result["output"] == 100
    
    def test_custom_range(self):
        node = CapNode("test-1", "capNode", {})
        node.set_user_input("min", 20)
        node.set_user_input("max", 80)
        
        node.inputs["input"] = 10
        result = asyncio.run(node.execute())
        assert result["output"] == 20
        
        node.inputs["input"] = 90
        result = asyncio.run(node.execute())
        assert result["output"] == 80


# ============================================================================
# MATH OPERATIONS
# ============================================================================

class TestAddNode:
    """Test AddNode - addition"""
    
    def test_add_positive(self):
        node = AddNode("test-1", "addNode", {})
        node.inputs = {"a": 10, "b": 5}
        result = asyncio.run(node.execute())
        assert result["output"] == 15
    
    def test_add_negative(self):
        node = AddNode("test-1", "addNode", {})
        node.inputs = {"a": 10, "b": -3}
        result = asyncio.run(node.execute())
        assert result["output"] == 7
    
    def test_missing_input(self):
        node = AddNode("test-1", "addNode", {})
        node.inputs = {"a": 10}  # b defaults to 0
        result = asyncio.run(node.execute())
        assert result["output"] == 10


class TestSubtractNode:
    """Test SubtractNode - subtraction"""
    
    def test_subtract_positive(self):
        node = SubtractNode("test-1", "subtractNode", {})
        node.inputs = {"a": 10, "b": 5}
        result = asyncio.run(node.execute())
        assert result["output"] == 5
    
    def test_subtract_negative(self):
        node = SubtractNode("test-1", "subtractNode", {})
        node.inputs = {"a": 10, "b": -3}
        result = asyncio.run(node.execute())
        assert result["output"] == 13
    
    def test_missing_input(self):
        node = SubtractNode("test-1", "subtractNode", {})
        node.inputs = {"a": 10}  # b defaults to 0
        result = asyncio.run(node.execute())
        assert result["output"] == 10


# ============================================================================
# DISPLAY & MONITORING
# ============================================================================

class TestHistoryDisplayNode:
    """Test HistoryDisplayNode - time-series display"""
    
    def test_default_values(self):
        node = HistoryDisplayNode("test-1", "historyDisplayNode", {})
        result = asyncio.run(node.execute())
        assert result["currentValue"] == 0
        assert result["history"] == []
        assert result["sampleRate"] == 0.5
    
    def test_sample_rate_change(self):
        node = HistoryDisplayNode("test-1", "historyDisplayNode", {})
        node.set_user_input("sampleRate", 1.0)
        assert node.sample_rate == 1.0
        assert node.inputs["sampleRate"] == 1.0
    
    def test_history_accumulation(self):
        node = HistoryDisplayNode("test-1", "historyDisplayNode", {})
        node.max_history = 5
        
        # Simulate samples
        for value in [10, 20, 30, 40, 50]:
            node.inputs["value"] = value
            asyncio.run(node.execute())
            node.history.append(value)
        
        assert len(node.history) == 5
        assert node.history == [10, 20, 30, 40, 50]


# ============================================================================
# CONTROL BLOCKS
# ============================================================================

class TestIntegratorNode:
    """Test IntegratorNode - accumulator"""
    
    def test_disabled_by_default(self):
        node = IntegratorNode("test-1", "integratorNode", {})
        node.inputs["input"] = 10
        result = asyncio.run(node.execute())
        assert result["accumulator"] == 0
    
    def test_accumulation_over_time(self):
        node = IntegratorNode("test-1", "integratorNode", {})
        node.set_user_input("enabled", True)
        
        # Accumulates: value * dt
        node.inputs["input"] = 10
        asyncio.run(node.execute())
        time.sleep(0.1)
        result = asyncio.run(node.execute())
        # Should have accumulated ~1 (10 * 0.1)
        assert result["accumulator"] >= 0
        assert result["accumulator"] <= 100
    
    def test_reset(self):
        node = IntegratorNode("test-1", "integratorNode", {})
        node.set_user_input("enabled", True)
        
        # Set accumulator directly for testing
        node.accumulator = 50
        
        # Reset
        node.set_user_input("reset", True)
        node.inputs["reset"] = True
        result = asyncio.run(node.execute())
        assert result["accumulator"] == 0
    
    def test_clamping(self):
        node = IntegratorNode("test-1", "integratorNode", {})
        node.set_user_input("enabled", True)
        
        # Test upper limit
        node.accumulator = 99
        node.inputs["input"] = 10
        time.sleep(0.2)  # 10 * 0.2 = 2, so 99 + 2 = 101, clamped to 100
        result = asyncio.run(node.execute())
        assert result["accumulator"] == 100
        
        # Test lower limit
        node.accumulator = 1
        node.inputs["input"] = -10
        time.sleep(0.2)  # -10 * 0.2 = -2, so 1 - 2 = -1, clamped to 0
        result = asyncio.run(node.execute())
        assert result["accumulator"] == 0


class TestPControllerNode:
    """Test PControllerNode - proportional controller"""
    
    def test_disabled_by_default(self):
        node = PControllerNode("test-1", "pControllerNode", {})
        result = asyncio.run(node.execute())
        assert result["output"] == 0
    
    def test_proportional_control(self):
        node = PControllerNode("test-1", "pControllerNode", {})
        node.set_user_input("enabled", True)
        node.set_user_input("pGain", 0.5)
        
        # Setpoint = 50, current = 30, error = 20
        node.inputs["setpoint"] = 50
        node.inputs["currentValue"] = 30
        result = asyncio.run(node.execute())
        # output = 0.5 * 20 = 10
        assert result["output"] == 10
    
    def test_negative_error(self):
        node = PControllerNode("test-1", "pControllerNode", {})
        node.set_user_input("enabled", True)
        node.set_user_input("pGain", 0.5)
        
        # Setpoint = 30, current = 50, error = -20
        node.inputs["setpoint"] = 30
        node.inputs["currentValue"] = 50
        result = asyncio.run(node.execute())
        # output = 0.5 * -20 = -10
        assert result["output"] == -10
    
    def test_output_clamping(self):
        node = PControllerNode("test-1", "pControllerNode", {})
        node.set_user_input("enabled", True)
        node.set_user_input("pGain", 2.0)
        
        # Large error should clamp to [-100, 100]
        node.inputs["setpoint"] = 100
        node.inputs["currentValue"] = 0
        result = asyncio.run(node.execute())
        # error = 100, output = 2.0 * 100 = 200, clamped to 100
        assert result["output"] == 100
        
        node.inputs["setpoint"] = 0
        node.inputs["currentValue"] = 100
        result = asyncio.run(node.execute())
        # error = -100, output = 2.0 * -100 = -200, clamped to -100
        assert result["output"] == -100
    
    def test_gain_change(self):
        node = PControllerNode("test-1", "pControllerNode", {})
        node.set_user_input("pGain", 1.5)
        assert node.p_gain == 1.5
        assert node.inputs["pGain"] == 1.5


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

