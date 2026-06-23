import ast
from typing import List, Dict

class LaunchAnalyzer(ast.NodeVisitor):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.includes = []
        self.nodes = []

    def analyze(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            content = f.read()
        try:
            tree = ast.parse(content)
            self.visit(tree)
        except SyntaxError:
            pass

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            if node.func.id == "IncludeLaunchDescription":
                self._extract_include(node)
            elif node.func.id == "Node":
                self._extract_node(node)
        self.generic_visit(node)

    def _extract_include(self, node: ast.Call):
        # Extremely simplified heuristic to find launch file string
        for walk_node in ast.walk(node):
            if isinstance(walk_node, ast.Constant) and isinstance(walk_node.value, str):
                if walk_node.value.endswith(".launch.py") or walk_node.value.endswith(".launch.xml"):
                    self.includes.append(walk_node.value)
                    return

    def _extract_node(self, node: ast.Call):
        # Look for package and executable args
        pkg = "unknown"
        executable = "unknown"
        for kw in node.keywords:
            if kw.arg == "package" and isinstance(kw.value, ast.Constant):
                pkg = kw.value.value
            elif kw.arg == "executable" and isinstance(kw.value, ast.Constant):
                executable = kw.value.value
        if pkg != "unknown" or executable != "unknown":
            self.nodes.append({"package": pkg, "executable": executable})
