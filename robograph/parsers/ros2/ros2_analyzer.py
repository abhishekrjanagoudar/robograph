import ast
from pathlib import Path
from typing import List, Dict, Any

class Ros2PythonAnalyzer(ast.NodeVisitor):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.node_name = None
        self.publishers = []
        self.subscribers = []
        self.services = []
        self.clients = []
        self.classes = []
        self.functions = []
        self.variables = {}  # Symbol table for simple variable resolution
        self.context_stack = []
        self.function_calls = []

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

    def visit_Call(self, node: ast.Call):
        if self.context_stack:
            caller = self.context_stack[-1]
            callee = None
            if isinstance(node.func, ast.Name):
                callee = node.func.id
            elif isinstance(node.func, ast.Attribute):
                callee = node.func.attr
            if callee:
                self.function_calls.append((caller, callee))
                
        # Look for super().__init__("node_name")
        if isinstance(node.func, ast.Attribute) and node.func.attr == "__init__":
            if isinstance(node.func.value, ast.Call) and isinstance(node.func.value.func, ast.Name) and node.func.value.func.id == "super":
                if len(node.args) >= 1 and isinstance(node.args[0], ast.Constant):
                    self.node_name = node.args[0].value

        if isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
            if func_name == "create_publisher":
                self._extract_pub_sub(node, self.publishers)
            elif func_name == "create_subscription":
                self._extract_pub_sub(node, self.subscribers)
            elif func_name == "create_service":
                self._extract_srv(node, self.services)
            elif func_name == "create_client":
                self._extract_srv(node, self.clients)
        
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        inherits = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                inherits.append(base.id)
            elif isinstance(base, ast.Attribute):
                inherits.append(base.attr)
        self.classes.append({
            "name": node.name,
            "inherits": inherits,
            "line": node.lineno
        })
        self.context_stack.append(node.name)
        self.generic_visit(node)
        self.context_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # We might not want to capture every single nested function, but top level or class methods
        self.functions.append({
            "name": node.name,
            "line": node.lineno
        })
        self.context_stack.append(node.name)
        self.generic_visit(node)
        self.context_stack.pop()

    def _resolve_arg(self, arg: ast.AST) -> str:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
        elif isinstance(arg, ast.Name) and arg.id in self.variables:
            return self.variables[arg.id]
        return "unknown"

    def _extract_pub_sub(self, node: ast.Call, target_list: List[Dict[str, Any]]):
        if len(node.args) >= 2:
            topic_name = self._resolve_arg(node.args[1])
            
            # Try to get msg type
            msg_type = "unknown"
            msg_arg = node.args[0]
            if isinstance(msg_arg, ast.Name):
                msg_type = msg_arg.id
            elif isinstance(msg_arg, ast.Attribute):
                msg_type = msg_arg.attr
                
            target_list.append({"topic": topic_name, "msg_type": msg_type, "line": node.lineno})

    def _extract_srv(self, node: ast.Call, target_list: List[Dict[str, Any]]):
        if len(node.args) >= 2:
            srv_name = self._resolve_arg(node.args[1])
                
            msg_type = "unknown"
            msg_arg = node.args[0]
            if isinstance(msg_arg, ast.Name):
                msg_type = msg_arg.id
            elif isinstance(msg_arg, ast.Attribute):
                msg_type = msg_arg.attr
                
            target_list.append({"service": srv_name, "srv_type": msg_type, "line": node.lineno})

class PackageAnalyzer:
    @staticmethod
    def extract_package_info(package_xml_path: Path) -> Dict[str, Any]:
        import xml.etree.ElementTree as ET
        info = {"name": "", "dependencies": []}
        try:
            tree = ET.parse(package_xml_path)
            root = tree.getroot()
            name_elem = root.find("name")
            if name_elem is not None:
                info["name"] = name_elem.text

            for dep in root.findall("depend"):
                if dep.text:
                    info["dependencies"].append(dep.text)
            for dep in root.findall("exec_depend"):
                if dep.text:
                    info["dependencies"].append(dep.text)
            for dep in root.findall("build_depend"):
                if dep.text:
                    info["dependencies"].append(dep.text)
        except Exception:
            pass
        return info
