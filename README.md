# RoboGraph 🤖📊

**RoboGraph** is an AI-first codebase indexing and architecture mapping system designed to reduce token consumption and context acquisition time for LLM coding agents (Claude, Cursor, Antigravity, etc.) working on large robotics (ROS2) projects.

It statically scans packages, C++/Python nodes, topics, launch trees, classes, and call graphs to construct a unified topological model, which is then served via a **Studio Web UI**, a **FastMCP Server**, or injected directly into local agent instruction files.

---

## 🚀 Key Features

*   🖥️ **Studio Web UI**: Sub-100ms localhost dashboard powered by `vis.js` for multi-graph views, execution flows, and impact analysis.
*   🔌 **Intelligent Parsing**: `tree-sitter-cpp` & AST parsing for Python and C++ files to identify topic publishers, subscribers, services, actions, class inheritances, and dynamic caller-callee execution edges.
*   🚀 **Launch Topologies**: Automatically resolves runtime `.yaml` configurations and `remaps` argument topic translations.
*   🧠 **Context Compression**: Reduces context size by up to 90% by replacing raw code lines with a concise architectural summary, saving LLM tokens.
*   🎯 **Context Injection**: Synchronizes architectural knowledge across **10+** agent configurations (Cursor, Claude, Gemini, Cline, Antigravity IDE, etc.).
*   🧩 **FastMCP Server**: Integrates with Model Context Protocol to expose architectural lookup tools directly to LLMs.

---

## 🛠️ Installation

*Prerequisites: Python 3.11+, Git*

### 🐧 Linux & WSL
```bash
git clone https://github.com/abhishekrjanagoudar/robograph.git
cd robograph
pipx install .  # Recommended for isolated global install
# OR
pip install --user .
```

### 🪟 Windows (via WSL)
For full ROS2 compatibility on Windows, always run RoboGraph **inside** WSL:
1. Open your **WSL terminal** (e.g., Ubuntu).
2. Follow the **Linux & WSL** steps above.

### 🐍 Virtual Environment (venv / poetry)
For isolated development without affecting system packages:
```bash
git clone https://github.com/abhishekrjanagoudar/robograph.git
cd robograph

# Using standard venv
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# OR Using Poetry
poetry install
```

---

## ⚠️ Troubleshooting Command Not Found
If the `robograph` command is not recognized, run the module directly as a fallback:
```bash
python -m robograph analyze .
python -m robograph ui
```
*(To fix permanently, add `export PATH="$HOME/.local/bin:$PATH"` to your `~/.bashrc`)*

---

## 💻 CLI Commands

Run these commands inside your ROS2 workspace (you can substitute `robograph` with `python -m robograph` or `poetry run robograph` if using fallbacks):

| Command | Description |
| :--- | :--- |
| `robograph analyze <path>` | Scans workspace and builds knowledge graph in `.robograph/knowledge.json` |
| `robograph ui [--port <port>]` | Starts the localhost Studio Web Dashboard (defaults to `http://localhost:8000`) |
| `robograph mcp` | Launches the stdio Model Context Protocol (FastMCP) server |
| `robograph list-agents` | Checks presence/missing state of AI agent files in the workspace |
| `robograph init-agents` | Creates missing configuration files for selected agent platforms |
| `robograph inject [--all]` | Injects the generated architectural context into existing agent files |
| `robograph doctor <path>` | Performs architecture health validation and agent context audits |
| `robograph explain <entity>` | Renders explainability summary and dependency info for a node or topic |
| `robograph debug <start> <end>` | Finds the shortest execution trace/data flow path between two nodes |
| `robograph export <format>` | Exports graph to `agent` (markdown text) or `mermaid` (`.mmd` graph) |

---

## 🔌 Model Context Protocol (MCP) Tools

When running `robograph mcp`, LLM agents can query your architecture using the following exposed tools:

*   `get_architectural_context()`: Returns the full compiled workspace architecture markdown block.
*   `get_debug_path(start, end)`: Traces the shortest execution path between two nodes or topics.
*   `find_usages(symbol)`: Performs a reverse dependency search to locate where a topic or node is spawned/referenced.
*   `explain_entity(entity_name)`: Provides detailed metrics, file location, and description of a node or topic.

---

## 🖥️ Studio Web UI API

The backend hosts a FastAPI server providing standard endpoints:

*   `GET /api/graph?view=<all|packages|launch|nodes|topics|classes|calls>`: Returns filtered nodes and edges.
*   `GET /api/search?q=<query>`: Global search across packages, nodes, classes, and functions.
*   `GET /api/impact/{entity_name}`: Computes inbound/outbound dependencies and risk criticality.
*   `GET /api/flow/{entity_name}`: Generates a local 2-hop sub-graph of execution flows.
*   `GET /api/recommendations`: Identifies root launch files and central chokepoints.

---

## 🤖 Supported Agent Platforms

RoboGraph synchronizes architectural mappings across the following systems:

*   **Claude Code**: `CLAUDE.md`
*   **Gemini CLI**: `GEMINI.md`
*   **Antigravity IDE**: `.agents/AGENTS.md` + `.agents/skills/robograph/SKILL.md`
*   **AGY CLI**: `.agents/AGENTS.md` + `.agents/skills/robograph/SKILL.md`
*   **Codex**: `AGENTS.md`
*   **Cursor**: `.cursorrules`
*   **Cline**: `.clinerules`
*   **Roo Code**: `.roo/rules.md`
*   **Continue**: `.continue/README.md`
*   **Windsurf**: `.windsurfrules`

---

## 🤝 Contributing

Contributions are welcome! 🚀
*(Current focus: `libclang` C++ call graphs, Service/Action mapping extensions, and visual layout features in Studio Web UI)*

