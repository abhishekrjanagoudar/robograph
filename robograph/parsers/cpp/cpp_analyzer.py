import tree_sitter
try:
    import tree_sitter_cpp
except ImportError:
    tree_sitter_cpp = None

from typing import List, Dict, Any

class CppAnalyzer:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.classes = []
        self.functions = []
        
        self.node_name = None
        self.publishers = []
        self.subscribers = []
        self.services = []
        self.clients = []
        self.variables = {}  # Track variable assignments for strings
        
        if tree_sitter_cpp is not None:
            self.language = tree_sitter.Language(tree_sitter_cpp.language())
            self.parser = tree_sitter.Parser()
            self.parser.set_language(self.language)
        else:
            self.parser = None

    def analyze(self):
        if not self.parser:
            return
            
        with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
        tree = self.parser.parse(bytes(content, "utf8"))
        self._traverse(tree.root_node, content.encode("utf8"))

    def _traverse(self, node, source: bytes):
        if node.type == "class_specifier":
            name_node = node.child_by_field_name("name")
            if name_node:
                class_name = source[name_node.start_byte:name_node.end_byte].decode("utf8")
                
                # Extract inheritance
                inherits = []
                base_clause = node.child_by_field_name("base")
                if base_clause:
                    for child in base_clause.children:
                        if child.type == "type_identifier":
                            inherits.append(source[child.start_byte:child.end_byte].decode("utf8"))
                            
                self.classes.append({"name": class_name, "inherits": inherits, "line": node.start_point[0] + 1})

        elif node.type == "function_definition":
            decl_node = node.child_by_field_name("declarator")
            if decl_node:
                func_name = self._extract_identifier(decl_node, source)
                if func_name:
                    self.functions.append({"name": func_name, "line": node.start_point[0] + 1})
        
        elif node.type == "declaration":
            # Track variable assignments for topic strings
            type_node = node.child_by_field_name("type")
            decl_node = node.child_by_field_name("declarator")
            if decl_node and decl_node.type == "init_declarator":
                var_name_node = decl_node.child_by_field_name("declarator")
                value_node = decl_node.child_by_field_name("value")
                if var_name_node and value_node and value_node.type == "string_literal":
                    var_name = source[var_name_node.start_byte:var_name_node.end_byte].decode("utf8")
                    string_val = source[value_node.start_byte:value_node.end_byte].decode("utf8").strip('"')
                    self.variables[var_name] = string_val
        
        elif node.type == "call_expression":
            func_node = node.child_by_field_name("function")
            args_node = node.child_by_field_name("arguments")
            
            if func_node:
                func_name = self._extract_func_name(func_node, source)
                if func_name:
                    if func_name == "Node" or func_name == "rclcpp::Node":
                        if args_node and len(args_node.children) > 1: # first is '('
                            first_arg = args_node.children[1]
                            if first_arg.type == "string_literal":
                                self.node_name = source[first_arg.start_byte:first_arg.end_byte].decode("utf8").strip('"')
                    
                    elif func_name in ["create_publisher", "create_subscription", "create_client", "create_service"]:
                        msg_type = self._extract_template_arg(func_node, source) or "Unknown"
                        
                        topic_name = "unknown"
                        if args_node and len(args_node.children) > 1:
                            first_arg = args_node.children[1]
                            if first_arg.type == "string_literal":
                                topic_name = source[first_arg.start_byte:first_arg.end_byte].decode("utf8").strip('"')
                            elif first_arg.type == "identifier":
                                var_name = source[first_arg.start_byte:first_arg.end_byte].decode("utf8")
                                topic_name = self.variables.get(var_name, f"{{{var_name}}}")
                                
                        entry = {"topic": topic_name, "msg_type": msg_type, "line": node.start_point[0] + 1}
                        if func_name == "create_publisher":
                            self.publishers.append(entry)
                        elif func_name == "create_subscription":
                            self.subscribers.append(entry)
                        elif func_name == "create_service":
                            self.services.append(entry)
                        elif func_name == "create_client":
                            self.clients.append(entry)
                            
        for child in node.children:
            self._traverse(child, source)
            
    def _extract_identifier(self, node, source: bytes) -> str:
        if node.type in ["identifier", "field_identifier", "type_identifier"]:
            return source[node.start_byte:node.end_byte].decode("utf8")
        for child in node.children:
            res = self._extract_identifier(child, source)
            if res:
                return res
        return None
        
    def _extract_func_name(self, node, source: bytes) -> str:
        if node.type in ["identifier", "qualified_identifier"]:
            return source[node.start_byte:node.end_byte].decode("utf8")
        elif node.type == "field_expression":
            field_node = node.child_by_field_name("field")
            if field_node:
                return self._extract_func_name(field_node, source)
        elif node.type == "template_function":
            name_node = node.child_by_field_name("name")
            if name_node:
                return source[name_node.start_byte:name_node.end_byte].decode("utf8")
        return None
        
    def _extract_template_arg(self, node, source: bytes) -> str:
        if node.type == "template_function":
            args = node.child_by_field_name("arguments")
            if args and len(args.children) > 1:
                arg_node = args.children[1] # < Type >
                return source[arg_node.start_byte:arg_node.end_byte].decode("utf8")
        elif node.type == "field_expression":
            field_node = node.child_by_field_name("field")
            if field_node:
                return self._extract_template_arg(field_node, source)
        return None
