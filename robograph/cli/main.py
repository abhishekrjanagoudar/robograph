import typer
import os
from pathlib import Path
from rich.console import Console

from robograph.analyzers.scanner import WorkspaceScanner
from robograph.analyzers.community_analyzer import CommunityAnalyzer
from robograph.parsers.python.ros2_analyzer import Ros2PythonAnalyzer, PackageAnalyzer
from robograph.parsers.python.launch_analyzer import LaunchAnalyzer
from robograph.parsers.cpp.cpp_analyzer import CppAnalyzer
from robograph.graph.engine import GraphEngine
from robograph.exporters.agent import AgentContextExporter
from robograph.exporters.mermaid import MermaidExporter
from robograph.agent_injection.detector import detect_agents
from robograph.agent_injection.injector import inject_context
from robograph.agent_injection.registry import AGENT_FILES

app = typer.Typer(help="RoboGraph: AI Codebase Architecture Mapper")
console = Console()

def get_engine() -> GraphEngine:
    engine = GraphEngine()
    knowledge_file = Path(".robograph/knowledge.json")
    if knowledge_file.exists():
        engine.load(str(knowledge_file))
    return engine

def find_package_for_file(file_path: Path, packages_map: list) -> str | None:
    file_path_abs = file_path.resolve()
    best_pkg_name = None
    best_len = -1
    for pkg_root, pkg_name in packages_map:
        try:
            pkg_root_abs = pkg_root.resolve()
            if pkg_root_abs == file_path_abs or pkg_root_abs in file_path_abs.parents:
                pkg_len = len(pkg_root_abs.parts)
                if pkg_len > best_len:
                    best_len = pkg_len
                    best_pkg_name = pkg_name
        except Exception:
            pass
    return best_pkg_name


