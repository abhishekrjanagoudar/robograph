from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Set

class Topic(BaseModel):
    name: str
    msg_type: Optional[str] = None

class Service(BaseModel):
    name: str
    srv_type: Optional[str] = None

class Action(BaseModel):
    name: str
    action_type: Optional[str] = None

class RosNode(BaseModel):
    name: str
    file_path: str
    publishers: List[Topic] = Field(default_factory=list)
    subscribers: List[Topic] = Field(default_factory=list)
    service_servers: List[Service] = Field(default_factory=list)
    service_clients: List[Service] = Field(default_factory=list)
    action_servers: List[Action] = Field(default_factory=list)
    action_clients: List[Action] = Field(default_factory=list)
    parameters: List[str] = Field(default_factory=list)

class LaunchFile(BaseModel):
    name: str
    file_path: str
    includes: List[str] = Field(default_factory=list)
    nodes: List[str] = Field(default_factory=list)
    arguments: List[str] = Field(default_factory=list)

class Package(BaseModel):
    name: str
    path: str
    dependencies: List[str] = Field(default_factory=list)
    executables: List[str] = Field(default_factory=list)
    nodes: List[RosNode] = Field(default_factory=list)
    launch_files: List[LaunchFile] = Field(default_factory=list)

class ClassDef(BaseModel):
    name: str
    file_path: str
    inherits: List[str] = Field(default_factory=list)
    methods: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)

class FunctionDef(BaseModel):
    name: str
    file_path: str
    calls: List[str] = Field(default_factory=list)

class Workspace(BaseModel):
    path: str
    packages: List[Package] = Field(default_factory=list)
    classes: List[ClassDef] = Field(default_factory=list)
    functions: List[FunctionDef] = Field(default_factory=list)
