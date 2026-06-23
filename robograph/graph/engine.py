import networkx as nx
from typing import List, Dict, Any, Optional
import json

class GraphEngine:
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_package(self, package_name: str, **attributes):
        self.graph.add_node(package_name, type="package", **attributes)
        
    def add_package_dependency(self, source_pkg: str, target_pkg: str):
        self.graph.add_edge(source_pkg, target_pkg, relation="depends_on", confidence=1.0, source="PackageXML")

    def add_node(self, node_name: str, package_name: Optional[str] = None, **attributes):
        self.graph.add_node(node_name, type="ros_node", **attributes)
        if package_name:
            self.graph.add_edge(package_name, node_name, relation="contains", confidence=1.0, source="AST")

    def add_topic(self, topic_name: str, msg_type: Optional[str] = None):
        if not self.graph.has_node(topic_name):
            self.graph.add_node(topic_name, type="topic", msg_type=msg_type)

    def add_publisher(self, node_name: str, topic_name: str, **attributes):
        self.graph.add_edge(node_name, topic_name, relation="publishes", confidence=1.0, source="AST", **attributes)

    def add_subscriber(self, node_name: str, topic_name: str, **attributes):
        self.graph.add_edge(topic_name, node_name, relation="subscribes", confidence=1.0, source="AST", **attributes)

    def add_launch_file(self, launch_name: str, package_name: Optional[str] = None, **attributes):
        self.graph.add_node(launch_name, type="launch_file", **attributes)
        if package_name:
            self.graph.add_edge(package_name, launch_name, relation="contains", confidence=1.0, source="LaunchAST")

    def add_launch_include(self, parent_launch: str, child_launch: str):
        self.graph.add_edge(parent_launch, child_launch, relation="includes", confidence=1.0, source="LaunchAST")

    def add_class(self, class_name: str, **attributes):
        self.graph.add_node(class_name, type="class", **attributes)
        
    def add_class_inheritance(self, child_class: str, parent_class: str):
        self.graph.add_edge(child_class, parent_class, relation="inherits", confidence=1.0, source="AST")

    def add_function(self, func_name: str, **attributes):
        self.graph.add_node(func_name, type="function", **attributes)

    def add_function_call(self, caller: str, callee: str):
        self.graph.add_edge(caller, callee, relation="calls", confidence=1.0, source="AST")

    def get_nodes_by_type(self, node_type: str) -> List[str]:
        return [n for n, attr in self.graph.nodes(data=True) if attr.get("type") == node_type]

    def save(self, filepath: str):
        data = nx.node_link_data(self.graph)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
            
    def load(self, filepath: str):
        with open(filepath, 'r') as f:
            data = json.load(f)
        self.graph = nx.node_link_graph(data)
