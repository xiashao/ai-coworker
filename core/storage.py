import os
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import sqlite3
from pathlib import Path


class TaskState(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    BLOCKED = "blocked"


class AgentRole(str, Enum):
    HR = "hr"
    PM = "pm"
    BA = "ba"
    DEV = "dev"
    QA = "qa"
    ARCHITECT = "architect"
    ORCHESTRATOR = "orchestrator"


class MessageType(str, Enum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"
    TASK_UPDATE = "task_update"
    REQUEST = "request"


@dataclass
class Message:
    id: str
    sender: str
    sender_role: str
    content: str
    message_type: MessageType
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "id": self.id,
            "sender": self.sender,
            "sender_role": self.sender_role,
            "content": self.content,
            "message_type": self.message_type.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class Task:
    id: str
    title: str
    description: str
    assignee: Optional[str] = None
    assignee_role: Optional[AgentRole] = None
    state: TaskState = TaskState.PENDING
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    priority: str = "medium"
    dependencies: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "assignee": self.assignee,
            "assignee_role": self.assignee_role.value if self.assignee_role else None,
            "state": self.state.value,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "priority": self.priority,
            "dependencies": self.dependencies,
            "notes": self.notes
        }


@dataclass
class Agent:
    id: str
    name: str
    role: AgentRole
    description: str
    system_prompt: str
    is_active: bool = True
    current_task_id: Optional[str] = None
    message_count: int = 0

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "description": self.description,
            "is_active": self.is_active,
            "current_task_id": self.current_task_id,
            "message_count": self.message_count
        }


class Session:
    def __init__(self, id: str = None):
        self.id = id or str(uuid.uuid4())
        self.messages: List[Message] = []
        self.agents: Dict[str, Agent] = {}
        self.tasks: Dict[str, Task] = {}
        self.created_at = datetime.now()
        self.turn_count = 0
        self.is_active = True
        self.handover_doc: Optional[str] = None

    def add_message(self, message: Message):
        self.messages.append(message)
        if message.message_type == MessageType.USER or message.message_type == MessageType.AGENT:
            self.turn_count += 1

    def check_session_end(self) -> tuple[bool, str]:
        """Check if session should end. Returns (should_end, reason)"""
        if self.turn_count >= 30:
            return True, "conversation_30_turns"

        for task in self.tasks.values():
            if task.state == TaskState.DONE:
                return True, "task_completed"

        return False, ""

    def generate_handover_doc(self) -> str:
        """Generate handover document for incomplete tasks"""
        incomplete_tasks = [t for t in self.tasks.values() if t.state != TaskState.DONE]
        
        doc = f"""# 离职交接文档
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Session ID: {self.id}

## 交接事项

### 未完成任务 ({len(incomplete_tasks)} 项)
"""
        for task in incomplete_tasks:
            doc += f"""
### {task.title}
- 描述: {task.description}
- 当前状态: {task.state.value}
- 负责人: {task.assignee or '未分配'}
- 优先级: {task.priority}
- 备注: {', '.join(task.notes) if task.notes else '无'}
"""

        doc += """
## 建议
1. PM需要申请额外人力
2. 交接给新成员继续跟进
"""
        return doc


class Storage:
    def __init__(self, db_path: str = "data/workspace.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                data TEXT,
                created_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()

    def save_session(self, session: Session):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        session_data = {
            "id": session.id,
            "messages": [m.to_dict() for m in session.messages],
            "agents": {k: v.to_dict() for k, v in session.agents.items()},
            "tasks": {k: v.to_dict() for k, v in session.tasks.items()},
            "turn_count": session.turn_count,
            "is_active": session.is_active,
            "handover_doc": session.handover_doc
        }
        
        cursor.execute(
            "INSERT OR REPLACE INTO sessions (id, data, created_at) VALUES (?, ?, ?)",
            (session.id, json.dumps(session_data), session.created_at.isoformat())
        )
        
        conn.commit()
        conn.close()

    def load_session(self, session_id: str) -> Optional[Session]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT data FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        data = json.loads(row[0])
        session = Session(data["id"])
        session.turn_count = data.get("turn_count", 0)
        session.is_active = data.get("is_active", True)
        session.handover_doc = data.get("handover_doc")
        
        for m in data.get("messages", []):
            msg = Message(
                id=m["id"],
                sender=m["sender"],
                sender_role=m["sender_role"],
                content=m["content"],
                message_type=MessageType(m["message_type"]),
                timestamp=datetime.fromisoformat(m["timestamp"]),
                metadata=m.get("metadata", {})
            )
            session.messages.append(msg)
        
        for k, v in data.get("agents", {}).items():
            agent = Agent(
                id=v["id"],
                name=v["name"],
                role=AgentRole(v["role"]),
                description=v["description"],
                system_prompt="",
                is_active=v.get("is_active", True),
                current_task_id=v.get("current_task_id"),
                message_count=v.get("message_count", 0)
            )
            session.agents[k] = agent
        
        for k, v in data.get("tasks", {}).items():
            task = Task(
                id=v["id"],
                title=v["title"],
                description=v["description"],
                assignee=v.get("assignee"),
                assignee_role=AgentRole(v["assignee_role"]) if v.get("assignee_role") else None,
                state=TaskState(v["state"]),
                created_by=v.get("created_by", ""),
                priority=v.get("priority", "medium"),
                notes=v.get("notes", [])
            )
            session.tasks[k] = task
        
        return session

    def list_sessions(self) -> List[dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, created_at FROM sessions ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        
        return [{"id": r[0], "created_at": r[1]} for r in rows]
