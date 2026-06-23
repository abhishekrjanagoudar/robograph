from robograph.graph.engine import GraphEngine

class MermaidExporter:
    def __init__(self, engine: GraphEngine):
        self.engine = engine
        self.graph = engine.graph

    def export_package_graph(self) -> str:
        lines = ["graph TD"]
        packages = self.engine.get_nodes_by_type("package")
        for pkg in packages:
            lines.append(f"    {pkg}[{pkg}]")
        
        # Here we would add inter-package dependencies if captured in graph
        return "\n".join(lines)

    def export_node_topic_graph(self) -> str:
        lines = ["graph TD"]
        for u, v, data in self.graph.edges(data=True):
            relation = data.get("relation")
            if relation == "publishes":
                lines.append(f"    {u}([{u}]) -->|publishes| {v}(({v}))")
            elif relation == "subscribes":
                lines.append(f"    {v}(({v})) -->|subscribes| {u}([{u}])")
        return "\n".join(lines)

    def export_launch_graph(self) -> str:
        lines = ["graph TD"]
        for u, v, data in self.graph.edges(data=True):
            relation = data.get("relation")
            if relation == "includes":
                lines.append(f"    {u}[{u}] --> {v}[{v}]")
        return "\n".join(lines)
