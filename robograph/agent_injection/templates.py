from datetime import datetime
import networkx as nx
from robograph.graph.engine import GraphEngine

def generate_context(engine: GraphEngine, agent_type: str) -> str:
    packages = len(engine.get_nodes_by_type("package"))
    nodes = len(engine.get_nodes_by_type("ros_node"))
    topics = len(engine.get_nodes_by_type("topic"))
    classes = len(engine.get_nodes_by_type("class"))
    functions = len(engine.get_nodes_by_type("function"))
    
    # Get roots
    launch_files = engine.get_nodes_by_type("launch_file")
    roots = []
    for launch in launch_files:
        in_edges = [u for u, v, d in engine.graph.edges(data=True) if v == launch and d.get("relation") == "includes"]
        if not in_edges:
            roots.append(launch)
            
    # Get most important nodes (highest degree)
    central_nodes = []
    central_topics = []
    central_classes = []
    if len(engine.graph.nodes) > 0:
        deg = nx.degree_centrality(engine.graph)
        sorted_nodes = [n for n, d in sorted(deg.items(), key=lambda x: x[1], reverse=True)]
        central_nodes = [n for n in sorted_nodes if engine.graph.nodes[n].get("type") == "ros_node"][:5]
        central_topics = [n for n in sorted_nodes if engine.graph.nodes[n].get("type") == "topic"][:5]
        central_classes = [n for n in sorted_nodes if engine.graph.nodes[n].get("type") == "class"][:5]

    date_str = datetime.now().strftime("%Y-%m-%d")
    
    context = f"""# RoboGraph Architecture Context

Generated: {date_str}

Packages: {packages}
Nodes: {nodes}
Topics: {topics}
Classes: {classes}
Functions: {functions}

## Entry Point
{chr(10).join(roots) if roots else 'None found'}

## Important Nodes
{chr(10).join(central_nodes) if central_nodes else 'None found'}

## Important Classes
{chr(10).join(central_classes) if central_classes else 'None found'}

## Critical Topics
{chr(10).join(central_topics) if central_topics else 'None found'}

## Recommended Reading Order
1. Launch files
2. Important Nodes
3. Configuration

## Critical Failure Paths
Look at the edges in the knowledge graph for dependencies. If a critical topic drops, nodes consuming it will fail.
"""
    
    # Simple customization based on agent type
    if agent_type == "claude":
        context = "## Project Architecture\n" + context
    elif agent_type == "gemini":
        context = "## Repository Summary\n" + context
    elif agent_type == "cursor":
        context = "## Architecture Overview\n" + context
        
    return context

def generate_skill_content(engine: GraphEngine) -> str:
    packages = len(engine.get_nodes_by_type("package"))
    nodes = len(engine.get_nodes_by_type("ros_node"))
    topics = len(engine.get_nodes_by_type("topic"))
    
    launch_files = engine.get_nodes_by_type("launch_file")
    roots = []
    for launch in launch_files:
        in_edges = [u for u, v, d in engine.graph.edges(data=True) if v == launch and d.get("relation") == "includes"]
        if not in_edges:
            roots.append(launch)
            
    central_topics = []
    if len(engine.graph.nodes) > 0:
        deg = nx.degree_centrality(engine.graph)
        sorted_nodes = [n for n, d in sorted(deg.items(), key=lambda x: x[1], reverse=True)]
        central_topics = [n for n in sorted_nodes if engine.graph.nodes[n].get("type") == "topic"][:5]

    repo_summary = f"Packages: {packages}, Nodes: {nodes}, Topics: {topics}"
    entry_points = chr(10).join(roots) if roots else 'None found'
    critical_topics = chr(10).join(central_topics) if central_topics else 'None found'
    
    # We could theoretically extract flows, but for now we'll put a placeholder or summary
    flows = "See interactive dashboard at http://localhost:8000 for execution flows."

    return f"""---
name: robograph-architecture
description: Use this skill when understanding repository architecture, ROS2 nodes, launch files, execution flows, topics, services, actions, or debugging.
---

# RoboGraph Architecture Skill

Before reading source code:

1. Read architecture summary.
2. Read execution flows.
3. Read impact analysis.
4. Read debug paths.

Repository Summary:
{repo_summary}

Important Entry Points:
{entry_points}

Critical Topics:
{critical_topics}

Execution Flows:
{flows}
"""
