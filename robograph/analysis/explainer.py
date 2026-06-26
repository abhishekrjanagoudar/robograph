from robograph.graph.engine import GraphEngine

class Explainer:
    def __init__(self, engine: GraphEngine):
        self.engine = engine
        self.graph = engine.graph

    def explain(self, entity_name: str) -> str:
        if not self.graph.has_node(entity_name):
            return f"Entity '{entity_name}' not found in the knowledge graph."

        node_data = self.graph.nodes[entity_name]
        node_type = node_data.get("type", "unknown")
        
        if node_type == "ros_node":
            return self._explain_node(entity_name)
        elif node_type == "topic":
            return self._explain_topic(entity_name)
        else:
            return f"Explainability for type '{node_type}' is not yet fully supported.\nData: {node_data}"

    def _explain_node(self, node_name: str) -> str:
        lines = []
        lines.append(f"Explain: Node '{node_name}'")
        lines.append("=" * 40)
        
        # Purpose Heuristic
        publishes = []
        subscribers = []
        for u, v, data in self.graph.edges(data=True):
            if u == node_name and data.get("relation") == "publishes":
                publishes.append(v)
            elif v == node_name and data.get("relation") == "subscribes":
                subscribers.append(u)
                
        purpose = "Processes data and interacts with the ROS2 system."
        if any("cmd_vel" in p for p in publishes):
            purpose = "Controller node: Drives the robot by publishing velocity commands."
        elif any("scan" in s or "camera" in s for s in subscribers):
            purpose = "Perception node: Processes sensor data."
        
        lines.append("\nNode Purpose:")
        lines.append(purpose)
        
        lines.append("\nInputs (Subscribes):")
        for sub in subscribers:
            lines.append(f" * {sub}")
        if not subscribers:
            lines.append(" * (None detected)")
            
        lines.append("\nOutputs (Publishes):")
        for pub in publishes:
            lines.append(f" * {pub}")
        if not publishes:
            lines.append(" * (None detected)")
            
        lines.append("\nImportant Files:")
        node_data = self.graph.nodes[node_name]
        lines.append(f" * {node_data.get('file_path', 'unknown')}")
        
        lines.append("\nDependencies:")
        lines.append(" *(Derived from graph structure)*")
        
        lines.append("\nCommon Failure Modes:")
        if subscribers:
            lines.append(f" * Missing incoming data on {subscribers[0]}")
            lines.append(" * QoS profile mismatch on inputs")
        if publishes:
            lines.append(f" * Downstream nodes not receiving {publishes[0]}")
            
        return "\n".join(lines)
        
    def _explain_topic(self, topic_name: str) -> str:
        lines = []
        lines.append(f"Explain: Topic '{topic_name}'")
        lines.append("=" * 40)
        
        publishers = [u for u, v, d in self.graph.edges(data=True) if v == topic_name and d.get("relation") == "publishes"]
        subscribers = [v for u, v, d in self.graph.edges(data=True) if u == topic_name and d.get("relation") == "subscribes"]
        
        lines.append(f"\nMessage Type: {self.graph.nodes[topic_name].get('msg_type', 'Unknown')}")
        
        lines.append("\nPublishers:")
        for p in publishers:
            lines.append(f" * {p}")
            
        lines.append("\nSubscribers:")
        for s in subscribers:
            lines.append(f" * {s}")
            
        return "\n".join(lines)
