#!/usr/bin/env python3
"""
Generate demo/sample data for screenshots and documentation.
Creates fake AI sessions in a demo workspace without exposing real conversation history.
"""

import json
import shutil
from pathlib import Path


def create_demo_workspace(base_path: Path):
    """Create a demo workspace with fake AI sessions."""
    demo_path = base_path / "demo_workspace"

    # Clean up if exists
    if demo_path.exists():
        shutil.rmtree(demo_path)

    demo_path.mkdir(parents=True)
    return demo_path


def generate_cursor_sessions(workspace: Path, base_path: Path):
    """Generate fake Cursor sessions in proper storage structure."""
    # Create Cursor workspaceStorage structure
    cursor_storage = base_path / ".cursor" / "User" / "workspaceStorage"
    cursor_storage.mkdir(parents=True, exist_ok=True)

    # Create a workspace-specific directory with workspace.json
    import hashlib

    workspace_hash = hashlib.md5(str(workspace).encode()).hexdigest()[:32]
    workspace_dir = cursor_storage / workspace_hash
    workspace_dir.mkdir(exist_ok=True)

    # Create workspace.json to link to our demo workspace
    import json

    workspace_json = {"folder": f"file://{workspace}"}
    with open(workspace_dir / "workspace.json", "w") as f:
        json.dump(workspace_json, f, indent=2)

    # Create the SQLite database with sessions
    import sqlite3

    db_path = workspace_dir / "state.vscdb"
    conn = sqlite3.connect(db_path)

    # Create ItemTable if it doesn't exist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ItemTable (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    sessions = [
        {
            "id": "demo-cursor-001",
            "title": "Building a REST API with FastAPI",
            "messages": [
                {"sender": "user", "text": "How do I create a REST API with FastAPI?"},
                {
                    "sender": "assistant",
                    "text": "I'll help you create a REST API with FastAPI. Here's a basic example...",
                },
                {"sender": "user", "text": "Can you add database support with SQLAlchemy?"},
                {"sender": "assistant", "text": "Sure! Let me add SQLAlchemy integration..."},
            ],
        },
        {
            "id": "demo-cursor-002",
            "title": "Debug Python memory leak",
            "messages": [
                {"sender": "user", "text": "My Python app is using too much memory. Can you help debug it?"},
                {
                    "sender": "assistant",
                    "text": "Let me analyze the memory usage patterns. First, let's use memory_profiler...",
                },
            ],
        },
        {
            "id": "demo-cursor-003",
            "title": "Implement authentication system",
            "messages": [
                {"sender": "user", "text": "I need to implement JWT authentication for my API"},
                {"sender": "assistant", "text": "I'll help you implement JWT authentication with refresh tokens..."},
            ],
        },
    ]

    # Insert sessions into database
    import json

    for session in sessions:
        data = {"messages": session["messages"], "customTitle": session["title"]}
        key = f"workbench.panel.aichat.view.aichat.chatdata.{session['id']}"
        conn.execute("INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)", (key, json.dumps(data)))

    conn.commit()
    conn.close()

    print(f"✓ Created {len(sessions)} Cursor sessions")


def generate_copilot_sessions(workspace: Path, base_path: Path):
    """Generate fake GitHub Copilot sessions in proper storage structure."""
    # Create VS Code workspaceStorage structure similar to real setup
    vscode_storage = base_path / ".vscode" / "User" / "workspaceStorage"
    vscode_storage.mkdir(parents=True, exist_ok=True)

    # Create a workspace-specific directory with workspace.json
    import hashlib

    workspace_hash = hashlib.md5(str(workspace).encode()).hexdigest()[:32]
    workspace_dir = vscode_storage / workspace_hash
    workspace_dir.mkdir(exist_ok=True)

    # Create workspace.json
    import json

    workspace_json = {"folder": f"file://{workspace}"}
    with open(workspace_dir / "workspace.json", "w") as f:
        json.dump(workspace_json, f, indent=2)

    # Create chatSessions directory (what Copilot reader expects)
    copilot_dir = workspace_dir / "chatSessions"
    copilot_dir.mkdir(parents=True, exist_ok=True)

    sessions = [
        {
            "sessionId": "demo-copilot-001",
            "customTitle": "React component optimization",
            "requests": [
                {
                    "message": {"text": "How can I optimize this React component for performance?"},
                    "response": [
                        {
                            "kind": "text",
                            "value": "Here are several optimization techniques for your React component...",
                        }
                    ],
                },
                {
                    "message": {"text": "Should I use useMemo or useCallback here?"},
                    "response": [
                        {
                            "kind": "text",
                            "value": "Use useMemo for expensive calculations and useCallback for function references...",
                        }
                    ],
                },
            ],
        },
        {
            "sessionId": "demo-copilot-002",
            "customTitle": "Writing unit tests",
            "requests": [
                {
                    "message": {"text": "Help me write unit tests for this function"},
                    "response": [
                        {"kind": "text", "value": "I'll help you write comprehensive unit tests using pytest..."}
                    ],
                }
            ],
        },
    ]

    for idx, session in enumerate(sessions):
        session_file = copilot_dir / f"session_{idx + 1}.json"
        with open(session_file, "w") as f:
            json.dump(session, f, indent=2)

    print(f"✓ Created {len(sessions)} Copilot sessions")