@app.command()
def analyze(path: str = typer.Argument(..., help="Path to the repository to analyze")):
    """
    Analyze a repository and generate architectural graphs.
    """
    console.print(f"[bold green]Analyzing repository at:[/bold green] {path}")
    scanner = WorkspaceScanner(path)
    results = scanner.scan()
    engine = GraphEngine()
    
    packages_map = []
    # Process packages
    for pkg_xml in results["packages"]:
        pkg_xml_abs = pkg_xml.resolve()
        info = PackageAnalyzer.extract_package_info(pkg_xml_abs)
        if info["name"]:
            engine.add_package(info["name"])
            packages_map.append((pkg_xml_abs.parent, info["name"]))
            for dep in info["dependencies"]:
                engine.add_package(dep) # Ensure target node exists
                engine.add_package_dependency(info["name"], dep)
            
    executable_map = {}

    # Process python files (ROS2 Nodes)
    for py_file in results["source_py"]:
        py_file_abs = py_file.resolve()
        analyzer = Ros2PythonAnalyzer(str(py_file_abs))
        analyzer.analyze()
        
        # Determine node name
        node_name = analyzer.node_name if analyzer.node_name else py_file_abs.stem
        
        # Keep track of mapping from file and stem to node name
        executable_map[py_file_abs.name] = node_name
        executable_map[py_file_abs.stem] = node_name
        
        # Determine package name
        pkg_name = find_package_for_file(py_file_abs, packages_map)
        
        # If publishers/subscribers found, treat as node
        if analyzer.publishers or analyzer.subscribers or analyzer.services or analyzer.node_name:
            engine.add_node(node_name, package_name=pkg_name, file_path=str(py_file_abs))
            for pub in analyzer.publishers:
                engine.add_topic(pub["topic"], pub["msg_type"])
                engine.add_publisher(node_name, pub["topic"], line=pub.get("line"))
            for sub in analyzer.subscribers:
                engine.add_topic(sub["topic"], sub["msg_type"])
                engine.add_subscriber(node_name, sub["topic"], line=sub.get("line"))
        
        # Add classes and functions even if not a node
        for cls in analyzer.classes:
            engine.add_class(cls["name"], file_path=str(py_file_abs), line=cls["line"])
            for parent in cls["inherits"]:
                engine.add_class(parent)
                engine.add_class_inheritance(cls["name"], parent)
        for func in analyzer.functions:
            engine.add_function(func["name"], file_path=str(py_file_abs), line=func["line"])

    # Process C++ files
    for cpp_file in results["source_cpp"]:
        cpp_file_abs = cpp_file.resolve()
        analyzer = CppAnalyzer(str(cpp_file_abs))
        analyzer.analyze()
        
        node_name = analyzer.node_name if analyzer.node_name else cpp_file_abs.stem
        
        # Keep track of mapping from file and stem to node name
        executable_map[cpp_file_abs.name] = node_name
        executable_map[cpp_file_abs.stem] = node_name
        
        pkg_name = find_package_for_file(cpp_file_abs, packages_map)
        
        if analyzer.publishers or analyzer.subscribers or analyzer.services or analyzer.clients or analyzer.node_name:
            engine.add_node(node_name, package_name=pkg_name, file_path=str(cpp_file_abs))
            for pub in analyzer.publishers:
                engine.add_topic(pub["topic"], pub["msg_type"])
                engine.add_publisher(node_name, pub["topic"], line=pub.get("line"))
            for sub in analyzer.subscribers:
                engine.add_topic(sub["topic"], sub["msg_type"])
                engine.add_subscriber(node_name, sub["topic"], line=sub.get("line"))
                
        for cls in analyzer.classes:
            engine.add_class(cls["name"], file_path=str(cpp_file_abs), line=cls["line"])
            for parent in cls["inherits"]:
                engine.add_class(parent)
                engine.add_class_inheritance(cls["name"], parent)
        for func in analyzer.functions:
            engine.add_function(func["name"], file_path=str(cpp_file_abs), line=func["line"])

    # Process Launch files
    for launch_file in results["launch_files"]:
        launch_file_abs = launch_file.resolve()
        analyzer = LaunchAnalyzer(str(launch_file_abs))
        analyzer.analyze()
        
        pkg_name = find_package_for_file(launch_file_abs, packages_map)
        engine.add_launch_file(launch_file_abs.name, package_name=pkg_name, file_path=str(launch_file_abs))
        for include in analyzer.includes:
            engine.add_launch_include(launch_file_abs.name, include)
        for node in analyzer.nodes:
            # Resolve executable name to node name
            exe_name = node["executable"]
            resolved_node_name = executable_map.get(exe_name, exe_name)
            
            engine.add_node(resolved_node_name, package_name=node["package"])
            engine.graph.add_edge(launch_file_abs.name, resolved_node_name, relation="spawns")

    # Run Community Detection
    comm_analyzer = CommunityAnalyzer(engine)
    comm_analyzer.analyze()

    # Save to knowledge graph
    out_dirs = [Path(".robograph")]
    try:
        path_resolved = Path(path).resolve()
        cwd_resolved = Path(".").resolve()
        if path_resolved != cwd_resolved:
            out_dirs.append(path_resolved / ".robograph")
    except Exception:
        pass

    for out_dir in out_dirs:
        out_dir.mkdir(exist_ok=True)
        engine.save(str(out_dir / "knowledge.json"))

    console.print(f"[bold blue]Found packages:[/bold blue] {len(results['packages'])}")
    console.print(f"[bold blue]Found nodes:[/bold blue] {len(engine.get_nodes_by_type('ros_node'))}")
    console.print(f"[bold blue]Found C++ classes:[/bold blue] {len(engine.get_nodes_by_type('class'))}")
    console.print(f"[bold blue]Found launch files:[/bold blue] {len(engine.get_nodes_by_type('launch_file'))}")
    console.print(f"[bold blue]Found communities:[/bold blue] {len(engine.get_nodes_by_type('community'))}")
    
    # Priority 10: Context Compression Metrics
    try:
        raw_loc = 0
        all_files = results["source_py"] + results["source_cpp"] + results["launch_files"] + results["cmakelists"] + results["packages"]
        for fpath in all_files:
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    raw_loc += sum(1 for _ in f)
            except Exception:
                pass
                
        # We estimate context size based on current graph nodes/edges
        context_loc = len(engine.graph.nodes) * 4 + len(engine.graph.edges) * 2 + 100
        compression = ((raw_loc - context_loc) / raw_loc * 100) if raw_loc > 0 else 0.0
        
        console.print("\n[bold magenta]--- Context Compression Metrics ---[/bold magenta]")
        console.print(f"Repository: {raw_loc:,} LOC")
        console.print(f"Agent Context: ~{context_loc:,} LOC")
        console.print(f"Compression: {compression:.1f}%")
        console.print(f"Estimated Token Reduction: {compression:.1f}%")
        console.print("[bold magenta]-----------------------------------[/bold magenta]\n")
    except Exception as e:
        pass
        
    console.print("[bold green]Analysis complete. Knowledge graph saved to .robograph/knowledge.json[/bold green]")

    # Check agents
    present, missing = detect_agents(path)
    agent_names = {
            "claude": "Claude Code", "gemini": "Gemini CLI", "antigravity": "Antigravity IDE", 
            "agy": "AGY CLI", "codex": "Codex", "cursor": "Cursor", "cline": "Cline", 
            "roo": "Roo Code", "continue": "Continue", "windsurf": "Windsurf"
        }
    if present:
        console.print(f"\n[bold green]Found Agent Files: {len(present)}[/bold green]")
        for agent, filename in present.items():
            display_name = agent_names.get(agent, agent.title())
            display_fname = f"{filename} + Skill" if agent in ("antigravity", "agy") else filename
            console.print(f"  [green][OK][/green] {display_name} ({display_fname})")
    else:
        console.print("\n[bold yellow]Found Agent Files: 0[/bold yellow]")
        
    if missing:
        console.print(f"\n[bold yellow]Missing Agent Files: {len(missing)}[/bold yellow]")
        for agent, filename in missing.items():
            display_name = agent_names.get(agent, agent.title())
            display_fname = f"{filename} + Skill" if agent in ("antigravity", "agy") else filename
            console.print(f"  [red][X][/red] {display_name} ({display_fname})")
            
    console.print("\n[italic]Run 'robograph inject' to synchronize AI agent context.[/italic]")

