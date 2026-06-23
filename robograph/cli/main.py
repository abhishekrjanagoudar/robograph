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

@app.command()
def analyze(path: str = typer.Argument(..., help="Path to the repository to analyze")):
    """
    Analyze a repository and generate architectural graphs.
    """
    console.print(f"[bold green]Analyzing repository at:[/bold green] {path}")
    scanner = WorkspaceScanner(path)
    results = scanner.scan()
    engine = GraphEngine()
    
    # Process packages
    for pkg_xml in results["packages"]:
        info = PackageAnalyzer.extract_package_info(pkg_xml)
        if info["name"]:
            engine.add_package(info["name"])
            for dep in info["dependencies"]:
                engine.add_package(dep) # Ensure target node exists
                engine.add_package_dependency(info["name"], dep)
            
    # Process python files (ROS2 Nodes)
    for py_file in results["source_py"]:
        analyzer = Ros2PythonAnalyzer(str(py_file))
        analyzer.analyze()
        
        # Determine node name
        node_name = analyzer.node_name if analyzer.node_name else py_file.stem
        
        # If publishers/subscribers found, treat as node
        if analyzer.publishers or analyzer.subscribers or analyzer.services or analyzer.node_name:
            engine.add_node(node_name, file_path=str(py_file))
            for pub in analyzer.publishers:
                engine.add_topic(pub["topic"], pub["msg_type"])
                engine.add_publisher(node_name, pub["topic"], line=pub.get("line"))
            for sub in analyzer.subscribers:
                engine.add_topic(sub["topic"], sub["msg_type"])
                engine.add_subscriber(node_name, sub["topic"], line=sub.get("line"))

    # Process C++ files
    for cpp_file in results["source_cpp"]:
        analyzer = CppAnalyzer(str(cpp_file))
        analyzer.analyze()
        
        node_name = analyzer.node_name if analyzer.node_name else cpp_file.stem
        
        if analyzer.publishers or analyzer.subscribers or analyzer.services or analyzer.clients or analyzer.node_name:
            engine.add_node(node_name, file_path=str(cpp_file))
            for pub in analyzer.publishers:
                engine.add_topic(pub["topic"], pub["msg_type"])
                engine.add_publisher(node_name, pub["topic"], line=pub.get("line"))
            for sub in analyzer.subscribers:
                engine.add_topic(sub["topic"], sub["msg_type"])
                engine.add_subscriber(node_name, sub["topic"], line=sub.get("line"))
                
        for cls in analyzer.classes:
            engine.add_class(cls["name"], file_path=str(cpp_file), line=cls["line"])
            for parent in cls["inherits"]:
                engine.add_class(parent)
                engine.add_class_inheritance(cls["name"], parent)
        for func in analyzer.functions:
            engine.add_function(func["name"], file_path=str(cpp_file), line=func["line"])

    # Process Launch files
    for launch_file in results["launch_files"]:
        analyzer = LaunchAnalyzer(str(launch_file))
        analyzer.analyze()
        engine.add_launch_file(launch_file.name, file_path=str(launch_file))
        for include in analyzer.includes:
            engine.add_launch_include(launch_file.name, include)
        for node in analyzer.nodes:
            # Connect launch file to executable node (simplified)
            engine.add_node(node["executable"], package_name=node["package"])
            engine.graph.add_edge(launch_file.name, node["executable"], relation="spawns")

    # Run Community Detection
    comm_analyzer = CommunityAnalyzer(engine)
    comm_analyzer.analyze()

    # Save to knowledge graph
    out_dir = Path(".robograph")
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
    console.print(f"\n[bold blue]Found Agent Files:[/bold blue] {len(present)}")
    for agent, fname in present.items():
        console.print(f"  [green][OK] {fname}[/green]")
        
    if missing:
        console.print(f"\n[bold yellow]Missing Agent Files:[/bold yellow] {len(missing)}")
        for agent, fname in missing.items():
            console.print(f"  [red][X] {fname}[/red]")
            
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
    console.print("\n[bold blue]Supported AI Agent Instructions:[/bold blue]")
    for agent, f in AGENT_FILES.items():
        if agent in present:
            console.print(f"  [green][OK] {f.ljust(20)} Present[/green]")
        else:
            console.print(f"  [red][X] {f.ljust(20)} Missing[/red]")
    console.print("")

@app.command()
def init_agents(path: str = typer.Argument(".", help="Path to workspace")):
    """Create all missing AI agent instruction files."""
    engine = get_engine()
    present, missing = detect_agents(path)
    if not missing:
        console.print("[green]All agent files are already present![/green]")
        return
        
    for agent, filename in missing.items():
        inject_context(path, agent, filename, engine)
        console.print(f"[green][OK] Created {filename}[/green]")

@app.command()
def inject(
    path: str = typer.Argument(".", help="Path to workspace"), 
    all: bool = typer.Option(False, "--all", help="Update all agent files"),
    claude: bool = typer.Option(False, "--claude", help="Update CLAUDE.md"),
    gemini: bool = typer.Option(False, "--gemini", help="Update GEMINI.md"),
    codex: bool = typer.Option(False, "--codex", help="Update AGENTS.md"),
    cursor: bool = typer.Option(False, "--cursor", help="Update .cursorrules"),
    cline: bool = typer.Option(False, "--cline", help="Update .clinerules"),
    roo: bool = typer.Option(False, "--roo", help="Update .roo/rules.md"),
    continue_dev: bool = typer.Option(False, "--continue", help="Update .continue/README.md"),
    openhands: bool = typer.Option(False, "--openhands", help="Update AGENTS.md"),
    aider: bool = typer.Option(False, "--aider", help="Update AGENTS.md"),
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
        if codex: targets.append("codex")
        if cursor: targets.append("cursor")
        if cline: targets.append("cline")
        if roo: targets.append("roo")
        if continue_dev: targets.append("continue")
        if openhands: targets.append("openhands")
        if aider: targets.append("aider")
        if windsurf: targets.append("windsurf")
        
    if not targets:
        # Interactive mode
        console.print("\n[bold blue]Detected AI Agent Files[/bold blue]")
        options = list(AGENT_FILES.items())
        for i, (agent, fname) in enumerate(options):
            status = "[green][OK][/green]" if agent in present else "[red][X][/red]"
            console.print(f"{i+1}. {status} {fname}")
        
        selection = typer.prompt("Select numbers (comma separated) or 'All'")
        if selection.lower() == "all":
            targets = [agent for agent, _ in options]
        else:
            indices = [int(x.strip())-1 for x in selection.split(",")]
            targets = [options[i][0] for i in indices]
            
    for agent in targets:
        fname = AGENT_FILES[agent]
        inject_context(path, agent, fname, engine)
        console.print(f"[green][OK] Injected context into {fname}[/green]")

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
