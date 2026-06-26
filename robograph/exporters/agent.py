import networkx as nx
from robograph.graph.engine import GraphEngine

class AgentContextExporter:
    def __init__(self, engine: GraphEngine):
        self.engine = engine
        self.graph = engine.graph

    def export(self) -> str:
        lines = []
        lines.append("# Project Summary")
        packages = self.engine.get_nodes_by_type("package")
        nodes = self.engine.get_nodes_by_type("ros_node")
        topics = self.engine.get_nodes_by_type("topic")
        launch_files = self.engine.get_nodes_by_type("launch_file")
        communities = self.engine.get_nodes_by_type("community")
        classes = self.engine.get_nodes_by_type("class")
        functions = self.engine.get_nodes_by_type("function")
        
        lines.append(f"Packages: {len(packages)}")
        lines.append(f"Nodes: {len(nodes)}")
        lines.append(f"Topics: {len(topics)}")
        lines.append(f"Launch Files: {len(launch_files)}")
        lines.append(f"Communities Identified: {len(communities)}")
        lines.append(f"Classes: {len(classes)}")
        lines.append(f"Functions: {len(functions)}")
        lines.append("\n---\n")

        lines.append("# Major Subsystems")
        if communities:
            for comm in communities:
                comm_nodes = [v for u, v, data in self.graph.edges(data=True) if u == comm and data.get("relation") == "contains_in_community"]
                if comm_nodes:
                    lines.append(f"## {comm}")
                    lines.append(f"Components: {', '.join(comm_nodes)}")
                    lines.append("")
        else:
            lines.append("No subsystems identified.")
            
        lines.append("\n---\n")
        lines.append("# Launch Flow")
        # Find root launch files
        for launch in launch_files:
            in_edges = [u for u, v, d in self.graph.edges(data=True) if v == launch and d.get("relation") == "includes"]
            if not in_edges:
                lines.append(f"## {launch} (Root)")
                self._print_launch_tree(launch, lines, level=1)
                lines.append("")
                
        lines.append("\n---\n")
        lines.append("# Runtime Execution Flows")
        lines.append("*(Under construction: ExecutionFlowAnalyzer will map full chains here)*")
        
        lines.append("\n---\n")
        lines.append("# Critical Topics")
        if len(topics) > 0:
            degree_dict = dict(self.graph.degree(topics))
            sorted_topics = sorted(degree_dict.items(), key=lambda x: x[1], reverse=True)[:10]
            for t, d in sorted_topics:
                lines.append(f"- **{t}** (Connections: {d})")
                
        lines.append("\n---\n")
        lines.append("# Important Nodes")
        for node in nodes:
            node_data = self.graph.nodes[node]
            lines.append(f"## {node}")
            lines.append(f"File: {node_data.get('file_path', 'unknown')}")
            
            publishes = []
            subscribers = []
            for u, v, data in self.graph.edges(data=True):
                relation = data.get("relation")
                if u == node and relation == "publishes":
                    publishes.append(v)
                elif v == node and relation == "subscribes":
                    subscribers.append(u)
                    
            if publishes:
                lines.append(f"Publishes: {', '.join(publishes)}")
            if subscribers:
                lines.append(f"Subscribes: {', '.join(subscribers)}")
            lines.append("")

        if classes:
            lines.append("\n---\n")
            lines.append("# Important Classes")
            for cls in classes:
                cls_data = self.graph.nodes[cls]
                file_path = cls_data.get('file_path', 'unknown')
                line = cls_data.get('line', '')
                lines.append(f"- **{cls}** (File: {file_path}{':' + str(line) if line else ''})")
                
                # Check for inheritance
                parents = []
                for u, v, data in self.graph.edges(data=True):
                    if u == cls and data.get("relation") == "inherits_from":
                        parents.append(v)
                if parents:
                    lines.append(f"  - Inherits from: {', '.join(parents)}")

        lines.append("\n---\n")
        lines.append("# Central Chokepoints")
        if len(self.graph.nodes) > 0:
            try:
                betweenness = nx.betweenness_centrality(self.graph.to_undirected())
                sorted_centrality = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)
                for node, score in sorted_centrality[:5]:
                    if score > 0:
                        lines.append(f"- **{node}** (Centrality Score: {score:.3f})")
            except Exception:
                lines.append("Could not compute chokepoints.")

        lines.append("\n---\n")
        lines.append("# Debugging Guide")
        lines.append("1. **Verify Topics**: For any central chokepoint topics listed above, run `ros2 topic hz <topic>` to ensure data is flowing.")
        lines.append("2. **QoS Profiles**: If publishers exist but subscribers aren't triggering, check QoS mismatches.")
        lines.append("3. **Launch Execution**: Follow the Launch Flow above to ensure your target node is actually being spawned.")
        
        lines.append("\n---\n")
        lines.append("# Failure Paths")
        lines.append("*(Under construction: DebugPathAnalyzer will map cascading failure routes here)*")

        lines.append("\n---\n")
        lines.append("# Recommended Files To Read First")
        relevant_files = set()
        for node in nodes + launch_files:
            fp = self.graph.nodes[node].get("file_path")
            if fp:
                relevant_files.add(fp)
                
        for file in sorted(list(relevant_files))[:5]:
            lines.append(f"- {file}")
            
        return "\n".join(lines)

    def _print_launch_tree(self, launch, lines, level=1):
        indent = "  " * level
        for u, v, d in self.graph.edges(data=True):
            if u == launch:
                if d.get("relation") == "includes":
                    lines.append(f"{indent}├── {v} (Include)")
                    self._print_launch_tree(v, lines, level+1)
                elif d.get("relation") == "spawns":
                    lines.append(f"{indent}├── {v} (Node)")
