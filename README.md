# RoboGraph 🤖📊

**RoboGraph** is an AI-first codebase indexing and architecture mapping system designed to help LLMs, coding agents, and developers understand large robotics (ROS2) and software repositories without reading the entire codebase.

The primary goal is to drastically reduce token consumption and context acquisition time for AI agents such as **Claude Code, OpenAI Codex, Cursor, Cline, Roo Code**, and more. 

---

## 🚀 Features

### 🖥️ RoboGraph Studio v1
A blazing-fast, sub-100ms localhost web dashboard providing full architecture intelligence:
- **Multi-Graph Views**: Filter the architecture by Packages, Launch files, Nodes, Topics, Classes, Calls, and Subsystems.
- **Execution Flow Explorer**: Isolate the 2-hop execution path surrounding a selected node or topic.
- **Impact Analysis**: Automatically calculates Risk, Inbound, and Outbound effects for any entity.
- **AI Explainability**: Understand node functions and failure paths instantly without making an external LLM call.

### 🧠 AI Agent Context Injection
Automatically inject RoboGraph architecture intelligence directly into your favorite AI agent's configuration files without overwriting your custom rules! Supported agents include:
`CLAUDE.md`, `GEMINI.md`, `AGENTS.md`, `.cursorrules`, `.clinerules`, `.roo/rules.md`, `.windsurfrules`, etc.

### 🔌 Intelligent Parsing
- **C++ / Python AST Analysis**: Leverages `tree-sitter` and AST tools for highly accurate ROS2 node, topic, publisher, subscriber, class, and execution parsing.
- **Model Context Protocol (MCP)**: Native integration for coding agents to interactively query the graph.

---

## 🛠️ Installation

**Supported OS:** RoboGraph is designed primarily for **Linux (Ubuntu)** and ROS2 workspaces. It also fully supports Windows (via WSL2 or native).
**Prerequisites:** Python 3.11+

### 📦 Using pip (Recommended)
You can install RoboGraph globally using `pipx` (recommended for Python CLI tools) or `pip`:
```bash
pipx install robograph
# OR
pip install robograph
```

*Note: If the package is not yet on PyPI, you can install directly from GitHub:*
```bash
pip install git+https://github.com/abhishekrjanagoudar/robograph.git
```

### 🛠️ From Source (Development)
If you want to modify RoboGraph or install it from source:
```bash
git clone https://github.com/abhishekrjanagoudar/robograph.git
cd robograph
pip install -e .
```

---

## 💻 Usage

### 1. Build the Architecture Knowledge Graph
Navigate to your ROS2 workspace and run the analyzer. This parses all C++, Python, and Launch files to build `.robograph/knowledge.json`.
```bash
cd /path/to/ros2_ws
poetry run robograph analyze .
```

### 2. Launch RoboGraph Studio (Web UI)
Explore the codebase visually.
```bash
poetry run robograph ui
# Open http://localhost:8000
```

### 3. AI Agent Context Injection
RoboGraph will automatically scaffold and inject context into files like `CLAUDE.md` and `.cursorrules` so your AI agents immediately understand the architecture.
```bash
# Initialize missing agent configuration files
poetry run robograph init-agents .

# Inject architecture intelligence into all supported agent files
poetry run robograph inject --all .

# Verify your repository health and agent synchronization
poetry run robograph doctor .
```

### 4. Run the MCP Server
Allow compatible LLM clients to dynamically query the architecture.
```bash
poetry run robograph mcp
```

---

## 📂 Project Structure

- `robograph/analyzers/`: Workspace scanning and community (subsystem) detection.
- `robograph/parsers/`: Tree-sitter and AST parsers for C++, Python, ROS2, and XML.
- `robograph/graph/`: The core NetworkX based graph engine.
- `robograph/agent_injection/`: Safely injects context into AI Agent instruction files.
- `robograph/exporters/`: Converts graph data to Mermaid, JSON, or LLM-friendly Markdown.
- `robograph/api/`: FastAPI based backend server driving RoboGraph Studio.
- `robograph/cli/`: Typer-based command line interface.
- `robograph/mcp/`: Model Context Protocol definitions.

---

## 🤝 Contributing

Contributions are welcome! Focus areas:
- Advanced C++ Call Graph parsing using `libclang`.
- Action & Service graph mapping extensions.
- Semantic code search integrations.
- Extended execution timeline tracking.
