import networkx as nx
from robograph.graph.engine import GraphEngine

class CommunityAnalyzer:
    def __init__(self, engine: GraphEngine):
        self.engine = engine
        
    def analyze(self):
        # We need an undirected graph for Louvain clustering
        undirected_graph = self.engine.graph.to_undirected()
        
        # Remove nodes with degree 0 to avoid noise
        isolated = list(nx.isolates(undirected_graph))
        undirected_graph.remove_nodes_from(isolated)
        
        if len(undirected_graph.nodes) == 0:
            return
            
        try:
            # Requires networkx >= 2.7
            communities = nx.community.louvain_communities(undirected_graph, seed=42)
            
            # Map communities to a flat format and add back to the main DiGraph
            for comm_id, node_set in enumerate(communities):
                # Find the most connected node in this community to act as the title
                top_node = None
                max_degree = -1
                for node in node_set:
                    degree = undirected_graph.degree[node]
                    if degree > max_degree:
                        max_degree = degree
                        top_node = node
                
                comm_name = f"Subsystem: {top_node}" if top_node else f"Community_{comm_id}"
                self.engine.graph.add_node(comm_name, type="community", community_id=comm_id)
                
                for node in node_set:
                    if self.engine.graph.has_node(node):
                        self.engine.graph.nodes[node]["community"] = comm_id
                        self.engine.graph.add_edge(comm_name, node, relation="contains_in_community", confidence=0.8, source="CommunityAnalyzer")
        except AttributeError as e:
            # Fallback if networkx doesn't have louvain_communities
            print(f"Warning: Louvain communities not available in this networkx version: {e}")
        except Exception as e:
            print(f"Warning: Community detection failed: {e}")