def generate_rovodev_sessions(workspace: Path, base_path: Path):
    """Generate fake Rovo Dev sessions in proper storage structure."""
    import uuid

    # Create Rovodev sessions directory
    rovodev_sessions_dir = base_path / ".rovodev" / "sessions"
    rovodev_sessions_dir.mkdir(parents=True, exist_ok=True)

    sessions = [
        {
            "title": "Refactor legacy codebase",
            "workspace": str(workspace),
            "messages": [
                {"role": "user", "parts": [{"part_kind": "text", "content": "Help me refactor this legacy codebase"}]},
                {
                    "role": "assistant",
                    "parts": [
                        {
                            "part_kind": "text",
                            "content": "I'll analyze the codebase structure and suggest a refactoring strategy...",
                        }
                    ],
                },
                {
                    "role": "user",
                    "parts": [{"part_kind": "text", "content": "Can you extract common patterns into utilities?"}],
                },
            ],
        },
        {
            "title": "Set up CI/CD pipeline",
            "workspace": str(workspace),
            "messages": [
                {
                    "role": "user",
                    "parts": [{"part_kind": "text", "content": "Set up CI/CD pipeline for Python project"}],
                },
                {
                    "role": "assistant",
                    "parts": [
                        {
                            "part_kind": "text",
                            "content": "I'll help you set up GitHub Actions for testing and deployment...",
                        }
                    ],
                },
            ],
        },
        {
            "title": "Find TODO comments",
            "workspace": str(workspace),
            "messages": [
                {"role": "user", "parts": [{"part_kind": "text", "content": "Find all TODO comments in the codebase"}]},
                {
                    "role": "assistant",
                    "parts": [
                        {"part_kind": "text", "content": "I'll search for TODO comments across your codebase..."}
                    ],
                },
            ],
        },
    ]

    for session_data in sessions:
        # Generate UUID for session
        session_uuid = str(uuid.uuid4())
        session_dir = rovodev_sessions_dir / session_uuid
        session_dir.mkdir(exist_ok=True)

        # Create session_context.json with message history
        session_context = {"message_history": session_data["messages"]}
        with open(session_dir / "session_context.json", "w") as f:
            json.dump(session_context, f, indent=2)

        # Create metadata.json
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        try:
            from ai_session_bridge.core import normalize_workspace_path

            normalized_workspace = normalize_workspace_path(session_data["workspace"])
        except ImportError:
            # Fallback if import fails
            normalized_workspace = str(Path(session_data["workspace"]).resolve())

        metadata = {"title": session_data["title"], "workspace_path": normalized_workspace}
        with open(session_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

    print(f"✓ Created {len(sessions)} Rovo Dev sessions in {rovodev_sessions_dir}")


def main():
    """Generate all demo data."""
    print("🎬 Generating demo data for screenshots...\n")

    # Create demo workspace in /tmp for isolation
    base_path = Path("/tmp/ai_session_bridge_demo")
    demo_workspace = create_demo_workspace(base_path)

    print(f"📁 Demo workspace: {demo_workspace}\n")

    # Generate sessions for each tool
    generate_cursor_sessions(demo_workspace, base_path)
    generate_copilot_sessions(demo_workspace, base_path)
    generate_rovodev_sessions(demo_workspace, base_path)

    print("\n✅ Demo data generated successfully!")
    print("\n📸 To use for screenshots, run commands with environment variables:")
    print("\nOption 1: Set environment variables")
    print(f"export CURSOR_STORAGE='{base_path}/.cursor/User/workspaceStorage'")
    print(f"export VSCODE_STORAGE='{base_path}/.vscode/User/workspaceStorage'")
    print(f"export ROVODEV_HOME='{base_path}'")
    print("\nThen run:")
    print("   ai-session-bridge list")
    print("   ai-session-bridge search 'API'")
    print("\nOption 2: One-liner")
    print(f"CURSOR_STORAGE='{base_path}/.cursor/User/workspaceStorage' \\")
    print(f"VSCODE_STORAGE='{base_path}/.vscode/User/workspaceStorage' \\")
    print(f"ROVODEV_HOME='{base_path}' \\")
    print("ai-session-bridge list")
    print(f"\n🧹 To clean up: rm -rf {base_path}")


if __name__ == "__main__":
    main()
