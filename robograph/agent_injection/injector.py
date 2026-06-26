import re
from pathlib import Path
from robograph.agent_injection.templates import generate_context
from robograph.graph.engine import GraphEngine

START_MARKER = "<!-- ROBOGRAPH_START -->"
END_MARKER = "<!-- ROBOGRAPH_END -->"

def inject_context(workspace_dir: str, agent_type: str, filename: str, engine: GraphEngine):
    context = generate_context(engine, agent_type)
    block = f"{START_MARKER}\n\n{context}\n\n{END_MARKER}"
    
    path = Path(workspace_dir) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    
    if path.exists():
        content = path.read_text(encoding="utf-8")
        pattern = re.compile(rf"{START_MARKER}.*?{END_MARKER}", re.DOTALL)
        if pattern.search(content):
            content = pattern.sub(block, content)
        else:
            content = f"{content.strip()}\n\n{block}\n"
        path.write_text(content, encoding="utf-8")
    else:
        path.write_text(f"{block}\n", encoding="utf-8")
        
    if agent_type in ("antigravity", "agy"):
        from robograph.agent_injection.templates import generate_skill_content
        skill_dir = Path(workspace_dir) / ".antigravity" / "skills" / "robograph"
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_path = skill_dir / "SKILL.md"
        skill_content = generate_skill_content(engine)
        skill_path.write_text(skill_content, encoding="utf-8")