@app.command()
def export(format: str = typer.Argument(..., help="Export format: agent or mermaid")):
    """
    Export the generated architectural data.
    """
    console.print(f"[bold green]Exporting in format:[/bold green] {format}")
    engine = get_engine()
    
    if len(engine.graph.nodes) == 0:
        console.print("[bold red]Graph is empty! Run 'robograph analyze .' first.[/bold red]")
        return

    if format == "agent":
        exporter = AgentContextExporter(engine)
        context = exporter.export()
        with open("agent_context.md", "w", encoding="utf-8") as f:
            f.write(context)
        console.print("[bold green]Generated agent_context.md[/bold green]")
    elif format == "mermaid":
        exporter = MermaidExporter(engine)
        with open("node_graph.mmd", "w", encoding="utf-8") as f:
            f.write(exporter.export_node_topic_graph())
        console.print("[bold green]Generated node_graph.mmd[/bold green]")
    else:
        console.print(f"[red]Unknown format:[/red] {format}")

@app.command()
def explain(entity: str):
    """
    Explain a specific node, topic, or component from the knowledge graph.
    """
    try:
        from robograph.intelligence.explainer import Explainer
    except ImportError:
        console.print("[bold red]Failed to import Explainer.[/bold red]")
        return
        
    engine = get_engine()
    if len(engine.graph.nodes) == 0:
        console.print("[bold red]Graph is empty! Run 'robograph analyze .' first.[/bold red]")
        return
        
    explainer = Explainer(engine)
    explanation = explainer.explain(entity)
    console.print(f"\n[bold green]Explanation:[/bold green]\n{explanation}\n")

@app.command()
def debug(start: str, end: str):
    """
    Generate a debug path between two nodes/topics to trace data flow.
    """
    import networkx as nx
    engine = get_engine()
    if len(engine.graph.nodes) == 0:
        console.print("[bold red]Graph is empty! Run 'robograph analyze .' first.[/bold red]")
        return
        
    if not engine.graph.has_node(start):
        console.print(f"[bold red]Start node '{start}' not found in graph.[/bold red]")
        return
    if not engine.graph.has_node(end):
        console.print(f"[bold red]End node '{end}' not found in graph.[/bold red]")
        return
        
    try:
        path = nx.shortest_path(engine.graph, source=start, target=end)
        console.print(f"\n[bold green]Debug Path found:[/bold green]")
        path_str = " -> ".join(path)
        console.print(path_str)
        
        console.print("\n[bold yellow]To debug this flow:[/bold yellow]")
        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            edge_data = engine.graph.get_edge_data(u, v)
            relation = edge_data.get("relation", "connects to")
            console.print(f" * Check if {u} [italic]{relation}[/italic] {v}")
            
    except nx.NetworkXNoPath:
        console.print(f"\n[bold yellow]No execution path found from '{start}' to '{end}'.[/bold yellow]")

