# 🚀 SlickNXT - Visual Programming Interface for Lego Mindstorms NXT

A modern, web-based visual programming environment inspired by Node-RED, designed for building control flows and interacting with Lego Mindstorms NXT devices. Features a beautiful, responsive UI with real-time execution on the server.

![SlickNXT Interface](https://img.shields.io/badge/Status-Active-green) ![Python](https://img.shields.io/badge/Python-3.13-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-Latest-teal)

---

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Usage](#usage)
- [Available Nodes](#available-nodes)
- [Technical Details](#technical-details)
- [Future Enhancements](#future-enhancements)

---

## ✨ Features

### Core Functionality
- **Visual Flow Editor**: Drag-and-drop interface for building control flows
- **Real-Time Execution**: Server-side execution engine with WebSocket updates (10Hz)
- **Type-Safe Connections**: Prevents invalid connections between incompatible port types
- **Live Value Display**: Port values displayed in real-time under each port label
- **Flow Management**: Save, load, delete, import, and export flows as JSON files

### User Experience
- **Mobile-Friendly**: Touch-optimized controls and gestures for iOS/tablet use
- **Responsive Design**: Beautiful, modern UI with dark theme
- **Single-Use Device Blocks**: Device blocks (motors, sensors) can only be instantiated once
- **Smart Control Disabling**: Manual controls automatically disable when ports are connected
- **Non-Intrusive Notifications**: Toast-style notifications for save/load/delete operations

### Advanced Features
- **19 Node Types**: Input/output, logic gates, timers, math operations, control blocks
- **History Display**: Real-time graphing of signal values over time
- **P Controller**: Proportional control for closed-loop systems
- **Integrator/Accumulator**: For generating ramps and integral control
- **Pulse & Delay Timers**: Time-based signal generation and processing

---

## 🏗️ Architecture

### Backend (Python + FastAPI)
```
app/
├── app.py                  # FastAPI server, WebSocket handler, API endpoints
├── execution_engine.py     # Flow executor and node implementations
└── static/
    └── index.html          # Frontend application (React + ReactFlow)

flows/                      # Saved flow JSON files (auto-created)
```

**Key Components:**
- **FlowExecutor**: Manages flow execution, topological sorting, and state updates
- **Node Classes**: 19 Python classes implementing node logic (one per node type)
- **WebSocket Server**: Broadcasts real-time state updates to all connected clients
- **REST API**: Endpoints for flow management (save, load, delete, list)

### Frontend (React + ReactFlow)
- **React 18**: Component-based UI framework
- **ReactFlow**: Visual node-based editor with drag-and-drop
- **WebSocket Client**: Receives real-time state updates from server
- **Custom Node Components**: 19 specialized React components for each node type
- **Port Type System**: Validates connections based on data types (boolean, number, any)

### Communication Flow
```
User Interaction → WebSocket → Server (FlowExecutor) → Node Execution → State Update → WebSocket → UI Update
```

---

## 🔧 Installation

### Prerequisites
- Python 3.13 or higher
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd SlickNXT
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the server:**
   ```bash
   python app/app.py
   ```

4. **Open in browser:**
   ```
   http://localhost:8000
   ```

### Dependencies
```
fastapi>=0.115.0
uvicorn>=0.32.0
pydantic>=2.9.0
```

---

## 🎮 Usage

### Getting Started

1. **Drag nodes** from the left palette onto the canvas
2. **Connect nodes** by dragging from an output port (right side) to an input port (left side)
3. **Configure nodes** using the controls inside each node
4. **Click ▶ Start** to begin flow execution
5. **Watch values** update in real-time on port labels

### Controls

| Action | Desktop | Mobile/iOS |
|--------|---------|------------|
| Add Node | Drag from palette | Drag from palette |
| Connect Ports | Click & drag | Touch & drag |
| Delete Connection | Select edge + Backspace | Select edge + 🗑️ button |
| Delete Node | Select node + Backspace | Select node + 🗑️ button |
| Pan Canvas | Click & drag | Touch & drag |
| Zoom | Mouse wheel | Pinch |

### Saving & Loading Flows

- **💾 Save**: Save current flow (prompts for name or overwrite confirmation)
- **📂 Load**: Load a previously saved flow from the list
- **🗑️ Delete**: Remove a saved flow (with confirmation)
- **📥 Import**: Import a flow from a JSON file on your device
- **📤 Export**: Export current flow as a JSON file

---

## 🧩 Available Nodes

### 📥 Virtual Input Nodes

#### **Dial**
- **Purpose**: Manual number input (0-100)
- **Outputs**: `value` (number)
- **Controls**: Slider
- **Use Case**: Testing, manual control

#### **Switch**
- **Purpose**: Manual boolean input (ON/OFF)
- **Outputs**: `value` (boolean)
- **Controls**: Toggle button (green=ON, red=OFF)
- **Use Case**: Testing, manual enable/disable

---

### 📤 Virtual Output Nodes

#### **Number Display**
- **Purpose**: Displays numeric values (0-100)
- **Inputs**: `value` (number)
- **Use Case**: Monitoring sensor values, outputs

#### **Bool Display**
- **Purpose**: Displays boolean values (red/green indicator)
- **Inputs**: `value` (boolean)
- **Use Case**: Monitoring state, debugging

#### **History Display**
- **Purpose**: Real-time graph of signal values over time
- **Inputs**: 
  - `value` (any): Signal to plot
  - `sampleRate` (number): Update rate (0.1s - 3s)
- **Controls**: Sample rate slider
- **Features**: Auto-detects boolean vs. numeric signals, keeps last 50 points
- **Use Case**: Signal analysis, debugging, control tuning

---

### 🔌 Connected Device Nodes

#### **Motor** *(Single-use per port)*
- **Purpose**: Control NXT motor (future: actual NXT integration)
- **Inputs**:
  - `onOff` (boolean): Enable motor
  - `forward` (boolean): Direction
  - `speed` (number 0-100): Motor speed
- **Outputs**: Same as inputs (mirrored)
- **Controls**: Checkboxes, slider
- **Note**: Each motor port (A, B, C) can only be used once in a flow

---

### 🧮 Logic Gates

#### **AND Gate**
- **Inputs**: `a`, `b` (boolean)
- **Outputs**: `output` = `a AND b`

#### **OR Gate**
- **Inputs**: `a`, `b` (boolean)
- **Outputs**: `output` = `a OR b`

#### **XOR Gate**
- **Inputs**: `a`, `b` (boolean)
- **Outputs**: `output` = `a XOR b`

#### **NOT Gate**
- **Inputs**: `input` (boolean)
- **Outputs**: `output` = `NOT input`

---

### ⏱️ Timer Nodes

#### **Pulse Timer**
- **Purpose**: Generates repeating ON/OFF pulses
- **Inputs**:
  - `enable` (boolean): Start/stop timer
  - `onDuration` (number): How long to stay ON (seconds)
  - `offDuration` (number): How long to stay OFF (seconds)
- **Outputs**: `output` (boolean): Pulsing signal
- **Controls**: Duration sliders, Start/Stop buttons
- **Use Case**: Blinking lights, periodic actions

#### **Delay Timer**
- **Purpose**: Delays any signal by a specified time
- **Inputs**:
  - `input` (any): Signal to delay
  - `delay` (number): Delay time (0-10 seconds)
- **Outputs**: `output` (any): Delayed signal
- **Controls**: Delay slider
- **Use Case**: Sequencing, debouncing

---

### 🔀 Signal Processing

#### **Comparator**
- **Purpose**: Compares two numbers
- **Inputs**: `a`, `b` (number)
- **Outputs**: `output` (boolean): Result of comparison
- **Controls**: Mode selector (`>`, `<`, `==`)
- **Use Case**: Threshold detection, conditional logic

#### **Bool Gate**
- **Purpose**: Passes signal through only when enabled
- **Inputs**:
  - `signal` (any): Signal to gate
  - `enable` (boolean): Gate control
- **Outputs**: `output` (any): Signal if enabled, null otherwise
- **Use Case**: Conditional signal routing

#### **Cap/Clamp**
- **Purpose**: Clamps a number between min and max
- **Inputs**:
  - `input` (number): Value to clamp
  - `min`, `max` (number): Optional range override
- **Outputs**: `output` (number): Clamped value
- **Controls**: Min/Max sliders (default: 0-100)
- **Use Case**: Value limiting, safety constraints

---

### ➕ Math Operations

#### **Add (+)**
- **Inputs**: `a`, `b` (number, default: 0)
- **Outputs**: `output` = `a + b`

#### **Subtract (-)**
- **Inputs**: `a`, `b` (number, default: 0)
- **Outputs**: `output` = `a - b`

---

### 🎛️ Control Blocks

#### **P Controller**
- **Purpose**: Proportional control for closed-loop systems
- **Inputs**:
  - `enabled` (boolean): Enable controller
  - `pGain` (number 0-5): Proportional gain
  - `setpoint` (number): Target value
  - `currentValue` (number): Current measurement
- **Outputs**: `output` (number): Control signal = `P × (setpoint - current)`
- **Controls**: Enable button, P gain slider
- **Use Case**: Speed control, position control, temperature regulation

#### **Integrator/Accumulator**
- **Purpose**: Accumulates values over time (integration)
- **Inputs**:
  - `input` (number): Value to integrate
  - `enabled` (boolean): Enable integration
  - `reset` (boolean): Reset accumulator to 0
- **Outputs**: `output` (number): Accumulated value (-1000 to 1000)
- **Controls**: Enable button, Reset button
- **Use Case**: Ramp generation, integral control (PI/PID), state tracking

---

## 🔬 Technical Details

### Port Types
- **`boolean`**: True/False values
- **`number`**: Integer values (typically 0-100 range)
- **`any`**: Accepts any type (used for pass-through nodes)

### Connection Validation
The system prevents invalid connections:
- Boolean → Number: ❌ Invalid
- Number → Boolean: ❌ Invalid
- Any → Boolean: ✅ Valid
- Any → Number: ✅ Valid
- Number → Any: ✅ Valid

### Execution Model
1. **Topological Sorting**: Nodes are sorted to respect data dependencies
2. **10Hz Loop**: Server executes flow at 10 times per second
3. **State Broadcasting**: Every execution cycle broadcasts state updates via WebSocket
4. **Input Queue**: User interactions are queued and processed each cycle

### Data Flow
```
User Input → WebSocket → Input Queue → Node Execution → Output Calculation → State Update → WebSocket → UI
```

### File Format
Flows are saved as JSON with the following structure:
```json
{
  "nodes": [
    {
      "id": "dialNode-123456",
      "type": "dialNode",
      "position": {"x": 100, "y": 200},
      "data": { ... }
    }
  ],
  "edges": [
    {
      "id": "edge-123",
      "source": "dialNode-123456",
      "target": "motorNode-789",
      "sourceHandle": "out-value",
      "targetHandle": "in-speed"
    }
  ],
  "metadata": {
    "name": "My Flow",
    "created": "2025-10-09T...",
    "modified": "2025-10-09T..."
  }
}
```

---

## 🚀 Future Enhancements

### Near-Term
- [ ] **NXT Integration**: Connect to actual Lego Mindstorms NXT devices via USB
- [ ] **Sensor Nodes**: Touch, light, ultrasonic, sound sensors
- [ ] **Advanced Motors**: Encoder feedback, synchronization
- [ ] **More Logic**: NAND, NOR, edge detection, flip-flops
- [ ] **PID Controller**: Full PID implementation with tuning

### Long-Term
- [ ] **Sub-Flows**: Reusable node groups/macros
- [ ] **Bluetooth Support**: Wireless NXT communication
- [ ] **Data Logging**: Save sensor data to CSV
- [ ] **Python Code Export**: Generate standalone Python scripts
- [ ] **Multi-Device**: Control multiple NXT bricks simultaneously
- [ ] **Collaboration**: Multi-user editing with conflict resolution
- [ ] **Mobile App**: Native iOS/Android apps

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

### Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Test thoroughly
5. Commit: `git commit -m 'Add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Open a pull request

---

## 📄 License

This project is provided as-is for educational and research purposes.

---

## 🙏 Acknowledgments

- **Node-RED**: Inspiration for the visual programming paradigm
- **ReactFlow**: Excellent React library for building node-based editors
- **FastAPI**: Modern, fast Python web framework
- **Lego Mindstorms**: The amazing robotics platform that started it all

---

## 📧 Contact

For questions, suggestions, or issues, please open an issue on the repository.

---

**Happy Building! 🎉**
