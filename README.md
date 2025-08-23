# Weevy - AI Agent Workflow Builder

Weevy is an intuitive visual workflow builder for creating and executing AI agent workflows. Build complex AI workflows with a drag-and-drop interface, connect different AI nodes, and execute them seamlessly.

## 🚀 Features

- **Visual Workflow Builder**: Drag-and-drop interface for creating AI agent workflows
- **Real-time Execution**: Execute workflows with live updates and streaming content
- **WebSocket Communication**: Real-time bidirectional communication between frontend and backend
- **Node-based Architecture**: Modular AI agents including Input, Brain, Knowledge Base, and Output nodes
- **Persistent Workflows**: Save and load workflows with auto-save functionality
- **Modern UI**: Clean, responsive interface built with modern web technologies

## 🏗️ Architecture

### Frontend
- **TypeScript/JavaScript**: Modern ES modules with full TypeScript support
- **Canvas System**: Interactive node-based visual editor
- **Component Panels**: Draggable node components and testing interface
- **WebSocket Client**: Real-time communication with backend services

### Backend
- **Python/FastAPI**: High-performance async API server
- **Node System**: Pluggable AI agent nodes
- **Workflow Engine**: Execute complex multi-node workflows
- **WebSocket Server**: Real-time updates and streaming responses

## 🛠️ Installation

### Prerequisites
- Node.js (v16 or higher)
- Python 3.8+
- TypeScript

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Manas-Kandi/weevy.git
   cd weevy
   ```

2. **Install frontend dependencies**
   ```bash
   npm install
   ```

3. **Setup Python backend**
   ```bash
   cd Backend
   pip install -r requirements.txt
   ```

4. **Build the project**
   ```bash
   npm run build
   ```

## 🚦 Usage

### Development Mode

1. **Start the backend server**
   ```bash
   npm run backend
   ```
   This starts the FastAPI server on `http://localhost:8000`

2. **Start the frontend in watch mode**
   ```bash
   npm run dev
   ```
   This starts TypeScript compilation in watch mode

3. **Serve the frontend**
   ```bash
   npm start
   ```
   This serves the frontend on `http://localhost:3000`

### Production Mode

1. **Build the project**
   ```bash
   npm run build
   ```

2. **Start the backend**
   ```bash
   npm run backend
   ```

3. **Serve the built files**
   ```bash
   npm start
   ```

## 📁 Project Structure

```
weevy/
├── Frontend/                 # Frontend application
│   ├── Canvas/              # Canvas system components
│   │   ├── Canvas.ts        # Main canvas implementation
│   │   ├── Components-Panel.ts # Component library panel
│   │   ├── Node-Design.ts   # Node design and styling
│   │   └── Testing-Panel.ts # Testing and execution panel
│   ├── index.html          # Main HTML file
│   ├── main.ts             # Application entry point
│   └── main.js             # Compiled JavaScript
├── Backend/                 # Backend API server
│   ├── main.py             # FastAPI server
│   ├── BrainNode.py        # AI brain node implementation
│   ├── InputNode.py        # Input node handling
│   ├── KnowledgeBaseNode.py # Knowledge base integration
│   ├── OutputNode.py       # Output formatting node
│   └── GeneralNodeLogic.py # Shared node functionality
├── package.json            # Project dependencies and scripts
├── tsconfig.json          # TypeScript configuration
└── README.md              # This file
```

## 🔧 Configuration

### TypeScript Configuration
The project uses ES2015 modules for browser compatibility. Configuration is in `tsconfig.json`.

### WebSocket Configuration
- Frontend connects to `ws://localhost:8000/ws`
- Backend serves WebSocket on port 8000
- Auto-reconnection with 3-second retry interval

## 🧪 Node Types

- **Input Node**: Handles user input and data ingestion
- **Brain Node**: Core AI processing and decision making  
- **Knowledge Base Node**: Integration with knowledge bases and databases
- **Output Node**: Formats and delivers results

## 🔄 Workflow Execution

1. **Design**: Create workflows using the visual canvas
2. **Configure**: Set up individual node parameters
3. **Execute**: Run workflows with real-time feedback
4. **Monitor**: Watch execution progress with live updates
5. **Results**: View formatted outputs and performance metrics

## 📊 Features in Detail

### Canvas System
- Drag-and-drop node placement
- Visual connection system
- Node selection and manipulation
- Zoom and pan capabilities

### Real-time Communication  
- WebSocket-based live updates
- Streaming content display
- Execution progress tracking
- Error handling and recovery

### Persistence
- Auto-save functionality
- Local storage integration
- Workflow import/export
- Session restoration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with FastAPI for high-performance backend
- TypeScript for type-safe frontend development  
- Modern ES modules for clean architecture
- WebSocket for real-time communication

---

**Weevy** - Building the future of AI workflow automation, one node at a time. 🧠✨