@app.command()
def mcp():
    """
    Run the RoboGraph MCP Server over stdio.
    """
    try:
        from robograph.mcp.server import mcp as mcp_server
    except ImportError as e:
        console.print(f"[bold red]MCP dependencies not found: {e}. Did you run `poetry add mcp`?[/bold red]")
        return
        
    engine = get_engine()
    if len(engine.graph.nodes) == 0:
        console.print("[bold red]Warning: Graph is empty. Run `robograph analyze` in another terminal first.[/bold red]")
        
    # Start MCP stdio server
    mcp_server.run()

@app.command()
def ui(port: int = 8000):
    """
    Launch the RoboGraph Web Dashboard on localhost.
    """
    import uvicorn
    console.print(f"[bold green]Starting RoboGraph UI on http://localhost:{port}[/bold green]")
    uvicorn.run("robograph.api.main:app", host="127.0.0.1", port=port, reload=False)

@app.command()
def list_agents(path: str = typer.Argument(".", help="Path to workspace")):
    """List supported AI agents and their status in this repository."""
    present, missing = detect_agents(path)
    console.print("\n[bold blue]Supported Agent Platforms:[/bold blue]")
    
    agent_names = {
        "claude": "Claude Code", "gemini": "Gemini CLI", "antigravity": "Antigravity IDE", 
        "agy": "AGY CLI", "codex": "Codex", "cursor": "Cursor", "cline": "Cline", 
        "roo": "Roo Code", "continue": "Continue", "windsurf": "Windsurf"
    }
    
    for agent, filename in AGENT_FILES.items():
        status = "[green][OK][/green]" if agent in present else "[red][X][/red]"
        display_name = agent_names.get(agent, agent.title())
        display_fname = f"{filename} + Skill" if agent in ("antigravity", "agy") else filename
        status_text = "Present" if agent in present else "Missing"
        console.print(f"  {status} {display_name:<18} ({display_fname}) - {status_text}")
    console.print("")

@app.command()
def init_agents(
    path: str = typer.Argument(".", help="Path to workspace"),
    all: bool = typer.Option(False, "--all", help="Initialize all missing agent files")
):
    """Create all missing AI agent instruction files."""
    engine = get_engine()
    present, missing = detect_agents(path)
    if not missing:
        console.print("[green]All agent files are already present![/green]")
        return
        
    targets = []
    if all:
        targets = list(missing.keys())
    else:
        console.print("\n[bold blue]Missing Agent Platforms[/bold blue]")
        agent_names = {
            "claude": "Claude Code", "gemini": "Gemini CLI", "antigravity": "Antigravity IDE", 
            "agy": "AGY CLI", "codex": "Codex", "cursor": "Cursor", "cline": "Cline", 
            "roo": "Roo Code", "continue": "Continue", "windsurf": "Windsurf"
        }
        options = list(missing.items())
        for i, (agent, fname) in enumerate(options):
            display_name = agent_names.get(agent, agent.title())
            display_fname = f"{fname} + Skill" if agent in ("antigravity", "agy") else fname
            console.print(f"{i+1}. [yellow][Missing][/yellow] {display_name} ({display_fname})")
            
        selection = typer.prompt("\nSelect numbers to initialize (comma separated) or 'All'")
        if selection.lower() == "all":
            targets = [agent for agent, _ in options]
        else:
            try:
                indices = [int(x.strip())-1 for x in selection.split(",") if x.strip()]
                targets = [options[i][0] for i in indices if 0 <= i < len(options)]
            except ValueError:
                console.print("[red]Invalid selection.[/red]")
                return

    for agent in targets:
        filename = missing[agent]
        inject_context(path, agent, filename, engine)
        console.print(f"[green][OK] Created {filename}[/green]")

