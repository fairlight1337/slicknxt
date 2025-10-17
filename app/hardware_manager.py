#!/usr/bin/env python3
"""
Hardware Manager for NXT
Detects and manages connected NXT motors and sensors
"""

import asyncio
import logging
from typing import Dict, Set, Optional, Callable, Any
import nxt.locator
import nxt.motor
import nxt.sensor
import nxt.sensor.generic
import nxt.sensor.digital

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HardwareManager:
    """Manages NXT hardware detection and state"""
    
    def __init__(self):
        self.brick: Optional[any] = None
        self.connected_motors: Set[str] = set()  # {'A', 'B', 'C'}
        self.connected_sensors: Dict[str, Any] = {}  # {'1': {'type': 'Touch', ...}, '2': {...}}
        self.battery_level: int = 0  # Battery voltage in millivolts
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
        logger.info(f"Notifying {len(self.change_callbacks)} callbacks about hardware change: {hardware_config}")
        for callback in self.change_callbacks:
            try:
                await callback(hardware_config)
                logger.debug(f"Callback {callback.__name__} executed successfully")
            except Exception as e:
                logger.error(f"Error in hardware change callback {callback.__name__}: {e}", exc_info=True)
    
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
        self.battery_level = 0
    
    def detect_motors(self) -> Set[str]:
        """
        Returns all motor ports (manual configuration)
        Returns: Set of port names ('A', 'B', 'C')
        
        Note: Since NXT firmware doesn't reliably detect motor presence without
        moving them, we use manual configuration and assume all ports are available.
        """
        if not self.brick or not self.is_connected:
            logger.debug("detect_motors: brick not connected")
            return set()
        
        # Manual configuration: assume all motor ports are available
        motors = {'A', 'B', 'C'}
        logger.info(f"Motor ports available: {motors}")
        return motors
    
    def detect_sensors(self) -> Dict[str, Any]:
        """
        Auto-detect sensors on all ports using NXT autodetection
        Returns: Dict of port -> sensor info
        """
        if not self.brick or not self.is_connected:
            return {}
        
        detected_sensors = {}
        
        for port_num in [1, 2, 3, 4]:
            try:
                port = getattr(nxt.sensor.Port, f'S{port_num}')
                
                # Try autodetection (only works for digital sensors with ID info)
                try:
                    sensor = self.brick.get_sensor(port)
                    sensor_type = type(sensor).__name__
                    sensor_info = {
                        'type': sensor_type,
                        'port': port_num,
                        'class': sensor_type
                    }
                    detected_sensors[str(port_num)] = sensor_info
                    logger.info(f"✓ Sensor detected on port {port_num}: {sensor_type}")
                except nxt.sensor.digital.SearchError:
                    # No digital sensor with ID, try generic analog detection
                    try:
                        # Try to read as a generic analog sensor
                        sensor = nxt.sensor.generic.TouchSensor(self.brick, port)
                        # If we can read a value, something is connected
                        value = sensor.get_sample()
                        sensor_info = {
                            'type': 'Analog',
                            'port': port_num,
                            'class': 'Generic'
                        }
                        detected_sensors[str(port_num)] = sensor_info
                        logger.info(f"✓ Analog sensor detected on port {port_num}")
                    except:
                        logger.debug(f"✗ No sensor on port {port_num}")
                except Exception as e:
                    logger.debug(f"✗ No sensor on port {port_num}: {e}")
            except Exception as e:
                logger.error(f"Error checking port {port_num}: {e}")
        
        if detected_sensors:
            logger.info(f"Sensor detection complete: {list(detected_sensors.keys())}")
        else:
            logger.info("Sensor detection complete: No sensors found")
        
        return detected_sensors
    
    async def monitor_hardware(self):
        """
        Continuously monitor hardware connections
        Detects changes and notifies callbacks
        """
        logger.info("Starting hardware monitoring")
        first_connection = True
        
        while True:
            try:
                # Try to connect if not connected
                if not self.is_connected:
                    logger.debug("Not connected, attempting to find NXT...")
                    if self.connect_brick():
                        # Connection established, detect hardware
                        logger.info("NXT connected! Detecting hardware...")
                        prev_motors = self.connected_motors.copy()
                        prev_sensors = self.connected_sensors.copy()
                        
                        self.connected_motors = self.detect_motors()
                        self.connected_sensors = self.detect_sensors()
                        
                        # Get battery level
                        try:
                            self.battery_level = self.brick.get_battery_level()
                            logger.info(f"Battery level: {self.battery_level}mV ({self.battery_level/1000:.2f}V)")
                        except Exception as e:
                            logger.warning(f"Could not read battery level: {e}")
                        
                        # Always notify on first connection or if hardware changed
                        if first_connection or prev_motors != self.connected_motors or prev_sensors != self.connected_sensors:
                            logger.info(f"Initial hardware state: motors={self.connected_motors}, sensors={list(self.connected_sensors.keys())}")
                            await self._notify_changes()
                            first_connection = False
                    else:
                        # Not connected, clear all hardware
                        if self.connected_motors or self.connected_sensors or self.battery_level > 0:
                            logger.info("Clearing hardware state (NXT disconnected)")
                            self.connected_motors.clear()
                            self.connected_sensors.clear()
                            self.battery_level = 0
                            await self._notify_changes()
                else:
                    # Already connected, keep alive and check for changes
                    try:
                        # Keep NXT awake
                        self.brick.keep_alive()
                        
                        # Update battery level
                        try:
                            self.battery_level = self.brick.get_battery_level()
                        except:
                            pass
                        
                        # Check for sensor changes (motors are manual config, so don't change)
                        prev_sensors = self.connected_sensors.copy()
                        self.connected_sensors = self.detect_sensors()
                        
                        if prev_sensors != self.connected_sensors:
                            logger.info(f"Sensor configuration changed: {list(prev_sensors.keys())} -> {list(self.connected_sensors.keys())}")
                            await self._notify_changes()
                    except Exception as e:
                        # Lost connection
                        logger.warning(f"Lost connection to NXT: {e}")
                        self.disconnect_brick()
                        first_connection = True
                        await self._notify_changes()
                
            except Exception as e:
                logger.error(f"Error in hardware monitoring: {e}", exc_info=True)
            
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
            "sensors": self.connected_sensors,
            "batteryLevel": self.battery_level,
            "batteryVoltage": round(self.battery_level / 1000.0, 2) if self.battery_level > 0 else 0
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

