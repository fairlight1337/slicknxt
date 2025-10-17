#!/usr/bin/env python3
"""
Hardware Manager for NXT
Detects and manages connected NXT motors and sensors
"""

import asyncio
import logging
from typing import Dict, Set, Optional, Callable
import nxt.locator
import nxt.motor
import nxt.sensor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HardwareManager:
    """Manages NXT hardware detection and state"""
    
    def __init__(self):
        self.brick: Optional[any] = None
        self.connected_motors: Set[str] = set()  # {'A', 'B', 'C'}
        self.connected_sensors: Set[str] = set()  # {'1', '2', '3', '4'}
        self.is_connected: bool = False
        self.change_callbacks: list[Callable] = []
        self.monitoring_task: Optional[asyncio.Task] = None
        
    def add_change_callback(self, callback: Callable):
        """Register a callback for hardware changes"""
        if callback not in self.change_callbacks:
            self.change_callbacks.append(callback)
    
    def remove_change_callback(self, callback: Callable):
        """Unregister a callback"""
        if callback in self.change_callbacks:
            self.change_callbacks.remove(callback)
    
    async def _notify_changes(self):
        """Notify all callbacks about hardware changes"""
        hardware_config = self.get_hardware_config()
        for callback in self.change_callbacks:
            try:
                await callback(hardware_config)
            except Exception as e:
                logger.error(f"Error in hardware change callback: {e}")
    
    def connect_brick(self) -> bool:
        """Connect to the NXT brick"""
        try:
            self.brick = nxt.locator.find()
            self.is_connected = True
            logger.info(f"Connected to NXT: {self.brick.get_device_info()}")
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to NXT: {e}")
            self.is_connected = False
            self.brick = None
            return False
    
    def disconnect_brick(self):
        """Disconnect from the NXT brick"""
        if self.brick:
            try:
                self.brick.close()
            except:
                pass
            self.brick = None
        self.is_connected = False
        self.connected_motors.clear()
        self.connected_sensors.clear()
    
    def detect_motors(self) -> Set[str]:
        """
        Detect which motor ports have motors connected
        Returns: Set of port names ('A', 'B', 'C')
        """
        if not self.brick or not self.is_connected:
            return set()
        
        detected_motors = set()
        
        for port_char in ['A', 'B', 'C']:
            try:
                port = getattr(nxt.motor.Port, port_char)
                motor = nxt.motor.Motor(self.brick, port)
                
                # Try to get motor state - if this succeeds, a motor is connected
                state = motor.get_state()
                if state:
                    detected_motors.add(port_char)
                    logger.debug(f"Motor detected on port {port_char}")
            except Exception as e:
                # No motor or error reading motor
                logger.debug(f"No motor on port {port_char}: {e}")
        
        return detected_motors
    
    def detect_sensors(self) -> Set[str]:
        """
        Detect which sensor ports have sensors connected
        Returns: Set of port numbers ('1', '2', '3', '4')
        """
        if not self.brick or not self.is_connected:
            return set()
        
        detected_sensors = set()
        
        # For now, return empty set - we'll implement sensor detection later
        # Sensor detection is more complex as different sensor types need different approaches
        
        return detected_sensors
    
    async def monitor_hardware(self):
        """
        Continuously monitor hardware connections
        Detects changes and notifies callbacks
        """
        logger.info("Starting hardware monitoring")
        
        while True:
            try:
                # Try to connect if not connected
                if not self.is_connected:
                    if self.connect_brick():
                        # Connection established, detect hardware
                        prev_motors = self.connected_motors.copy()
                        self.connected_motors = self.detect_motors()
                        
                        if prev_motors != self.connected_motors:
                            logger.info(f"Motors detected: {self.connected_motors}")
                            await self._notify_changes()
                    else:
                        # Not connected, clear all hardware
                        if self.connected_motors or self.connected_sensors:
                            self.connected_motors.clear()
                            self.connected_sensors.clear()
                            await self._notify_changes()
                else:
                    # Already connected, check for changes
                    try:
                        prev_motors = self.connected_motors.copy()
                        self.connected_motors = self.detect_motors()
                        
                        if prev_motors != self.connected_motors:
                            logger.info(f"Motor configuration changed: {self.connected_motors}")
                            await self._notify_changes()
                    except Exception as e:
                        # Lost connection
                        logger.warning(f"Lost connection to NXT: {e}")
                        self.disconnect_brick()
                        await self._notify_changes()
                
            except Exception as e:
                logger.error(f"Error in hardware monitoring: {e}")
            
            # Check every 2 seconds
            await asyncio.sleep(2.0)
    
    def start_monitoring(self):
        """Start the hardware monitoring task"""
        if not self.monitoring_task or self.monitoring_task.done():
            self.monitoring_task = asyncio.create_task(self.monitor_hardware())
            logger.info("Hardware monitoring started")
    
    def stop_monitoring(self):
        """Stop the hardware monitoring task"""
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            logger.info("Hardware monitoring stopped")
    
    def get_hardware_config(self) -> Dict[str, any]:
        """Get current hardware configuration"""
        return {
            "isConnected": self.is_connected,
            "motors": sorted(list(self.connected_motors)),
            "sensors": sorted(list(self.connected_sensors))
        }
    
    def get_motor(self, port: str) -> Optional[nxt.motor.Motor]:
        """Get a motor instance for the specified port"""
        if not self.brick or not self.is_connected:
            return None
        
        if port not in self.connected_motors:
            return None
        
        try:
            port_obj = getattr(nxt.motor.Port, port)
            return nxt.motor.Motor(self.brick, port_obj)
        except Exception as e:
            logger.error(f"Error getting motor on port {port}: {e}")
            return None

