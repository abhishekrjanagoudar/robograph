from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import networkx as nx
from typing import Dict, Any, List

from robograph.graph.engine import GraphEngine
from robograph.intelligence.explainer import Explainer
from pathlib import Path

app = FastAPI(title="RoboGraph Studio v1 API", description="AI Codebase Architecture Mapper API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

@app.on_event("startup")
def load_graph():
    engine = GraphEngine()
    knowledge_file = Path(".robograph/knowledge.json")
    if knowledge_file.exists():
        engine.load(str(knowledge_file))
    app.state.engine = engine

@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")

def get_engine() -> GraphEngine:
    return app.state.engine

@app.get("/api/graph")
def get_graph(view: str = "all", filter_pkg: str = None):
    engine = get_engine()
    nodes = []
    edges = []
    
    allowed_types = set()
    if view == "packages":
        allowed_types = {"package"}
    elif view == "launch":
        allowed_types = {"launch_file", "ros_node", "package"}
    elif view == "nodes":
        allowed_types = {"ros_node", "package"}
    elif view == "topics":
        allowed_types = {"ros_node", "topic"}
    elif view == "classes":
        allowed_types = {"class", "ros_node"}
    elif view == "calls":
        allowed_types = {"function", "class", "ros_node"}
    elif view == "subsystems":
        allowed_types = {"community", "package"}
    else:
        allowed_types = None # all
        
    for node, data in engine.graph.nodes(data=True):
        ntype = data.get("type", "unknown")
        if allowed_types and ntype not in allowed_types:
            continue
            
        nodes.append({
            "id": node,
            "label": node,
            "type": ntype,
            "community": data.get("community", 0),
            "file_path": data.get("file_path", "")
        })
        
    node_ids = {n["id"] for n in nodes}
        
    for u, v, data in engine.graph.edges(data=True):
        if u in node_ids and v in node_ids:
            edges.append({
                "from": u,
                "to": v,
                "relation": data.get("relation", "unknown"),
                "confidence": data.get("confidence", 1.0)
            })
        
    return {"nodes": nodes, "edges": edges}

@app.get("/api/search")
def search(q: str):
    engine = get_engine()
    query = q.lower()
    
    results = {
        "nodes": [],
        "classes": [],
        "files": [],
        "topics": [],
        "packages": [],
        "functions": [],
        "launch_files": []
    }
    
    for node, data in engine.graph.nodes(data=True):
        ntype = data.get("type", "unknown")
        label = str(node).lower()
        file_path = str(data.get("file_path", "")).lower()
        
        if query in label or query in file_path:
            item = {"id": node, "type": ntype, "file_path": data.get("file_path", "")}
            
            if ntype == "ros_node": results["nodes"].append(item)
            elif ntype == "class": results["classes"].append(item)
            elif ntype == "topic": results["topics"].append(item)
            elif ntype == "package": results["packages"].append(item)
            elif ntype == "function": results["functions"].append(item)
            elif ntype == "launch_file": results["launch_files"].append(item)
            
    return results

@app.get("/api/impact/{entity_name}")
def impact_analysis(entity_name: str):
    engine = get_engine()
    if not engine.graph.has_node(entity_name):
        raise HTTPException(status_code=404, detail="Entity not found")
        
    in_edges = []
    out_edges = []
    
    for u, v, data in engine.graph.in_edges(entity_name, data=True):
        in_edges.append({"node": u, "relation": data.get("relation", "unknown"), "type": engine.graph.nodes[u].get("type", "unknown")})
        
    for u, v, data in engine.graph.out_edges(entity_name, data=True):
        out_edges.append({"node": v, "relation": data.get("relation", "unknown"), "type": engine.graph.nodes[v].get("type", "unknown")})
        
    # Heuristics for Risk
    risk = "LOW"
    criticality = "LOW"
    
    if len(in_edges) > 5 or len(out_edges) > 5:
        risk = "HIGH"
        criticality = "HIGH"
    elif len(in_edges) > 2 or len(out_edges) > 2:
        risk = "MEDIUM"
        criticality = "MEDIUM"
        
    return {
        "entity": entity_name,
        "type": engine.graph.nodes[entity_name].get("type", "unknown"),
        "inbound": in_edges,
        "outbound": out_edges,
        "risk": risk,
        "criticality": criticality
    }

@app.get("/api/flow/{entity_name}")
def execution_flow(entity_name: str):
    engine = get_engine()
    if not engine.graph.has_node(entity_name):
        raise HTTPException(status_code=404, detail="Entity not found")
        
    # Build a local subgraph for 2 hops
    subgraph_nodes = set([entity_name])
    for u, v in nx.bfs_edges(engine.graph, entity_name, depth_limit=2):
        subgraph_nodes.add(v)
    for u, v in nx.bfs_edges(engine.graph.reverse(), entity_name, depth_limit=2):
        subgraph_nodes.add(v)
        
    flow_nodes = []
    flow_edges = []
    for n in subgraph_nodes:
        data = engine.graph.nodes[n]
        flow_nodes.append({"id": n, "label": n, "type": data.get("type", "unknown")})
        
    for u, v, data in engine.graph.edges(subgraph_nodes, data=True):
        if v in subgraph_nodes:
            flow_edges.append({"from": u, "to": v, "relation": data.get("relation", "unknown")})
            
    return {"nodes": flow_nodes, "edges": flow_edges}

@app.get("/api/metrics")
def get_metrics():
    engine = get_engine()
    
    counts = {
        "packages": 0, "nodes": 0, "topics": 0, "classes": 0, "functions": 0, "launch_files": 0
    }
    
    for n, data in engine.graph.nodes(data=True):
        ntype = data.get("type", "unknown")
        if ntype == "package": counts["packages"] += 1
        elif ntype == "ros_node": counts["nodes"] += 1
        elif ntype == "topic": counts["topics"] += 1
        elif ntype == "class": counts["classes"] += 1
        elif ntype == "function": counts["functions"] += 1
        elif ntype == "launch_file": counts["launch_files"] += 1
        
    try:
        deg = nx.degree_centrality(engine.graph)
        top_connected = sorted(deg.items(), key=lambda x: x[1], reverse=True)[:5]
        top_connected = [{"node": n, "score": s} for n, s in top_connected]
    except:
        top_connected = []
        
    return {
        "counts": counts,
        "top_connected": top_connected
    }

@app.get("/api/explain/{entity_name}")
def explain_entity(entity_name: str):
    engine = get_engine()
    explainer = Explainer(engine)
    return {"explanation": explainer.explain(entity_name)}

@app.get("/api/debug")
def debug_path(start: str, end: str):
    engine = get_engine()
    if not engine.graph.has_node(start) or not engine.graph.has_node(end):
        raise HTTPException(status_code=404, detail="Start or end node not found.")
        
    try:
        path = nx.shortest_path(engine.graph, source=start, target=end)
        details = []
        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            relation = engine.graph.get_edge_data(u, v).get("relation", "connects to")
            details.append({"from": u, "to": v, "relation": relation})
            
        return {"path": path, "details": details}
    except nx.NetworkXNoPath:
        return {"path": [], "details": [], "message": "No path found."}

@app.get("/api/recommendations")
def get_recommendations():
    engine = get_engine()
    launch_files = engine.get_nodes_by_type("launch_file")
    roots = []
    for launch in launch_files:
        in_edges = [u for u, v, d in engine.graph.edges(data=True) if v == launch and d.get("relation") == "includes"]
        if not in_edges:
            roots.append(launch)
            
    central_nodes = []
    if len(engine.graph.nodes) > 0:
        try:
            betweenness = nx.betweenness_centrality(engine.graph.to_undirected())
            sorted_centrality = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)
            central_nodes = [{"node": n, "score": s} for n, s in sorted_centrality[:5] if s > 0]
        except Exception:
            pass
            
    return {"root_launch_files": roots, "central_chokepoints": central_nodes}


