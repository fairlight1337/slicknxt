# SlickNXT - Node-RED Interface for Lego Mindstorms NXT

A modern web-based visual programming interface for controlling Lego Mindstorms NXT devices, inspired by Node-RED.

## Features

- 🎨 Beautiful, modern dark-themed UI
- 🔌 Drag-and-drop node-based programming interface
- ⚙️ Motor controller node with real-time feedback
- 💾 Save and load flow configurations
- 🚀 FastAPI backend with WebSocket support
- 🔄 Real-time state updates

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
python app/app.py
```

3. Open your browser and navigate to:
```
http://localhost:8000
```

## Usage

1. **Drag nodes from the palette** on the left sidebar onto the canvas
2. **Configure node parameters** using the controls within each node
3. **Connect nodes** by dragging from output ports to input ports
4. **Save your flow** using the "Save Flow" button
5. **Load saved flows** using the "Load Flow" button

## Available Nodes

### Motor Node
Controls an NXT motor with the following ports:

**Inputs:**
- `on_off` - Boolean: Turn motor on or off
- `forward` - Boolean: Direction (true = forward, false = reverse)
- `speed` - Integer (0-100): Motor speed

**Outputs:**
- `actual_on_off` - Boolean: Current motor status
- `actual_speed` - Integer: Current motor speed
- `actual_forward` - Boolean: Current motor direction

## Architecture

- **Backend**: FastAPI server with REST API and WebSocket support
- **Frontend**: React with ReactFlow for the visual editor
- **NXT Interface**: nxt-python library (integration ready)

## Development

The application structure:
```
SlickNXT/
├── app/
│   ├── app.py              # FastAPI server
│   └── static/
│       └── index.html      # Frontend application
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Future Enhancements

- Additional node types (sensors, logic gates, etc.)
- Real NXT device integration
- Flow execution engine
- Multi-device support
- Node configuration persistence
- Export/import flows as JSON

