import os
from pathlib import Path
from typing import List, Dict, Any

class WorkspaceScanner:
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)

    def scan(self) -> Dict[str, List[Path]]:
        """
        Recursively scan the workspace and identify key file types.
        """
        results = {
            "packages": [],       # package.xml
            "launch_files": [],   # *.launch.py, *.launch.xml
            "source_cpp": [],     # *.cpp, *.hpp, *.h
            "source_py": [],      # *.py (excluding launch)
            "messages": [],       # *.msg
            "services": [],       # *.srv
            "actions": [],        # *.action
            "config": [],         # *.yaml, *.rviz
            "cmakelists": [],     # CMakeLists.txt
            "setup_py": [],       # setup.py, setup.cfg
        }

        for path in self.root_path.rglob("*"):
            if not path.is_file():
                continue
                
            # Skip hidden directories like .git, and ROS2 generated dirs
            skip_dirs = {".git", "build", "install", "log"}
            if any(part in skip_dirs or part.startswith('.') for part in path.parts):
                continue
                
            if path.name == "package.xml":
                results["packages"].append(path)
            elif path.name.endswith(".launch.py") or path.name.endswith(".launch.xml"):
                results["launch_files"].append(path)
            elif path.suffix in [".cpp", ".hpp", ".h", ".c"]:
                results["source_cpp"].append(path)
            elif path.suffix == ".py":
                results["source_py"].append(path)
            elif path.suffix == ".msg":
                results["messages"].append(path)
            elif path.suffix == ".srv":
                results["services"].append(path)
            elif path.suffix == ".action":
                results["actions"].append(path)
            elif path.suffix in [".yaml", ".rviz"]:
                results["config"].append(path)
            elif path.name == "CMakeLists.txt":
                results["cmakelists"].append(path)
            elif path.name in ["setup.py", "setup.cfg"]:
                results["setup_py"].append(path)

        return results
