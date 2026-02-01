"""
COYOTE V2.5 - Memory Manager

Persistent memory system for COYOTE. Stores and retrieves context across sessions.
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import List, Optional
from pathlib import Path
import json
import uuid


@dataclass
class Memory:
    """A single memory entry"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    content: str = ""
    category: str = "general"
    importance: int = 5  # 1-10
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    source: str = ""  # Where this memory came from

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "category": self.category,
            "importance": self.importance,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "tags": self.tags,
            "source": self.source
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Memory":
        return cls(
            id=data["id"],
            content=data["content"],
            category=data.get("category", "general"),
            importance=data.get("importance", 5),
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            tags=data.get("tags", []),
            source=data.get("source", "")
        )

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


class MemoryManager:
    """Manages persistent memories for COYOTE"""

    def __init__(self, workspace_path: Path):
        self.workspace = workspace_path
        self.memory_dir = workspace_path / "memory"
        self.memory_dir.mkdir(exist_ok=True)
        self.core_memory_path = workspace_path / "MEMORY.md"
        self._ensure_core_memory()

    def _ensure_core_memory(self):
        """Ensure core memory file exists"""
        if not self.core_memory_path.exists():
            self.core_memory_path.write_text("""# COYOTE Core Memory

## Blake Context
- Blake is the founder/CEO of Atlas Industrial
- Atlas does thermal symbiosis with industrial sites (cement plants, etc.)
- Uses ORC (Organic Rankine Cycle) technology
- Current focus: Midlothian site with Quikrete

## Communication Preferences
- Blake prefers concise, actionable updates
- Use SMS for urgent matters only
- Batch non-urgent items for daily digest

## Active Projects
- [Add active projects here]

## Key Contacts
- [Add key contacts here]

## Important Dates
- [Add important dates here]
""")

    def get_core_memory(self) -> str:
        """Get the core memory content"""
        return self.core_memory_path.read_text()

    def update_core_memory(self, content: str):
        """Update the core memory"""
        self.core_memory_path.write_text(content)

    def _get_daily_file(self, dt: date) -> Path:
        """Get the memory file for a specific date"""
        return self.memory_dir / f"{dt.isoformat()}.json"

    def add(
        self,
        content: str,
        category: str = "general",
        importance: int = 5,
        tags: List[str] = None,
        source: str = "",
        expires_in_days: Optional[int] = None
    ) -> Memory:
        """Add a new memory"""
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        memory = Memory(
            content=content,
            category=category,
            importance=importance,
            tags=tags or [],
            source=source,
            expires_at=expires_at
        )

        # Store in daily file (use local date to match search behavior)
        daily_file = self._get_daily_file(date.today())
        memories = []
        if daily_file.exists():
            memories = json.loads(daily_file.read_text())

        memories.append(memory.to_dict())
        daily_file.write_text(json.dumps(memories, indent=2))

        return memory

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        min_importance: int = 1,
        days_back: int = 30,
        limit: int = 10
    ) -> List[Memory]:
        """Search memories matching query"""
        query_lower = query.lower()
        results = []

        # Search daily files
        for i in range(days_back):
            dt = date.today() - timedelta(days=i)
            daily_file = self._get_daily_file(dt)
            if not daily_file.exists():
                continue

            memories = json.loads(daily_file.read_text())
            for mem_dict in memories:
                memory = Memory.from_dict(mem_dict)

                # Skip expired
                if memory.is_expired():
                    continue

                # Apply filters
                if category and memory.category != category:
                    continue
                if memory.importance < min_importance:
                    continue

                # Check if query matches
                if query_lower in memory.content.lower():
                    results.append(memory)
                elif any(query_lower in tag.lower() for tag in memory.tags):
                    results.append(memory)

                if len(results) >= limit:
                    break

            if len(results) >= limit:
                break

        # Sort by importance and recency
        results.sort(key=lambda m: (m.importance, m.created_at), reverse=True)
        return results[:limit]

    def get_recent(
        self,
        days: int = 7,
        category: Optional[str] = None,
        limit: int = 50
    ) -> List[Memory]:
        """Get recent memories"""
        results = []

        for i in range(days):
            dt = date.today() - timedelta(days=i)
            daily_file = self._get_daily_file(dt)
            if not daily_file.exists():
                continue

            memories = json.loads(daily_file.read_text())
            for mem_dict in memories:
                memory = Memory.from_dict(mem_dict)

                if memory.is_expired():
                    continue

                if category and memory.category != category:
                    continue

                results.append(memory)

                if len(results) >= limit:
                    break

            if len(results) >= limit:
                break

        return results

    def get_by_id(self, memory_id: str, days_back: int = 30) -> Optional[Memory]:
        """Get a specific memory by ID"""
        for i in range(days_back):
            dt = date.today() - timedelta(days=i)
            daily_file = self._get_daily_file(dt)
            if not daily_file.exists():
                continue

            memories = json.loads(daily_file.read_text())
            for mem_dict in memories:
                if mem_dict["id"] == memory_id:
                    return Memory.from_dict(mem_dict)

        return None

    def delete(self, memory_id: str, days_back: int = 30) -> bool:
        """Delete a memory by ID"""
        for i in range(days_back):
            dt = date.today() - timedelta(days=i)
            daily_file = self._get_daily_file(dt)
            if not daily_file.exists():
                continue

            memories = json.loads(daily_file.read_text())
            original_count = len(memories)
            memories = [m for m in memories if m["id"] != memory_id]

            if len(memories) < original_count:
                daily_file.write_text(json.dumps(memories, indent=2))
                return True

        return False

    def cleanup_expired(self) -> int:
        """Remove expired memories, return count removed"""
        removed = 0
        for file in self.memory_dir.glob("*.json"):
            memories = json.loads(file.read_text())
            original_count = len(memories)

            memories = [
                m for m in memories
                if not Memory.from_dict(m).is_expired()
            ]

            if len(memories) < original_count:
                removed += original_count - len(memories)
                file.write_text(json.dumps(memories, indent=2))

        return removed

    def get_stats(self) -> dict:
        """Get memory statistics"""
        total = 0
        by_category = {}
        oldest = None
        newest = None

        for file in self.memory_dir.glob("*.json"):
            memories = json.loads(file.read_text())
            for mem_dict in memories:
                memory = Memory.from_dict(mem_dict)
                if memory.is_expired():
                    continue

                total += 1

                if memory.category not in by_category:
                    by_category[memory.category] = 0
                by_category[memory.category] += 1

                if oldest is None or memory.created_at < oldest:
                    oldest = memory.created_at
                if newest is None or memory.created_at > newest:
                    newest = memory.created_at

        return {
            "total_memories": total,
            "by_category": by_category,
            "oldest": oldest.isoformat() if oldest else None,
            "newest": newest.isoformat() if newest else None
        }
