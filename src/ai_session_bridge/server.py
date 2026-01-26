"""MCP server implementation."""

import asyncio
import json
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from .cache import SearchIndex, SessionCache
from .core import get_current_workspace, normalize_workspace_path
from .core.config import load_config
from .core.filter import ContentFilter
from .readers import get_registry

# Initialize MCP server
server = Server("ai-session-bridge")

# Global state
_config = None
_registry = None
_session_cache: SessionCache | None = None
_search_index: SearchIndex | None = None
_content_filter: ContentFilter | None = None


def _init_globals() -> None:
    """Initialize global state."""
    global _config, _registry, _session_cache, _search_index, _content_filter

    if _config is None:
        _config = load_config()
        _registry = get_registry()

        cache_dir = _config.get_cache_dir()

        if _config.cache.enabled:
            _session_cache = SessionCache(cache_dir)

        if _config.search.enabled:
            _search_index = SearchIndex(cache_dir)

        if _config.filtering.enabled:
            _content_filter = ContentFilter(_config.filtering)


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="list_sessions",
            description="List all AI sessions for a workspace. Returns session IDs, tools, timestamps, and preview of first message.",
            inputSchema={
                "type": "object",
                "properties": {
                    "workspace_path": {
                        "type": "string",
                        "description": "Workspace path. Defaults to current working directory. Ignored if all_workspaces is true.",
                    },
                    "all_workspaces": {
                        "type": "boolean",
                        "default": False,
                        "description": "If true, list sessions from all workspaces instead of just the specified workspace.",
                    },
                    "tool_filter": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by tools: copilot, cursor, rovodev",
                    },
                    "limit": {"type": "integer", "default": 10, "description": "Max sessions to return"},
                },
            },
        ),
        Tool(
            name="get_session",
            description="Get full conversation from a specific session.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Session ID"},
                    "tool": {"type": "string", "enum": ["copilot", "cursor", "rovodev"], "description": "Tool name"},
                    "workspace_path": {"type": "string", "description": "Workspace path (optional)"},
                },
                "required": ["session_id", "tool"],
            },
        ),
        Tool(
            name="search_sessions",
            description="Search across all sessions for keywords. Use full-text search to find relevant messages.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "workspace_path": {
                        "type": "string",
                        "description": "Workspace path. Defaults to current working directory. Ignored if all_workspaces is true.",
                    },
                    "all_workspaces": {
                        "type": "boolean",
                        "default": False,
                        "description": "If true, search sessions from all workspaces instead of just the specified workspace.",
                    },
                    "tool": {"type": "string", "description": "Filter by tool (optional)"},
                    "limit": {"type": "integer", "default": 20, "description": "Maximum results"},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_recent_context",
            description="Get summarized context from recent sessions. Use this when user says 'continue where I left off' or wants context from previous sessions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "workspace_path": {
                        "type": "string",
                        "description": "Workspace path. Defaults to current working directory. Ignored if all_workspaces is true.",
                    },
                    "all_workspaces": {
                        "type": "boolean",
                        "default": False,
                        "description": "If true, get context from all workspaces instead of just the specified workspace.",
                    },
                    "max_sessions": {"type": "integer", "default": 3, "description": "Max sessions to include"},
                    "max_messages": {"type": "integer", "default": 20, "description": "Max messages per session"},
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    _init_globals()

    if name == "list_sessions":
        return await _list_sessions_tool(arguments)
    elif name == "get_session":
        return await _get_session_tool(arguments)
    elif name == "search_sessions":
        return await _search_sessions_tool(arguments)
    elif name == "get_recent_context":
        return await _get_recent_context_tool(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def _list_sessions_tool(args: dict) -> list[TextContent]:
    """Implement list_sessions tool."""
    all_workspaces = args.get("all_workspaces", False)

    if all_workspaces:
        workspace_path = None
    else:
        workspace_path = args.get("workspace_path") or get_current_workspace()
        workspace_path = normalize_workspace_path(workspace_path)

    tool_filter = args.get("tool_filter", [])
    limit = args.get("limit", 10)

    # Get tools to query
    tools_to_query = tool_filter if tool_filter else _registry.list_tools()

    # Collect sessions
    all_sessions = []

    for tool_name in tools_to_query:
        reader = _registry.get_reader(tool_name)
        if not reader:
            continue

        try:
            sessions = reader.get_sessions(workspace_path)
            all_sessions.extend(sessions)

            # Cache and index sessions
            if _session_cache:
                for session in sessions:
                    _session_cache.cache_summary(session)
        except Exception as e:
            print(f"Warning: Failed to read {tool_name} sessions: {e}")

    # Sort and limit
    all_sessions.sort(key=lambda s: s.updated_at, reverse=True)
    all_sessions = all_sessions[:limit]

    # Format response
    result = {
        "workspace": workspace_path if workspace_path else "all",
        "total_sessions": len(all_sessions),
        "sessions": [
            {
                "id": s.id,
                "tool": s.tool,
                "title": s.title,
                "workspace": s.workspace_path,
                "message_count": s.message_count,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
                "preview": s.preview,
            }
            for s in all_sessions
        ],
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _get_session_tool(args: dict) -> list[TextContent]:
    """Implement get_session tool."""
    session_id = args["session_id"]
    tool = args["tool"]
    workspace_path = args.get("workspace_path") or get_current_workspace()
    workspace_path = normalize_workspace_path(workspace_path)

    reader = _registry.get_reader(tool)
    if not reader:
        return [TextContent(type="text", text=f"Error: Unknown tool '{tool}'")]

    # Find and read session
    try:
        session_file = reader.find_session_by_id(session_id, workspace_path)
        if not session_file:
            return [TextContent(type="text", text=f"Error: Session '{session_id}' not found")]

        # Pass workspace_path to preserve it in the session
        try:
            session = reader.read_session(session_file, workspace_path)
        except TypeError:
            # Reader doesn't support workspace_path parameter
            session = reader.read_session(session_file)

        # Apply filtering
        if _content_filter:
            session.messages = [_content_filter.filter_message(msg) for msg in session.messages]

        # Index session if needed
        if _search_index and not _search_index.is_indexed(session, session_file):
            _search_index.index_session(session, session_file)

        # Format response
        result = {
            "id": session.id,
            "tool": session.tool,
            "workspace": session.workspace_path,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "message_count": len(session.messages),
            "messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                }
                for msg in session.messages
            ],
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]


async def _search_sessions_tool(args: dict) -> list[TextContent]:
    """Implement search_sessions tool."""
    query = args["query"]
    all_workspaces = args.get("all_workspaces", False)

    if all_workspaces:
        workspace_path = None
    else:
        workspace_path = args.get("workspace_path") or get_current_workspace()
        workspace_path = normalize_workspace_path(workspace_path)

    tool = args.get("tool")
    limit = args.get("limit", 20)

    if not _search_index:
        return [TextContent(type="text", text="Error: Search is disabled")]

    # Search
    try:
        results = _search_index.search(query, workspace=workspace_path, tool=tool, limit=limit)

        # Format response
        result = {
            "query": query,
            "total_results": len(results),
            "results": [
                {
                    "session_id": r.session_id,
                    "tool": r.tool,
                    "workspace": r.workspace_path,
                    "session_title": r.session_title,
                    "role": r.role,
                    "timestamp": r.timestamp.isoformat(),
                    "content": r.content[:500] + "..." if len(r.content) > 500 else r.content,
                    "relevance": r.relevance,
                }
                for r in results
            ],
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]


async def _get_recent_context_tool(args: dict) -> list[TextContent]:
    """Implement get_recent_context tool."""
    all_workspaces = args.get("all_workspaces", False)

    if all_workspaces:
        workspace_path = None
    else:
        workspace_path = args.get("workspace_path") or get_current_workspace()
        workspace_path = normalize_workspace_path(workspace_path)

    max_sessions = args.get("max_sessions", _config.mcp.max_context_sessions)
    max_messages = args.get("max_messages", _config.mcp.max_context_messages)

    # Get recent sessions
    all_sessions = []

    for tool_name in _registry.list_tools():
        reader = _registry.get_reader(tool_name)
        if not reader:
            continue

        try:
            sessions = reader.get_sessions(workspace_path)
            all_sessions.extend(sessions)
        except Exception as e:
            print(f"Warning: Failed to read {tool_name} sessions: {e}")

    # Sort by update time and limit
    all_sessions.sort(key=lambda s: s.updated_at, reverse=True)
    all_sessions = all_sessions[:max_sessions]

    # Load full sessions and get messages
    context_messages = []

    for summary in all_sessions:
        reader = _registry.get_reader(summary.tool)
        if not reader:
            continue

        try:
            session_file = Path(summary.file_path)
            # Pass workspace_path to preserve it
            try:
                session = reader.read_session(session_file, workspace_path)
            except TypeError:
                # Reader doesn't support workspace_path parameter
                session = reader.read_session(session_file)

            # Apply filtering
            if _content_filter:
                session.messages = [_content_filter.filter_message(msg) for msg in session.messages]

            # Take last N messages from each session
            recent_messages = session.messages[-max_messages:]

            for msg in recent_messages:
                context_messages.append(
                    {
                        "session_id": session.id,
                        "tool": session.tool,
                        "role": msg.role.value,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat(),
                    }
                )
        except Exception as e:
            print(f"Warning: Failed to read session {summary.id}: {e}")

    # Format response
    result = {
        "workspace": workspace_path if workspace_path else "all",
        "sessions_included": len(all_sessions),
        "total_messages": len(context_messages),
        "context": context_messages,
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


def run_server() -> None:
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server

    async def arun():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(arun())


if __name__ == "__main__":
    run_server()
