import ast
from pathlib import Path
from typing import List, Dict

class LaunchAnalyzer(ast.NodeVisitor):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.includes = []
        self.nodes = []
        self.variables = {}

    def analyze(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            content = f.read()
        try:
            tree = ast.parse(content)
            self.visit(tree)
        except SyntaxError:
            pass

    def visit_Assign(self, node: ast.Assign):
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.variables[target.id] = node.value.value
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant):
        if isinstance(node.value, str):
            val = node.value
            if val.endswith(".launch.py") or val.endswith(".launch.xml"):
                if val != Path(self.file_path).name:
                    if val not in self.includes:
                        self.includes.append(val)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if self._is_node_call(node.func):
            self._extract_node(node)
        self.generic_visit(node)

    def _is_node_call(self, func_node) -> bool:
        if isinstance(func_node, ast.Name):
            return func_node.id == "Node"
        elif isinstance(func_node, ast.Attribute):
            return func_node.attr == "Node"
        return False

    def _resolve_arg(self, arg: ast.AST) -> str:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
        elif isinstance(arg, ast.Name) and arg.id in self.variables:
            return self.variables[arg.id]
        return "unknown"

    def _extract_node(self, node: ast.Call):
        pkg = "unknown"
        executable = "unknown"
        for kw in node.keywords:
            if kw.arg == "package":
                pkg = self._resolve_arg(kw.value)
            elif kw.arg == "executable":
                executable = self._resolve_arg(kw.value)
        if pkg != "unknown" or executable != "unknown":
            self.nodes.append({"package": pkg, "executable": executable})