@app.command()
def inject(
    path: str = typer.Argument(".", help="Path to workspace"), 
    all: bool = typer.Option(False, "--all", help="Update all agent files"),
    claude: bool = typer.Option(False, "--claude", help="Update CLAUDE.md"),
    gemini: bool = typer.Option(False, "--gemini", help="Update GEMINI.md"),
    antigravity: bool = typer.Option(False, "--antigravity", help="Update AGENTS.md + Skill"),
    agy: bool = typer.Option(False, "--agy", help="Update AGENTS.md + Skill"),
    codex: bool = typer.Option(False, "--codex", help="Update AGENTS.md"),
    cursor: bool = typer.Option(False, "--cursor", help="Update .cursorrules"),
    cline: bool = typer.Option(False, "--cline", help="Update .clinerules"),
    roo: bool = typer.Option(False, "--roo", help="Update .roo/rules.md"),
    continue_dev: bool = typer.Option(False, "--continue", help="Update .continue/README.md"),
    windsurf: bool = typer.Option(False, "--windsurf", help="Update .windsurfrules")
):
    """Inject RoboGraph architecture intelligence into AI agent files."""
    engine = get_engine()
    present, missing = detect_agents(path)
    
    # Check flags
    targets = []
    if all:
        targets = list(AGENT_FILES.keys())
    else:
        if claude: targets.append("claude")
        if gemini: targets.append("gemini")
        if antigravity: targets.append("antigravity")
        if agy: targets.append("agy")
        if codex: targets.append("codex")
        if cursor: targets.append("cursor")
        if cline: targets.append("cline")
        if roo: targets.append("roo")
        if continue_dev: targets.append("continue")
        if windsurf: targets.append("windsurf")
        
    if not targets:
        # Interactive mode
        console.print("\n[bold blue]Detected Agent Platforms[/bold blue]")
        
        agent_names = {
            "claude": "Claude Code",
            "gemini": "Gemini CLI",
            "antigravity": "Antigravity IDE",
            "agy": "AGY CLI",
            "codex": "Codex",
            "cursor": "Cursor",
            "cline": "Cline",
            "roo": "Roo Code",
            "continue": "Continue",
            "windsurf": "Windsurf"
        }
        
        options = list(AGENT_FILES.items())
        for i, (agent, fname) in enumerate(options):
            status = "[green][OK][/green]" if agent in present else "[red][X][/red]"
            display_name = agent_names.get(agent, agent.title())
            display_fname = f"{fname} + Skill" if agent in ("antigravity", "agy") else fname
            console.print(f"{i+1}. {status} {display_name} ({display_fname})")
        
        selection = typer.prompt("\nSelect numbers (comma separated) or 'All'")
        if selection.lower() == "all":
            targets = [agent for agent, _ in options]
        else:
            try:
                indices = [int(x.strip())-1 for x in selection.split(",") if x.strip()]
                targets = [options[i][0] for i in indices if 0 <= i < len(options)]
            except ValueError:
                console.print("[red]Invalid selection.[/red]")
                return
            
    for agent in targets:
        fname = AGENT_FILES[agent]
        inject_context(path, agent, fname, engine)
        console.print(f"[green][OK] Injected context into {fname}[/green]")
        if agent in ("antigravity", "agy"):
            console.print("[green][OK] Generated .antigravity/skills/robograph/SKILL.md[/green]")

@app.command()
def doctor(path: str = typer.Argument(".", help="Path to workspace")):
    """Check repository architecture health and AI agent status."""
    engine = GraphEngine()
    knowledge_file = Path(path) / ".robograph" / "knowledge.json"
    
    console.print("\n[bold blue]RoboGraph Doctor[/bold blue]")
    
    if knowledge_file.exists():
        console.print("[green][OK] knowledge.json exists[/green]")
        engine.load(str(knowledge_file))
    else:
        console.print("[red][X] knowledge.json missing (Run 'robograph analyze')[/red]")
        return
        
    present, missing = detect_agents(path)
    for agent, fname in AGENT_FILES.items():
        fpath = Path(path) / fname
        if fpath.exists():
            content = fpath.read_text(encoding="utf-8")
            if "<!-- ROBOGRAPH_START -->" in content:
                console.print(f"[green][OK] {fname} synchronized[/green]")
            else:
                console.print(f"[yellow][!] {fname} exists but missing RoboGraph context[/yellow]")
        else:
            console.print(f"[yellow][!] {fname} missing[/yellow]")
    console.print("")

if __name__ == "__main__":
    app()
