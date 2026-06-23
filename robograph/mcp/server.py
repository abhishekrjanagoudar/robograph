import networkx as nx
from typing import Dict, List, Any
from mcp.server.fastmcp import FastMCP
from robograph.graph.engine import GraphEngine
from robograph.intelligence.explainer import Explainer

# Initialize FastMCP server
mcp = FastMCP("RoboGraph")

def get_engine() -> GraphEngine:
    try:
        return GraphEngine.load(".robograph/knowledge.json")
    except Exception as e:
        raise RuntimeError("Knowledge graph not found. Run `robograph analyze` first.")

@mcp.tool()
def get_architectural_context() -> str:
    """Returns the full architectural Agent Context 2.0 markdown string."""
    from robograph.exporters.agent import AgentContextExporter
    engine = get_engine()
    exporter = AgentContextExporter(engine)
    return exporter.export()

@mcp.tool()
def get_debug_path(start: str, end: str) -> str:
    """Generates a debug execution path between two nodes or topics to trace data flow."""
    engine = get_engine()
    if not engine.graph.has_node(start) or not engine.graph.has_node(end):
        return f"Error: Start '{start}' or End '{end}' node not found in graph."
        
    try:
        path = nx.shortest_path(engine.graph, source=start, target=end)
        path_str = " -> ".join(path)
        
        result = [f"Debug Path found: {path_str}", "\nTo debug this flow:"]
        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            relation = engine.graph.get_edge_data(u, v).get("relation", "connects to")
            result.append(f" * Check if {u} [{relation}] {v}")
            
        return "\n".join(result)
    except nx.NetworkXNoPath:
        return f"No execution path found from '{start}' to '{end}'."

@mcp.tool()
def find_usages(symbol: str) -> str:
    """Reverse dependency search: Where is a message type or node used/spawned?"""
    engine = get_engine()
    usages = []
    
    for u, v, data in engine.graph.edges(data=True):
        if engine.graph.nodes[v].get("type") == "topic":
            msg_type = engine.graph.nodes[v].get("msg_type", "")
            if symbol in msg_type or symbol == v:
                node_data = engine.graph.nodes[u]
                file_path = node_data.get("file_path", "unknown")
                usages.append(f"Node '{u}' ({file_path}) {data.get('relation')} {v} [{msg_type}]")
                
    if not usages:
        return f"No usages found for '{symbol}'."
    return "\n".join(usages)

@mcp.tool()
def explain_entity(entity_name: str) -> str:
    """Explains the purpose, inputs, outputs, and common failure modes of a node or topic."""
    engine = get_engine()
    explainer = Explainer(engine)
    return explainer.explain(entity_name)

if __name__ == "__main__":
    mcp.run()
