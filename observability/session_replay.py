"""
Session replay engine for debugging and auditing agent interactions.
"""
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, AsyncGenerator
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

try:
    import sqlite3
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False


class EventType(Enum):
    AGENT_START = "agent_start"
    AGENT_COMPLETE = "agent_complete"
    AGENT_ERROR = "agent_error"
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    STATE_UPDATE = "state_update"
    CONSENSUS_VOTE = "consensus_vote"
    SELF_HEALING = "self_healing"
    POLICY_CHECK = "policy_check"


@dataclass
class SessionEvent:
    """A single event in a session."""
    session_id: str
    event_id: str
    event_type: EventType
    timestamp: datetime
    agent_name: Optional[str] = None
    data: Dict[str, Any] = None
    duration_ms: Optional[float] = None
    parent_event_id: Optional[str] = None

    def to_dict(self):
        result = asdict(self)
        result["timestamp"] = self.timestamp.isoformat()
        result["event_type"] = self.event_type.value
        return result


class SessionReplayEngine:
    """
    Records and replays agent sessions for debugging and auditing.
    """

    def __init__(self, storage_path: str = "data/sessions"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Initialize SQLite database if available
        self.db_path = self.storage_path / "sessions.db"
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database for session storage."""
        if not SQLITE_AVAILABLE:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                run_id TEXT,
                goal TEXT,
                pipeline_type TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                status TEXT,
                metadata TEXT
            )
        """)

        # Create events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_events (
                event_id TEXT PRIMARY KEY,
                session_id TEXT,
                event_type TEXT,
                timestamp TIMESTAMP,
                agent_name TEXT,
                data TEXT,
                duration_ms REAL,
                parent_event_id TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id)
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON session_events (session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON session_events (timestamp)")

        conn.commit()
        conn.close()

    def start_session(self, session_id: str, run_id: str, goal: str,
                     pipeline_type: str, metadata: Optional[Dict] = None) -> str:
        """Start recording a new session."""
        if SQLITE_AVAILABLE:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO sessions
                (session_id, run_id, goal, pipeline_type, start_time, status, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, run_id, goal, pipeline_type,
                datetime.now().isoformat(), "running",
                json.dumps(metadata or {})
            ))

            conn.commit()
            conn.close()

        # Also write to JSON file for easy access
        json_path = self.storage_path / f"{session_id}.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)

        session_data = {
            "session_id": session_id,
            "run_id": run_id,
            "goal": goal,
            "pipeline_type": pipeline_type,
            "start_time": datetime.now().isoformat(),
            "status": "running",
            "metadata": metadata or {},
            "events": []
        }

        json_path.write_text(json.dumps(session_data, indent=2), encoding="utf-8")

        return session_id

    def record_event(self, session_id: str, event_type: EventType,
                    agent_name: Optional[str] = None, data: Optional[Dict] = None,
                    duration_ms: Optional[float] = None,
                    parent_event_id: Optional[str] = None) -> str:
        """Record an event in a session."""
        event_id = f"{session_id}_{int(datetime.now().timestamp() * 1000)}_{event_type.value}"
        event = SessionEvent(
            session_id=session_id,
            event_id=event_id,
            event_type=event_type,
            timestamp=datetime.now(),
            agent_name=agent_name,
            data=data or {},
            duration_ms=duration_ms,
            parent_event_id=parent_event_id
        )

        if SQLITE_AVAILABLE:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO session_events
                (event_id, session_id, event_type, timestamp, agent_name, data, duration_ms, parent_event_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id, session_id, event_type.value,
                event.timestamp.isoformat(), agent_name,
                json.dumps(data or {}), duration_ms, parent_event_id
            ))

            conn.commit()
            conn.close()

        # Update JSON file
        json_path = self.storage_path / f"{session_id}.json"
        if json_path.exists():
            session_data = json.loads(json_path.read_text(encoding="utf-8"))
            session_data["events"].append(event.to_dict())
            json_path.write_text(json.dumps(session_data, indent=2), encoding="utf-8")

        return event_id

    def end_session(self, session_id: str, status: str = "completed",
                   error: Optional[str] = None):
        """End a session recording."""
        end_time = datetime.now()

        if SQLITE_AVAILABLE:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE sessions
                SET end_time = ?, status = ?
                WHERE session_id = ?
            """, (end_time.isoformat(), status, session_id))

            conn.commit()
            conn.close()

        # Update JSON file
        json_path = self.storage_path / f"{session_id}.json"
        if json_path.exists():
            session_data = json.loads(json_path.read_text(encoding="utf-8"))
            session_data["end_time"] = end_time.isoformat()
            session_data["status"] = status
            if error:
                session_data["error"] = error
            json_path.write_text(json.dumps(session_data, indent=2), encoding="utf-8")

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a complete session with all events."""
        # Try to load from JSON first (faster)
        json_path = self.storage_path / f"{session_id}.json"
        if json_path.exists():
            return json.loads(json_path.read_text(encoding="utf-8"))

        # Fallback to database
        if not SQLITE_AVAILABLE:
            return None

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get session info
        cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
        session_row = cursor.fetchone()

        if not session_row:
            conn.close()
            return None

        # Get events
        cursor.execute("""
            SELECT * FROM session_events
            WHERE session_id = ?
            ORDER BY timestamp
        """, (session_id,))

        events = []
        for row in cursor.fetchall():
            event = dict(row)
            # Parse JSON data
            if event["data"]:
                event["data"] = json.loads(event["data"])
            events.append(event)

        conn.close()

        # Construct session data
        session_data = dict(session_row)
        if session_data["metadata"]:
            session_data["metadata"] = json.loads(session_data["metadata"])
        session_data["events"] = events

        return session_data

    def list_sessions(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List recent sessions."""
        sessions = []

        # List JSON files
        json_files = sorted(self.storage_path.glob("*.json"),
                          key=lambda x: x.stat().st_mtime,
                          reverse=True)

        for json_file in json_files[offset:offset + limit]:
            try:
                session_data = json.loads(json_file.read_text(encoding="utf-8"))
                sessions.append({
                    "session_id": session_data["session_id"],
                    "run_id": session_data["run_id"],
                    "goal": session_data["goal"],
                    "pipeline_type": session_data["pipeline_type"],
                    "start_time": session_data["start_time"],
                    "status": session_data.get("status", "unknown"),
                    "event_count": len(session_data.get("events", [])),
                    "file_path": str(json_file)
                })
            except (json.JSONDecodeError, KeyError):
                continue

        return sessions

    async def replay_session(self, session_id: str, speed: float = 1.0) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Replay a session in real-time (or sped up).

        Args:
            session_id: The session to replay
            speed: Playback speed (1.0 = real-time, 2.0 = 2x speed, etc.)

        Yields:
            Events in chronological order with simulated timing
        """
        session = self.get_session(session_id)
        if not session or "events" not in session:
            yield {"error": f"Session {session_id} not found or has no events"}
            return

        events = session["events"]
        if not events:
            yield {"info": "Session has no events"}
            return

        # Sort events by timestamp
        events.sort(key=lambda e: e["timestamp"])

        # Replay events
        start_time = datetime.fromisoformat(events[0]["timestamp"])
        last_time = start_time

        for i, event in enumerate(events):
            current_time = datetime.fromisoformat(event["timestamp"])
            wait_seconds = (current_time - last_time).total_seconds()

            if i > 0 and wait_seconds > 0:
                # Wait proportionally to playback speed
                await asyncio.sleep(wait_seconds / speed)

            # Yield the event
            yield {
                "event": event,
                "progress": (i + 1) / len(events),
                "total_events": len(events),
                "current_event": i + 1
            }

            last_time = current_time

        yield {"status": "replay_complete", "total_events": len(events)}

    def get_session_statistics(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session."""
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}

        events = session.get("events", [])
        if not events:
            return {"event_count": 0}

        # Calculate statistics
        agent_events = [e for e in events if e.get("agent_name")]
        llm_events = [e for e in events if e.get("event_type") == "llm_call"]
        error_events = [e for e in events if e.get("event_type") == "agent_error"]

        # Calculate durations
        durations = []
        for event in events:
            if event.get("duration_ms"):
                durations.append(event["duration_ms"])

        # Group by agent
        agent_stats = {}
        for event in agent_events:
            agent_name = event.get("agent_name")
            if agent_name:
                if agent_name not in agent_stats:
                    agent_stats[agent_name] = {
                        "count": 0,
                        "total_duration_ms": 0,
                        "errors": 0
                    }

                agent_stats[agent_name]["count"] += 1
                if event.get("duration_ms"):
                    agent_stats[agent_name]["total_duration_ms"] += event["duration_ms"]

                if event.get("event_type") == "agent_error":
                    agent_stats[agent_name]["errors"] += 1

        # Calculate timeline
        timeline = []
        for event in events[:100]:  # Limit for performance
            timeline.append({
                "timestamp": event["timestamp"],
                "event_type": event["event_type"],
                "agent_name": event.get("agent_name"),
                "duration_ms": event.get("duration_ms")
            })

        return {
            "session_id": session_id,
            "total_events": len(events),
            "agent_events": len(agent_events),
            "llm_events": len(llm_events),
            "error_events": len(error_events),
            "agent_statistics": agent_stats,
            "duration_stats": {
                "total_ms": sum(durations) if durations else 0,
                "average_ms": sum(durations) / len(durations) if durations else 0,
                "min_ms": min(durations) if durations else 0,
                "max_ms": max(durations) if durations else 0
            },
            "timeline": timeline
        }


# Global session replay instance
session_replay = SessionReplayEngine()