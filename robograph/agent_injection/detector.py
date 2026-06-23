import os
from pathlib import Path
from robograph.agent_injection.registry import AGENT_FILES

def detect_agents(workspace_dir: str):
    present = {}
    missing = {}
    for agent, filename in AGENT_FILES.items():
        path = Path(workspace_dir) / filename
        if path.exists():
            present[agent] = filename
        else:
            missing[agent] = filename
    return present, missing
